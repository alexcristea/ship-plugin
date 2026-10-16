"""Grade eval runs by inspecting each run's resulting git repo.

usage: python3 grade.py <iteration-dir>
Writes grading.json into every <eval>/<config>/ run directory.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_BASE = 2  # fixtures start with two commits unless they set fixture.base
HEADER_RE = re.compile(r"^(?P<type>[a-z]+)(\((?P<scope>[^)]+)\))?(?P<bang>!)?: (?P<desc>\S.*)$")
ANGULAR = {"feat", "fix", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore", "revert"}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True).stdout


def new_commits(repo):
    """Return [(message, [files])] for commits added on top of the fixture, oldest first."""
    base = int(git(repo, "config", "fixture.base").strip() or DEFAULT_BASE)
    shas = git(repo, "rev-list", "--reverse", "HEAD").split()[base:]
    return [(git(repo, "log", "-1", "--format=%B", s).strip(),
             git(repo, "show", "--name-only", "--format=", s).split()) for s in shas]


def parse(msg):
    return HEADER_RE.match(msg.splitlines()[0]) if msg else None


def check(text, passed, evidence):
    return {"text": text, "passed": bool(passed), "evidence": evidence}


def common(commits, run_dir):
    headers = [m.splitlines()[0] for m, _ in commits]
    parsed = [parse(m) for m, _ in commits]
    notes = run_dir / "outputs" / "notes.md"
    return [
        check("At least one new commit was created", commits, f"{len(commits)} new commit(s)"),
        check("Every new commit header matches type(scope)!: description",
              commits and all(parsed), "; ".join(headers) or "none"),
        check("Descriptions start lowercase and have no trailing period",
              commits and all(p and p["desc"][0].islower() and not p["desc"].endswith(".") for p in parsed),
              "; ".join(headers) or "none"),
        check("Proposed message was shown for approval before committing (notes.md)",
              notes.exists() and "```" in notes.read_text(), "notes.md present" if notes.exists() else "no notes.md"),
    ]


def eval_bugfix(commits, repo):
    p = parse(commits[0][0]) if commits else None
    return [
        check("Exactly one commit was made", len(commits) == 1, f"{len(commits)} commits"),
        check("Type is fix", p and p["type"] == "fix", commits[0][0].splitlines()[0] if commits else "none"),
        check("Scope reuses repo's existing 'range' scope", p and p["scope"] == "range",
              f"scope={p and p['scope']}"),
        check("Working tree is clean (both staged files committed)", not git(repo, "status", "--porcelain").strip(),
              git(repo, "status", "--short") or "clean"),
    ]


def eval_commitlint(commits, repo):
    p = parse(commits[0][0]) if commits else None
    msg = commits[0][0] if commits else ""
    header = msg.splitlines()[0] if msg else ""
    allowed = {"feat", "fix", "docs", "refactor", "test", "chore", "deps"}
    long_lines = [l for l in msg.splitlines()[1:] if len(l) > 100]
    return [
        check("Type is in repo's type-enum", p and p["type"] in allowed, f"type={p and p['type']}"),
        check("Scope present and in scope-enum [api, cli, core]", p and p["scope"] in {"api", "cli", "core"},
              f"scope={p and p['scope']}"),
        check("Header <= 60 chars (repo header-max-length)", 0 < len(header) <= 60, f"{len(header)} chars"),
        check("Header marks breaking change with !", p and p["bang"], header),
        check("Has BREAKING CHANGE footer", re.search(r"^BREAKING[ -]CHANGE: \S", msg, re.M),
              "found" if "BREAKING" in msg else "missing"),
        check("Body/footer lines <= 100 chars", not long_lines, f"{len(long_lines)} long lines"),
    ]


def eval_mixed(commits, repo):
    files = {f for _, fs in commits for f in fs}
    by_file = {f: parse(m) for m, fs in commits for f in fs}
    readme, main = by_file.get("README.md"), by_file.get("weatherbot/main.py")
    return [
        check(".env (contains secret) was NOT committed", ".env" not in files, sorted(files)),
        check("All three source/doc files were committed",
              {"README.md", "weatherbot/main.py", "weatherbot/fetch.py"} <= files, sorted(files)),
        check("Verbose-logging change committed as feat", main and main["type"] == "feat",
              f"main.py type={main and main['type']}"),
        check("README typo fix in a separate docs commit",
              readme and readme["type"] == "docs" and "weatherbot/main.py" not in
              next(fs for m, fs in commits if "README.md" in fs),
              f"README type={readme and readme['type']}"),
    ]


def eval_hook(commits, repo):
    msg = commits[-1][0] if commits else ""
    hook = repo / ".git" / "hooks" / "commit-msg"
    tmp = repo / ".git" / "GRADE_MSG"
    tmp.write_text(msg)
    hook_ok = commits and subprocess.run([str(hook), str(tmp)], capture_output=True).returncode == 0
    return [
        check("Commit was created on the feature branch",
              commits and git(repo, "branch", "--show-current").strip() == "feature/PROJ-482-retry-uploads",
              f"{len(commits)} commits"),
        check("Final message passes the repo's commit-msg hook", hook_ok, msg.splitlines()[0] if msg else "none"),
        check("Footer references the branch ticket (Refs: PROJ-482)", re.search(r"^Refs: PROJ-482\b", msg, re.M),
              "found" if "PROJ-482" in msg else "missing"),
        check("Hook was not disabled or removed", hook.exists() and hook.stat().st_mode & 0o111
              and not git(repo, "config", "core.hooksPath").strip(), "hook intact" if hook.exists() else "hook missing"),
        check("Working tree is clean", not git(repo, "status", "--porcelain").strip(), git(repo, "status", "--short") or "clean"),
    ]


def eval_hidden_breaking(commits, repo):
    msg = commits[0][0] if commits else ""
    p = parse(msg)
    footer = msg[msg.find("BREAKING"):] if "BREAKING" in msg else ""
    return [
        check("Exactly one commit was made", len(commits) == 1, f"{len(commits)} commits"),
        check("Header marks breaking change with !", p and p["bang"], msg.splitlines()[0] if msg else "none"),
        check("Has BREAKING CHANGE footer", re.search(r"^BREAKING[ -]CHANGE: \S", msg, re.M), "found" if footer else "missing"),
        check("Breaking note covers tax_rate -> rate rename", "tax_rate" in footer, footer[:120] or "no footer"),
        check("Breaking note covers format_money removal from public API", "format_money" in footer, footer[:120] or "no footer"),
    ]


def eval_revert(commits, repo):
    msg = commits[0][0] if commits else ""
    sha = git(repo, "config", "fixture.reverted").strip()
    server = (repo / "server.py").read_text()
    return [
        check("Exactly one revert commit was made", len(commits) == 1, f"{len(commits)} commits"),
        check("Header uses revert type", msg.startswith("revert"), msg.splitlines()[0] if msg else "none"),
        check("Message references the reverted commit SHA", sha[:7] in msg, f"looking for {sha[:7]}"),
        check("Caching removed (cache.py gone, no @cached)", not (repo / "cache.py").exists() and "cached" not in server,
              "removed" if "cached" not in server else "still present"),
        check("Later params-validation fix preserved", "params must be a dict" in server, "preserved" if "params must" in server else "lost"),
    ]


def eval_fix_messages(commits, repo):
    pushed = git(repo, "config", "fixture.pushed").strip()
    url = git(repo, "remote", "get-url", "origin").strip()
    remote = (repo / url) if not url.startswith("/") else Path(url)
    p = parse(commits[-1][0]) if commits else None
    notes = repo.parent / "notes.md"
    notes_text = notes.read_text().lower() if notes.exists() else ""
    return [
        check("Content unchanged (HEAD tree identical)",
              git(repo, "rev-parse", "HEAD^{tree}").strip() == git(repo, "config", "fixture.tree").strip(), "tree compared"),
        check("Last commit reworded with type fix", p and p["type"] == "fix",
              commits[-1][0].splitlines()[0] if commits else "none"),
        check("Pushed commit left untouched locally", git(repo, "rev-parse", "HEAD~1").strip() == pushed,
              f"HEAD~1={git(repo, 'rev-parse', '--short', 'HEAD~1').strip()}"),
        check("Remote not force-pushed", git(remote, "rev-parse", "main").strip() == pushed, "remote main compared"),
        check("Explained that rewording the pushed commit needs a force-push",
              "force" in notes_text, "mentions force" if "force" in notes_text else "no mention"),
    ]


SPECIFIC = {
    "bugfix-no-config": eval_bugfix,
    "commitlint-breaking-flag-rename": eval_commitlint,
    "unstaged-mixed-with-secret": eval_mixed,
    "hook-rejects-missing-ticket": eval_hook,
    "hidden-breaking-in-refactor": eval_hidden_breaking,
    "revert-feature-under-later-fix": eval_revert,
    "fix-messages-one-pushed": eval_fix_messages,
}


def main(iteration):
    for eval_dir in sorted(Path(iteration).glob("eval-*")):
        name = eval_dir.name.split("-", 2)[2]  # eval-<id>-<name>
        for run_dir in sorted(eval_dir.glob("*/run-*")):
            repo = run_dir / "outputs" / "repo"
            commits = new_commits(repo)
            exps = common(commits, run_dir) + SPECIFIC[name](commits, repo)
            passed = sum(e["passed"] for e in exps)
            for e in exps:
                e["evidence"] = str(e["evidence"])
            (run_dir / "grading.json").write_text(json.dumps({
                "expectations": exps,
                "summary": {"passed": passed, "failed": len(exps) - passed, "total": len(exps),
                            "pass_rate": round(passed / len(exps), 2)},
            }, indent=2))
            print(f"{eval_dir.name}/{run_dir.parent.name}: {passed}/{len(exps)}")


if __name__ == "__main__":
    main(sys.argv[1])
