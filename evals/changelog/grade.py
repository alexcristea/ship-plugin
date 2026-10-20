"""Grade changelog eval runs by inspecting each run's CHANGELOG.md and git repo.

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
LINK_RE = re.compile(r"^\[[^\]]+\]: ", re.M)  # link reference definitions at the bottom of the file


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True).stdout


def check(text, passed, evidence):
    return {"text": text, "passed": bool(passed), "evidence": evidence}


def changelog(repo):
    path = repo / "CHANGELOG.md"
    return path.read_text() if path.exists() else ""


def original(repo):
    """CHANGELOG.md as the fixture left it."""
    return git(repo, "show", git(repo, "config", "fixture.head").strip() + ":CHANGELOG.md")


def notes(repo):
    path = repo.parent / "notes.md"
    return path.read_text() if path.exists() else ""


def block(text, version):
    """Body of the `## [version]` section, up to the next `## ` heading or the link definitions."""
    m = re.search(rf"^## \[?{re.escape(version)}\b.*$", text, re.M | re.I)
    if not m:
        return ""
    rest = text[m.end():]
    end = re.search(r"^## ", rest, re.M) or LINK_RE.search(rest)
    return rest[:end.start()] if end else rest


def subsection(text, title):
    """Body of the first `### ...title...` heading (title is a regex), up to the next heading."""
    m = re.search(rf"^### .*(?:{title}).*$", text, re.M | re.I)
    if not m:
        return ""
    rest = text[m.end():]
    end = re.search(r"^##", rest, re.M)
    return rest[:end.start()] if end else rest


def breaking_notes(text):
    """Text marked as breaking: a `### ...breaking...` callout plus any entry flagged BREAKING inline."""
    entries = re.split(r"^(?=[-*] |#)", text, flags=re.M)  # each bullet with its continuation lines
    inline = "".join(e for e in entries if not e.startswith("#") and "breaking" in e.lower())
    return (subsection(text, "breaking") + inline).lower()


def released(text, since):
    """Everything from the `## [since]` heading down to the link definitions: history that must not change."""
    m = re.search(rf"^## \[?{re.escape(since)}\b", text, re.M)
    if not m:
        return ""
    rest = text[m.start():]
    end = LINK_RE.search(rest)
    return (rest[:end.start()] if end else rest).strip()


def unchanged(repo, since):
    same = released(changelog(repo), since) == released(original(repo), since)
    return check(f"Released sections from {since} down unchanged", same, "identical" if same else "edited")


def shown(repo):
    return check("Changelog changes shown for review (notes.md)", "```" in notes(repo),
                 "code block in notes.md" if "```" in notes(repo) else "no code block")


def common(repo):
    head = git(repo, "config", "fixture.head").strip()
    changed = set(git(repo, "diff", "--name-only", head).split()) | \
        set(git(repo, "ls-files", "--others", "--exclude-standard").split())
    tags = sorted(git(repo, "tag").split())
    return [
        check("Only CHANGELOG.md was changed", changed <= {"CHANGELOG.md"}, sorted(changed) or "nothing changed"),
        check("No tag was created", tags == sorted(git(repo, "config", "fixture.tags").split()), tags),
        check("Reported back to the user (notes.md)", notes(repo).strip(), "notes.md present" if notes(repo) else "no notes.md"),
    ]


def eval_new(repo):
    text = changelog(repo)
    unreleased = block(text, "Unreleased")
    added, fixed = subsection(unreleased, "Added"), subsection(unreleased, "Fixed").lower()
    return [
        shown(repo),
        check("CHANGELOG.md created with an [Unreleased] section", re.search(r"^## \[Unreleased\]", text, re.M),
              text[:200] or "no CHANGELOG.md"),
        check("Features listed under Added (CSV export, widget.toml)", "CSV" in added and "widget.toml" in added,
              added.strip()[:200] or "no Added section"),
        check("Fixes listed under Fixed, including the non-conventional crash fix", "comma" in fixed and "empty" in fixed,
              fixed.strip()[:200] or "no Fixed section"),
        check("CI, test and chore commits left out",
              not any(s in text.lower() for s in ("python 3.13", "unicode", "dev dependencies")), "checked"),
    ]


def eval_update(repo):
    text = changelog(repo)
    unreleased = block(text, "Unreleased")
    lower = unreleased.lower()
    changed = subsection(unreleased, "Changed").lower()
    return [
        shown(repo),
        unchanged(repo, "1.2.0"),
        check("New feature and fix added under Unreleased (JSON export, ~ in output_dir)",
              "json" in lower and ("~" in lower or "tilde" in lower or "home" in lower), unreleased.strip()[:200] or "empty"),
        check("Performance change listed under Changed", "stream" in changed or "memory" in changed,
              changed.strip()[:200] or "no Changed section"),
        check("Already released changes not repeated", "comma" not in lower, "checked"),
        check("CI-only commit left out", "pip" not in text.lower(), "checked"),
    ]


def eval_breaking(repo):
    unreleased = block(changelog(repo), "Unreleased")
    brk = breaking_notes(unreleased)
    return [
        shown(repo),
        unchanged(repo, "1.4.0"),
        check("Footer-only env-over-file change marked as breaking", "env" in brk,
              brk.strip()[:200] or "nothing marked breaking"),
        check("/v1/reports removal marked as breaking", "/v1/reports" in brk, brk.strip()[:200] or "nothing marked breaking"),
        check("Migration notes carried over from the footers",
              "/v2/reports" in brk and re.search(r"unset|remov\w* (the )?(env|variable)", brk), brk.strip()[:200] or "none"),
        check("New --quiet flag listed under Added", "--quiet" in subsection(unreleased, "Added"), "checked"),
    ]


def eval_cut(repo):
    text = changelog(repo)
    version, unreleased = block(text, "1.3.0"), block(text, "Unreleased")
    links = (re.search(r"^\[Unreleased\]: https://github\.com/acme/widget/compare/v1\.3\.0\.\.\.HEAD$", text, re.M)
             and re.search(r"^\[1\.3\.0\]: https://github\.com/acme/widget/compare/v1\.2\.0\.\.\.v1\.3\.0$", text, re.M))
    return [
        shown(repo),
        unchanged(repo, "1.2.0"),
        check("Dated 1.3.0 section added", re.search(r"^## \[1\.3\.0\] - \d{4}-\d{2}-\d{2}\s*$", text, re.M),
              "found" if version else "no 1.3.0 section"),
        check("Empty [Unreleased] kept above 1.3.0",
              "## [Unreleased]" in text and -1 < text.find("## [Unreleased]") < text.find("## [1.3.0]")
              and not re.search(r"^\s*[-*] ", unreleased, re.M), unreleased.strip()[:200] or "empty"),
        check("Changes moved into 1.3.0 (JSON export, --output rename)", "json" in version.lower() and "--output" in version,
              version.strip()[:200] or "none"),
        check("Compare links updated for 1.3.0", links, "found" if links else "missing or wrong"),
        check("Flagged that the breaking change calls for 2.0.0 (notes.md)",
              "2.0.0" in notes(repo) or "major" in notes(repo).lower(), "checked"),
    ]


def eval_conventional(repo):
    text = changelog(repo)
    new = text[:text.find("## [1.2.0]")]
    return [
        shown(repo),
        unchanged(repo, "1.2.0"),
        check("New entries use the file's Features / Bug Fixes headings",
              "json" in subsection(new, "Features").lower()
              and re.search(r"~|tilde|home", subsection(new, "Bug Fixes").lower()), new.strip()[:200] or "nothing added"),
        check("No Keep a Changelog headings introduced", not re.search(r"^### (Added|Fixed|Changed)\b", text, re.M), "checked"),
    ]


def eval_release_please(repo):
    same = changelog(repo) == original(repo)
    return [
        check("CHANGELOG.md left to release-please (unchanged)", same, "unchanged" if same else "hand-edited"),
        check("Explained that release-please generates the changelog (notes.md)",
              "release-please" in notes(repo).lower(), "checked"),
    ]


SPECIFIC = {
    "new-changelog-from-history": eval_new,
    "update-since-last-tag": eval_update,
    "breaking-footer-only": eval_breaking,
    "cut-version-mismatch": eval_cut,
    "existing-conventional-format": eval_conventional,
    "release-please-managed": eval_release_please,
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
