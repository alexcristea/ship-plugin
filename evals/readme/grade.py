"""Grade readme eval runs by inspecting each run's README.md and git repo.

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
NPM_RE = re.compile(r"\bnpm (?:run(?:-script)? ([\w:.-]+)|(start|test|t|stop|restart)\b)")


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True).stdout


def check(text, passed, evidence):
    return {"text": text, "passed": bool(passed), "evidence": evidence}


def readme(repo):
    path = repo / "README.md"
    return path.read_text() if path.exists() else ""


def original(repo):
    """README.md as the fixture left it ("" if there was none)."""
    return git(repo, "show", git(repo, "config", "fixture.head").strip() + ":README.md")


def notes(repo):
    path = repo.parent / "notes.md"
    return path.read_text() if path.exists() else ""


def env_example(repo):
    return re.findall(r"^([A-Z][A-Z0-9_]*)=", (repo / ".env.example").read_text(), re.M)


def npm_commands(text):
    """Scripts the README runs: `npm run x` -> x, `npm start` / `npm test` -> start / test."""
    return [run or {"t": "test"}.get(short, short) for run, short in NPM_RE.findall(text)]


def section(text, title):
    """Body of the first `#` heading matching title (a regex), up to the next heading of any level."""
    m = re.search(rf"^#+ .*(?:{title}).*$", text, re.M | re.I)
    if not m:
        return ""
    rest = text[m.end():]
    end = re.search(r"^#", rest, re.M)
    return rest[:end.start()] if end else rest


def migrated_before_run(text):
    migrate, run = text.find("npm run db:migrate"), text.find("npm run dev")
    return 0 <= migrate < run, f"db:migrate at {migrate}, dev at {run}"


def common(repo):
    head = git(repo, "config", "fixture.head").strip()
    changed = set(git(repo, "diff", "--name-only", head).split()) | \
        set(git(repo, "ls-files", "--others", "--exclude-standard").split())
    scripts = json.loads((repo / "package.json").read_text())["scripts"]
    missing = sorted(set(npm_commands(readme(repo))) - set(scripts))
    secrets = [s for s in git(repo, "config", "--get-all", "fixture.secret").split() if s in readme(repo)]
    return [
        check("Only README.md was changed", changed <= {"README.md"}, sorted(changed) or "nothing changed"),
        check("Nothing committed", git(repo, "rev-parse", "HEAD").strip() == head, git(repo, "log", "--oneline", "-1")),
        check("README shown for review (notes.md)", "```" in notes(repo),
              "code block in notes.md" if "```" in notes(repo) else "no code block"),
        check("Every npm command in the README exists in package.json", not missing, missing or "all exist"),
        check("No secret value copied from .env", not secrets, secrets or "none found"),
    ]


def eval_new(repo):
    text = readme(repo)
    quick = re.search(r"^#+ .*(quick ?start|getting started|set ?up|install)", text, re.M | re.I)
    ordered, where = migrated_before_run(text)
    compose = re.search(r"docker[ -]compose up", text)
    undocumented = [name for name in env_example(repo) if name not in text]
    words = len(text.split())
    return [
        check("README.md created with a quick start section", text and quick, quick and quick.group() or "none"),
        check("Database started and migrated before the app runs", compose and ordered,
              f"docker compose: {bool(compose)}, {where}"),
        check("Node 22 named as a prerequisite", re.search(r"node\D{0,15}22", text, re.I),
              re.findall(r"node[^\n]{0,20}", text, re.I)[:3]),
        check("Every variable in .env.example documented", not undocumented, undocumented or "all documented"),
        check("Concise (at most 600 words)", words <= 600, f"{words} words"),
    ]


def eval_stale(repo):
    text, before = readme(repo), original(repo)
    ordered, where = migrated_before_run(text)
    on_call = section(before, "on-call").strip()
    headings = [h for h in re.findall(r"^#+ (.+)$", before, re.M) if h.lower() not in text.lower()]
    return [
        check("Node version updated to 22", re.search(r"node\D{0,15}22", text, re.I) and not re.search(r"node\D{0,15}18", text, re.I),
              re.findall(r"node[^\n]{0,20}", text, re.I)[:3]),
        check("Migration step added before the app runs", ordered, where),
        check("SENDGRID_WEBHOOK_SECRET documented", "SENDGRID_WEBHOOK_SECRET" in text, "present" if "SENDGRID_WEBHOOK_SECRET" in text else "missing"),
        check("On-call section kept as written", on_call and on_call in text, "kept" if on_call in text else "edited or removed"),
        check("Existing headings kept", not headings, headings or "all kept"),
    ]


SPECIFIC = {
    "new-readme": eval_new,
    "stale-readme": eval_stale,
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
