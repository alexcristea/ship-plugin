"""Grade pr eval runs from the PR the fake gh recorded, the run's notes and the bare origin.

usage: python3 grade.py <iteration-dir> [--model <model-id>]
Writes grading.json into every <eval>/<config>/ run directory, and run.json into the iteration
directory recording which skill commit and model the iteration was graded against.
"""
import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

SKILL = Path(__file__).resolve().parent.name  # evals/<skill>/grade.py
ROOT = Path(__file__).resolve().parents[2]
MAX_WORDS = 200
HEADER = re.compile(r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(?:\(([\w./-]+)\))?(!)?: \S.*[^.]$")


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True).stdout


def check(text, passed, evidence):
    return {"text": text, "passed": bool(passed), "evidence": evidence}


def fixture(repo, key):
    return git(repo, "config", f"fixture.{key}").strip()


def pr(repo):
    """The PR as the fake gh left it: {} when none was opened."""
    path = repo.parent / "gh" / "pr.json"
    return json.loads(path.read_text()) if path.exists() else {}


def calls(repo, cmd):
    path = repo.parent / "gh" / "calls.jsonl"
    lines = path.read_text().splitlines() if path.exists() else []
    return [c for c in map(json.loads, lines) if c["cmd"] == cmd]


def notes(repo):
    path = repo.parent / "notes.md"
    return path.read_text() if path.exists() else ""


def pushed(repo):
    """SHA of the branch on origin, or "" if it was never pushed."""
    return git(repo.parent / "origin.git", "rev-parse", "-q", "--verify", f"refs/heads/{fixture(repo, 'branch')}").strip()


def contains(repo, ancestor, sha):
    return subprocess.run(["git", "-C", str(repo.parent / "origin.git"), "merge-base", "--is-ancestor", ancestor, sha],
                          capture_output=True).returncode == 0


def template(repo):
    return git(repo, "show", f"{fixture(repo, 'head')}:.github/pull_request_template.md")


def words(body, boilerplate):
    """Words a reader has to get through: no HTML comments, code blocks, or lines copied from the PR template."""
    text = re.sub(r"<!--.*?-->|```.*?```", "", body, flags=re.S)
    skip = {line.strip() for line in boilerplate.splitlines() if line.strip()}
    return sum(len(line.split()) for line in text.splitlines() if line.strip() not in skip)


def title(repo):
    return HEADER.match(pr(repo).get("title", ""))


def body(repo):
    return pr(repo).get("body", "")


def common(repo):
    on_origin, main = pushed(repo), git(repo.parent / "origin.git", "rev-parse", "refs/heads/main").strip()
    n = words(body(repo), template(repo))
    return [
        check("Reported back to the user (notes.md)", notes(repo).strip(), "notes.md present" if notes(repo) else "no notes.md"),
        check("main on origin untouched", main == fixture(repo, "originmain"), main[:7]),
        # not pushing is judged by the case's own checks; here only a rewritten branch fails
        check("No force-push or rewritten commits on the branch",
              on_origin in ("", fixture(repo, "originbranch")) or contains(repo, fixture(repo, "head"), on_origin),
              on_origin[:7] or "branch not on origin"),
        check("Title is a Conventional Commits header", title(repo) and len(pr(repo)["title"]) <= 100,
              pr(repo).get("title", "no PR")),
        check(f"Body is concise (at most {MAX_WORDS} words)", body(repo).strip() and n <= MAX_WORDS, f"{n} words"),
    ]


def created(repo):
    made = calls(repo, "create")
    return check("PR opened with gh pr create against main", made and pr(repo).get("baseRefName") == "main",
                 [c.get("base") for c in made] or "no gh pr create")


def title_type(repo, kind):
    return check(f"Title type is {kind}", title(repo) and title(repo).group(1) == kind, pr(repo).get("title", "no PR"))


def mentions(text, pattern):
    return re.search(pattern, text, re.I | re.M)


def eval_feature(repo):
    text = body(repo)
    return [
        created(repo),
        title_type(repo, "feat"),
        check("Body gives the reason from the commit (finance, spreadsheet)", mentions(text, r"financ|spreadsheet|reconcil"),
              text[:200] or "no body"),
        check("Links the issue from the branch (Closes #482)", mentions(text, r"\b(close[sd]?|fix(e[sd])?|resolve[sd]?):? #482\b"),
              "checked"),
        check("Uses the default sections (Summary, Changes, Testing)",
              all(mentions(text, rf"^## {s}\b") for s in ("Summary", "Changes", "Testing")),
              re.findall(r"^#+ .*$", text, re.M)),
        check("No breaking-changes section when nothing breaks", not mentions(text, r"^#+ .*breaking"), "checked"),
    ]


def eval_template(repo):
    text, headings = body(repo), re.findall(r"^## .+$", template(repo), re.M)
    return [
        created(repo),
        title_type(repo, "fix"),
        check("Body keeps the template's headings", all(h in text for h in headings), re.findall(r"^#+ .*$", text, re.M)),
        check("Bug fix box ticked", mentions(text, r"^\s*[-*] \[x\] Bug fix"), "checked"),
    ]


def eval_breaking(repo):
    text = body(repo)
    return [
        created(repo),
        check("Title marks the breaking change with !", title(repo) and title(repo).group(3), pr(repo).get("title", "no PR")),
        check("Body explains the break and the migration (--out to --output)",
              mentions(text, "breaking") and mentions(text, r"--out(?!put)") and "--output" in text, text[:200] or "no body"),
        check("Told the user it's a breaking change, not just a cleanup (notes.md)", mentions(notes(repo), "breaking"),
              "checked"),
    ]


def eval_stale_main(repo):
    text = body(repo)
    return [
        created(repo),
        title_type(repo, "fix"),
        check("Describes the ~ expansion fix", mentions(text, r"~|tilde|home dir|expanduser"), text[:200] or "no body"),
        check("Teammate's SSO commit on origin/main not described", not mentions(text, r"\bsso\b|single sign|login|auth"),
              text[:200] or "no body"),
    ]


def eval_commitlint(repo):
    t = title(repo)
    return [
        created(repo),
        title_type(repo, "feat"),
        check("Title scope is in commitlint's scope-enum (or omitted)",
              t and t.group(2) in (None, "config", "export", "cli", "deps"), pr(repo).get("title", "no PR")),
        check("Title at most 72 characters (header-max-length)", t and len(pr(repo)["title"]) <= 72,
              len(pr(repo).get("title", ""))),
    ]


def eval_existing(repo):
    text, on_origin = body(repo), pushed(repo)
    retries_pushed = on_origin and contains(repo, fixture(repo, "head"), on_origin)
    return [
        check("Existing PR #57 updated with gh pr edit, no new PR",
              any(c["body"] for c in calls(repo, "edit")) and not calls(repo, "create"), "checked"),
        check("Body covers the new retries", mentions(text, r"retr|backoff"), text[:200] or "no body"),
        check("Body still covers the S3 upload", mentions(text, r"\bs3\b|presigned"), text[:200] or "no body"),
        check("Retry commits pushed, or flagged as unpushed (notes.md)",
              retries_pushed or mentions(notes(repo), r"not (yet )?pushed|unpushed|haven't been pushed"), "checked"),
    ]


def claims_cli_wiring(text):
    """A sentence about the uncommitted --format flag that doesn't say it was left out of the PR."""
    sentences = re.split(r"(?<=[.!?;])\s+|\n+", text)
    return any(mentions(s, r"--format|format tsv")
               and not mentions(s, r"follow|separate|later|\byet\b|not (included|part|in)|uncommitted|out of scope")
               for s in sentences)


def eval_uncommitted(repo):
    on_origin = pushed(repo)
    cli = git(repo, "show", f"{on_origin}:widget/cli.py") if on_origin else ""
    describes_flag = claims_cli_wiring(body(repo))
    return [
        created(repo),
        check("Flagged the uncommitted cli.py change (notes.md)",
              mentions(notes(repo), r"uncommitted|not committed|isn't committed|unstaged|working tree|not staged"), "checked"),
        check("Body describes only what's pushed", not describes_flag or "tsv" in cli,
              "CLI wiring described and pushed" if describes_flag and "tsv" in cli else "checked"),
    ]


def eval_mixed(repo):
    return [
        created(repo),
        title_type(repo, "feat"),
        check("Suggested splitting the unrelated change (notes.md)",
              mentions(notes(repo), r"split|separate (pr|pull request)|own (pr|pull request)"), "checked"),
    ]


def eval_misleading(repo):
    text = body(repo)
    return [
        created(repo),
        title_type(repo, "fix"),
        check("Body describes the dropped-last-row bug", mentions(text, r"last (row|line)|trailing newline|final newline"),
              text[:200] or "no body"),
    ]


SPECIFIC = {
    "feature-from-branch": eval_feature,
    "repo-template": eval_template,
    "hidden-breaking-cleanup": eval_breaking,
    "stale-local-main": eval_stale_main,
    "commitlint-title": eval_commitlint,
    "existing-pr-update": eval_existing,
    "uncommitted-work": eval_uncommitted,
    "mixed-concerns": eval_mixed,
    "misleading-subjects": eval_misleading,
}


def write_run_info(iteration, model):
    dirty = git(ROOT, "status", "--porcelain", "--", f"skills/{SKILL}").strip()
    (Path(iteration) / "run.json").write_text(json.dumps({
        "skill": SKILL,
        "skill_sha": git(ROOT, "rev-parse", "HEAD").strip(),
        "skill_dirty": bool(dirty),
        "model": model,
        "graded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }, indent=2))


def main(iteration, model=None):
    write_run_info(iteration, model)
    for eval_dir in sorted(Path(iteration).glob("eval-*")):
        name = eval_dir.name.split("-", 2)[2]  # eval-<id>-<name>
        for run_dir in sorted(eval_dir.glob("*/run-*")):
            repo = run_dir / "outputs" / "repo"
            exps = common(repo) + SPECIFIC[name](repo)
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
    parser = argparse.ArgumentParser(description="Grade an eval iteration.")
    parser.add_argument("iteration")
    parser.add_argument("--model", help="model the runs used, recorded in run.json")
    args = parser.parse_args()
    main(args.iteration, args.model)
