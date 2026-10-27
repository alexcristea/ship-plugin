"""Checks the eval tooling without running Claude: definitions line up and graders score known runs correctly.

usage: python3 -m unittest discover -s tests
"""
import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"


def load_grader(skill):
    spec = importlib.util.spec_from_file_location(f"grade_{skill}", EVALS / skill / "grade.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def skills():
    return sorted(p.parent.name for p in EVALS.glob("*/cases.json"))


def cases(skill):
    return json.loads((EVALS / skill / "cases.json").read_text())["evals"]


class DefinitionsLineUp(unittest.TestCase):
    def test_at_least_one_skill_has_evals(self):
        self.assertTrue(skills(), "no evals/<skill>/cases.json found")

    def test_every_case_has_a_fixture_and_a_grader(self):
        for skill in skills():
            grade = load_grader(skill)
            for case in cases(skill):
                with self.subTest(skill=skill, case=case["name"]):
                    self.assertTrue((EVALS / skill / "fixtures" / case["fixture"]).is_file())
                    self.assertIn(case["name"], grade.SPECIFIC)

    def test_trigger_set_has_positives_and_near_misses(self):
        for skill in skills():
            with self.subTest(skill=skill):
                queries = json.loads((EVALS / skill / "triggers.json").read_text())
                self.assertTrue(any(q["should_trigger"] for q in queries))
                self.assertTrue(any(not q["should_trigger"] for q in queries))


class CommitGrader(unittest.TestCase):
    """Grades a bugfix-no-config run built from the real fixture, with a commit made by hand."""

    def setUp(self):
        self.grade = load_grader("commit")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.iteration = Path(tmp.name) / "iteration-1"
        self.run_dir = self.iteration / "eval-0-bugfix-no-config" / "with_skill" / "run-1"
        self.repo = self.run_dir / "outputs" / "repo"
        subprocess.run(["bash", str(EVALS / "commit" / "fixtures" / "bugfix_no_config.sh"), str(self.repo)],
                       check=True, capture_output=True)

    def grade_commit(self, message, **kwargs):
        subprocess.run(["git", "-C", str(self.repo), "commit", "-q", "-m", message], check=True)
        (self.run_dir / "outputs" / "notes.md").write_text(f"```\n{message}\n```\n")
        with contextlib.redirect_stdout(io.StringIO()):
            self.grade.main(self.iteration, **kwargs)
        return json.loads((self.run_dir / "grading.json").read_text())

    def test_good_commit_passes_every_check(self):
        result = self.grade_commit("fix(range): include the end date in dateRange")
        self.assertEqual(result["summary"]["failed"], 0, [e for e in result["expectations"] if not e["passed"]])

    def test_checks_are_the_assertions_listed_in_cases_json(self):
        result = self.grade_commit("fix(range): include the end date in dateRange")
        case = next(c for c in cases("commit") if c["name"] == "bugfix-no-config")
        self.assertEqual([e["text"] for e in result["expectations"]], case["assertions"])

    def test_bad_commit_fails_the_matching_checks(self):
        result = self.grade_commit("Fixed stuff.")
        failed = {e["text"] for e in result["expectations"] if not e["passed"]}
        self.assertEqual(failed, {
            "Every new commit header matches type(scope)!: description",
            "Descriptions start lowercase and have no trailing period",
            "Type is fix",
            "Scope reuses repo's existing 'range' scope",
        })

    def test_agent_attribution_fails_the_attribution_check(self):
        for trailer in ("Claude-Session: https://claude.ai/code/session_01ABC",
                        "Co-Authored-By: Claude <noreply@anthropic.com>",
                        "🤖 Generated with [Claude Code](https://claude.com/claude-code)"):
            with self.subTest(trailer=trailer):
                self.setUp()
                result = self.grade_commit(f"fix(range): include the end date in dateRange\n\n{trailer}")
                failed = {e["text"] for e in result["expectations"] if not e["passed"]}
                self.assertEqual(failed, {"Commit messages carry no agent attribution"})

    def test_records_skill_sha_and_model_for_the_iteration(self):
        self.grade_commit("fix(range): include the end date in dateRange", model="claude-opus-5-5")
        info = json.loads((self.iteration / "run.json").read_text())
        head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(info["skill"], "commit")
        self.assertEqual(info["skill_sha"], head)
        self.assertIsInstance(info["skill_dirty"], bool)
        self.assertEqual(info["model"], "claude-opus-5-5")
        self.assertIn("graded_at", info)

    def test_model_is_optional(self):
        self.grade_commit("fix(range): include the end date in dateRange")
        self.assertIsNone(json.loads((self.iteration / "run.json").read_text())["model"])


GOOD_UNRELEASED = """## [Unreleased]

### Added

- JSON export for reports.

### Changed

- CSV export streams rows to the output instead of building the whole file in memory.

### Fixed

- `~` in `output_dir` expands to the home directory.
"""

# new-changelog-from-history, as iteration 2's with_skill runs 2 and 3 wrote it
NEW_FOLDED = """## [Unreleased]

### Added

- Settings can be loaded from a `widget.toml` file. A file with no `[widget]` table is treated as empty settings instead of crashing.
- CSV export for reports. Fields that contain commas are quoted.
"""

NEW_SEPARATE = """## [Unreleased]

### Added

- Settings are loaded from `widget.toml`.
- CSV export for reports.

### Fixed

- A `widget.toml` without a `[widget]` table no longer crashes on load.
- CSV export quotes fields that contain commas.
"""

TILDE_FIX ="\n### Fixed\n\n- `~` in `output_dir` expands to the home directory.\n"

# breaking-footer-only, with the breaking changes marked inline (as the without_skill run did in iteration 1)
INLINE_BREAKING = """## [Unreleased]

### Added

- `--quiet` CLI flag to suppress progress output.

### Changed

- **BREAKING:** `WIDGET_*` environment variables now override settings in
  `widget.toml`. Unset the variable to keep the value from `widget.toml`.

### Removed

- **BREAKING:** the deprecated `/v1/reports` endpoint. Call `/v2/reports`,
  which returns the same fields plus paging.

### Fixed

- The CLI exits with status 1 on unknown flags.
"""

CALLOUT_BREAKING = """## [Unreleased]

### ⚠ Breaking changes

- `WIDGET_*` environment variables override `widget.toml`. Unset the variable to keep the file value.
- `/v1/reports` is removed. Call `/v2/reports`, which returns the same fields plus paging.

### Added

- `--quiet` CLI flag to suppress progress output.
"""


class ChangelogGrader(unittest.TestCase):
    """Grades runs built from the real fixtures, with CHANGELOG.md edited by hand."""

    def setUp(self):
        self.grade = load_grader("changelog")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.iteration = Path(tmp.name) / "iteration-1"

    def build(self, case):
        run_dir = self.iteration / f"eval-{case['id']}-{case['name']}" / "with_skill" / "run-1"
        repo = run_dir / "outputs" / "repo"
        subprocess.run(["bash", str(EVALS / "changelog" / "fixtures" / case["fixture"]), str(repo)],
                       check=True, capture_output=True)
        return run_dir, repo

    def grade_changelog(self, edit, name="update-since-last-tag"):
        run_dir, repo = self.build(next(c for c in cases("changelog") if c["name"] == name))
        path = repo / "CHANGELOG.md"
        path.write_text(edit(path.read_text() if path.exists() else ""))
        (run_dir / "outputs" / "notes.md").write_text(f"```diff\n{path.read_text()}```\n")
        with contextlib.redirect_stdout(io.StringIO()):
            self.grade.main(self.iteration)
        return json.loads((run_dir / "grading.json").read_text())

    def test_good_changelog_passes_every_check(self):
        result = self.grade_changelog(lambda text: text.replace("## [Unreleased]\n", GOOD_UNRELEASED))
        self.assertEqual(result["summary"]["failed"], 0, [e for e in result["expectations"] if not e["passed"]])

    def test_bad_changelog_fails_the_matching_checks(self):
        result = self.grade_changelog(lambda text: text
                                      .replace("## [Unreleased]\n", GOOD_UNRELEASED + "- Cache pip downloads in CI.\n")
                                      .replace("- CSV export for reports.", "- CSV export."))
        failed = {e["text"] for e in result["expectations"] if not e["passed"]}
        self.assertEqual(failed, {"Released sections from 1.2.0 down unchanged", "CI-only commit left out"})

    def test_streaming_change_under_added_counts(self):
        moved = GOOD_UNRELEASED.replace("### Changed\n\n- CSV export streams", "- CSV export streams")
        result = self.grade_changelog(lambda text: text.replace("## [Unreleased]\n", moved))
        self.assertEqual(result["summary"]["failed"], 0, [e for e in result["expectations"] if not e["passed"]])

    def grade_new(self, unreleased):
        return self.grade_changelog(lambda _: "# Changelog\n\n" + unreleased, "new-changelog-from-history")

    def test_fixes_folded_into_unreleased_features_count(self):
        result = self.grade_new(NEW_FOLDED)
        self.assertEqual(result["summary"]["failed"], 0, [e for e in result["expectations"] if not e["passed"]])

    def test_crash_fix_described_without_the_word_empty_counts(self):
        result = self.grade_new(NEW_SEPARATE)
        self.assertEqual(result["summary"]["failed"], 0, [e for e in result["expectations"] if not e["passed"]])

    def test_missing_fixes_fail(self):
        result = self.grade_new("## [Unreleased]\n\n### Added\n\n- Settings are loaded from `widget.toml`.\n- CSV export for reports.\n")
        failed = {e["text"] for e in result["expectations"] if not e["passed"]}
        self.assertEqual(failed, {"Both fixes recorded, including the non-conventional crash fix"})

    def grade_breaking(self, unreleased):
        return self.grade_changelog(lambda text: text.replace("## [Unreleased]\n", unreleased), "breaking-footer-only")

    def test_inline_breaking_markers_count_as_marked(self):
        result = self.grade_breaking(INLINE_BREAKING)
        self.assertEqual(result["summary"]["failed"], 0, [e for e in result["expectations"] if not e["passed"]])

    def test_breaking_changes_callout_counts_as_marked(self):
        result = self.grade_breaking(CALLOUT_BREAKING)
        self.assertEqual(result["summary"]["failed"], 0, [e for e in result["expectations"] if not e["passed"]])

    def test_unmarked_breaking_changes_fail_the_breaking_checks(self):
        result = self.grade_breaking(INLINE_BREAKING.replace("**BREAKING:** ", ""))
        failed = {e["text"] for e in result["expectations"] if not e["passed"]}
        self.assertEqual(failed, {
            "Footer-only env-over-file change marked as breaking",
            "/v1/reports removal marked as breaking",
            "Migration notes carried over from the footers",
        })

    # name: (entries a good run adds after "## [Unreleased]\n", entries a bad run adds, checks the bad run fails)
    HISTORY_TRAPS = {
        "revert-unreleased": (TILDE_FIX, "\n### Added\n\n- XML export for reports.\n" + TILDE_FIX,
                              {"Reverted XML export left out"}),
        "release-not-tagged": (TILDE_FIX, "\n### Added\n\n- JSON export for reports.\n" + TILDE_FIX,
                               {"JSON export from 1.3.0 not repeated under Unreleased"}),
        "duplicate-in-unreleased": (TILDE_FIX, "\n### Added\n\n- JSON export.\n" + TILDE_FIX,
                                    {"JSON export listed once"}),
    }

    def test_history_traps_pass_good_and_fail_bad_changelogs(self):
        for name, (good, bad, fails) in self.HISTORY_TRAPS.items():
            for entries, expected in ((good, set()), (bad, fails)):
                with self.subTest(case=name, expected=expected):
                    result = self.grade_changelog(lambda text: text.replace("## [Unreleased]\n", "## [Unreleased]\n" + entries), name)
                    self.assertEqual({e["text"] for e in result["expectations"] if not e["passed"]}, expected)

    def test_checks_are_the_assertions_listed_in_cases_json(self):
        for case in cases("changelog"):
            with self.subTest(case=case["name"]):
                run_dir, _ = self.build(case)
                with contextlib.redirect_stdout(io.StringIO()):
                    self.grade.main(self.iteration)
                result = json.loads((run_dir / "grading.json").read_text())
                self.assertEqual([e["text"] for e in result["expectations"]], case["assertions"])


class ChangelogFixtures(unittest.TestCase):
    """Fixtures must contain only the breaking changes their eval expects, or the grader rewards the wrong answer."""

    def test_update_since_tag_keeps_to_csv_backward_compatible(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            subprocess.run(["bash", str(EVALS / "changelog" / "fixtures" / "update_since_tag.sh"), str(repo)],
                           check=True, capture_output=True)
            out = subprocess.run(["python3", "-c", "from widget.export import to_csv; print(to_csv([['a,b', 1]]))"],
                                 cwd=repo, capture_output=True, text=True)
            self.assertEqual(out.stdout.strip(), '"a,b",1', out.stderr)




class SharedFixtureSetup(unittest.TestCase):
    """common.sh deletes the repo path it is given, so a missing path must stop it before it deletes the current directory."""

    def assert_refuses_and_keeps_cwd(self, cmd):
        with tempfile.TemporaryDirectory() as tmp:
            keep = Path(tmp) / "keep.txt"
            keep.write_text("work in progress\n")
            out = run(cmd, tmp)
            self.assertNotEqual(out.returncode, 0)
            self.assertIn("usage", out.stderr)
            self.assertTrue(keep.is_file(), "common.sh deleted the current directory")
            self.assertFalse((Path(tmp) / ".git").exists())

    def test_sourcing_without_a_path_refuses(self):
        self.assert_refuses_and_keeps_cwd(["bash", "-c", f'source "{EVALS / "shared" / "common.sh"}"'])

    def test_fixture_without_a_path_refuses(self):
        self.assert_refuses_and_keeps_cwd(["bash", str(EVALS / "commit" / "fixtures" / "bugfix_no_config.sh")])


class PrFixtures(unittest.TestCase):
    """PR fixtures must hold the trap their eval is about, and stay offline."""

    def build(self, fixture):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        repo = Path(tmp.name) / "outputs" / "repo"
        build_pr_fixture(fixture, repo)
        return repo

    def test_origin_is_a_visibly_local_repo(self):
        for fixture in sorted(p.name for p in (EVALS / "pr" / "fixtures").glob("*.sh")):
            with self.subTest(fixture=fixture):
                repo = self.build(fixture)
                url = run(["git", "remote", "get-url", "origin"], repo).stdout.strip()
                self.assertEqual(Path(url), repo.parent / "origin.git")
                self.assertEqual(run(["git", "config", "--get-regexp", "^url\\."], repo).stdout, "")

    def test_hidden_breaking_rejects_the_old_flag(self):
        repo = self.build("hidden_breaking.sh")
        (repo / "r.tsv").write_text("a\t1\n")
        out = run(["python3", "-c", "from widget.cli import main; main(['export', 'r.tsv', '--out', 'x.csv'])"], repo)
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("unrecognized arguments: --out", out.stderr)


def run(cmd, cwd, **kwargs):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, **kwargs)


def build_pr_fixture(fixture, repo):
    subprocess.run(["bash", str(EVALS / "pr" / "fixtures" / fixture), str(repo)], check=True, capture_output=True)


class FakeGh(unittest.TestCase):
    """The stand-in gh must fail where the real one fails, or evals reward runs that would break on GitHub."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name) / "outputs" / "repo"
        build_pr_fixture("feature_from_branch.sh", self.repo)
        self.gh = str(self.repo.parent / "bin" / "gh")

    def test_view_without_a_pr_fails_like_gh(self):
        out = run([self.gh, "pr", "view", "--json", "body"], self.repo)
        self.assertEqual(out.returncode, 1)
        self.assertIn("no pull requests found", out.stderr)

    def test_create_refuses_an_unpushed_branch(self):
        out = run([self.gh, "pr", "create", "--title", "feat: x", "--body", "b"], self.repo)
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("push the current branch", out.stderr)

    def test_create_then_edit_records_both_calls(self):
        run(["git", "push", "-q", "-u", "origin", "HEAD"], self.repo)
        created = run([self.gh, "pr", "create", "--title", "feat: x", "--body-file", "-"], self.repo, input="first")
        self.assertEqual(created.returncode, 0, created.stderr)
        run([self.gh, "pr", "edit", "--body", "second"], self.repo)
        out = run([self.gh, "pr", "view", "--json", "title,body", "--jq", ".body"], self.repo)
        self.assertEqual(out.stdout.strip(), "second")
        calls = (self.repo.parent / "gh" / "calls.jsonl").read_text().splitlines()
        self.assertEqual([json.loads(c)["cmd"] for c in calls], ["create", "edit"])

    def test_create_refuses_a_second_pr_for_the_branch(self):
        run(["git", "push", "-q", "-u", "origin", "HEAD"], self.repo)
        run([self.gh, "pr", "create", "--title", "feat: x", "--body", "b"], self.repo)
        out = run([self.gh, "pr", "create", "--title", "feat: y", "--body", "b"], self.repo)
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("already exists", out.stderr)

    def test_repo_view_reports_main_as_default_branch(self):
        out = run([self.gh, "repo", "view", "--json", "defaultBranchRef", "-q", ".defaultBranchRef.name"], self.repo)
        self.assertEqual(out.stdout.strip(), "main")


FEATURE_BODY = """## Summary

Finance reconciles reports in a spreadsheet tool that imports JSON but not CSV. This adds `widget export --format json`.

## Changes

- `--format json` writes the report as JSON. CSV stays the default.
- README documents `--format json`.

## Testing

- [x] `python -m unittest`

Closes #482
"""

TEMPLATE_BODY = """## Description

`load()` raised `KeyError` on a `widget.toml` without a `[widget]` table. It now returns empty settings.

## Type of change

- [x] Bug fix
- [ ] New feature
- [ ] Breaking change

## How has this been tested?

`python -m unittest`

## Checklist

- [x] Tests added or updated
- [ ] README updated if behavior changed
"""

BREAKING_BODY = """## Summary

Moves export parsing into `build_parser()` and renames `--out` to `--output`.

## ⚠ Breaking changes

- `--out` is no longer accepted. Use `--output` in scripts that call `widget export`.

## Testing

- [ ] `widget export r.tsv --output r.csv` writes the file
"""

UPLOAD_BODY = """## Summary

Uploads each export to S3 through a presigned URL, and retries 5xx responses with exponential backoff.

## Testing

- [x] `python -m unittest`
"""

# pr: a run that should pass every check, per case: (title, body, notes, gh pr subcommand)
PR_GOOD = {
    "feature-from-branch": ("feat(export): add JSON export", FEATURE_BODY, "Opened the PR.", "create"),
    "repo-template": ("fix(config): treat a config without [widget] as empty", TEMPLATE_BODY, "Opened the PR.", "create"),
    "hidden-breaking-cleanup": ("refactor(cli)!: rename --out to --output", BREAKING_BODY,
                                "This is a breaking change, not just a cleanup: --out was renamed.", "create"),
    "stale-local-main": ("fix(config): expand ~ in output_dir",
                         "## Summary\n\n`~` in `output_dir` now expands to the home directory.\n", "Opened the PR.", "create"),
    "commitlint-title": ("feat(config): read settings from widget.yaml",
                         "## Summary\n\nSettings can come from `widget.yaml` as well as `widget.toml`.\n", "Opened it.", "create"),
    "existing-pr-update": (None, UPLOAD_BODY, "Pushed the retry commits and updated #57.", "edit"),
    "uncommitted-work": ("feat(export): add TSV export", "## Summary\n\nAdds `to_tsv` for tab-separated export.\n",
                         "cli.py has uncommitted changes that are not in this PR.", "create"),
    "mixed-concerns": ("feat(export): add JSON export", "## Summary\n\nAdds `--format json`.\n",
                       "This branch also renames the config loader; consider splitting it into its own PR.", "create"),
    "misleading-subjects": ("fix(export): keep the last row when a report has no trailing newline",
                            "## Summary\n\n`load_rows` dropped the last row of reports without a final newline.\n",
                            "Opened.", "create"),
}


class PrGrader(unittest.TestCase):
    """Grades runs built from the real fixtures, with the branch pushed and the PR opened through the fake gh."""

    def setUp(self):
        self.grade = load_grader("pr")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.iteration = Path(tmp.name) / "iteration-1"

    def open_pr(self, name, title, body, notes, action="create"):
        case = next(c for c in cases("pr") if c["name"] == name)
        run_dir = self.iteration / f"eval-{case['id']}-{name}" / "with_skill" / "run-1"
        repo = run_dir / "outputs" / "repo"
        build_pr_fixture(case["fixture"], repo)
        gh = str(repo.parent / "bin" / "gh")
        run(["git", "push", "-q", "-u", "origin", "HEAD"], repo)
        cmd = [gh, "pr", action, "--body-file", "-"] + (["--title", title] if title else [])
        out = run(cmd, repo, input=body)
        self.assertEqual(out.returncode, 0, out.stderr)
        (run_dir / "outputs" / "notes.md").write_text(notes)
        with contextlib.redirect_stdout(io.StringIO()):
            self.grade.main(self.iteration)
        result = json.loads((run_dir / "grading.json").read_text())
        return {e["text"] for e in result["expectations"] if not e["passed"]}

    def test_good_runs_pass_every_check(self):
        for name, (title, body, notes, action) in PR_GOOD.items():
            with self.subTest(case=name):
                self.assertEqual(self.open_pr(name, title, body, notes, action), set())

    def test_long_untemplated_pr_fails_the_matching_checks(self):
        body = "## What\n\n" + "word " * 200 + "\n\n## Why\n\nFinance needs JSON in a spreadsheet.\n"
        self.assertEqual(self.open_pr("feature-from-branch", "Add JSON export", body, "Opened."), {
            "Title is a Conventional Commits header",
            "Body is concise (at most 200 words)",
            "Title type is feat",
            "Links the issue from the branch (Closes #482)",
            "Uses the default sections (Summary, Changes, Testing)",
        })

    # name: (title, body, notes, checks that fail)
    PR_BAD = {
        "hidden-breaking-cleanup": ("refactor(cli): tidy export flag parsing",
                                    "## Summary\n\nMoves export parsing into `build_parser()`.\n", "Opened.",
                                    {"Title marks the breaking change with !",
                                     "Body explains the break and the migration (--out to --output)",
                                     "Told the user it's a breaking change, not just a cleanup (notes.md)"}),
        "stale-local-main": ("fix(config): expand ~ in output_dir",
                             "## Summary\n\nExpands `~` in `output_dir`, and adds SSO login.\n", "Opened.",
                             {"Teammate's SSO commit on origin/main not described"}),
        "commitlint-title": ("feat(settings): support YAML configuration files alongside the existing TOML ones",
                             "## Summary\n\nReads `widget.yaml`.\n", "Opened.",
                             {"Title scope is in commitlint's scope-enum (or omitted)",
                              "Title at most 72 characters (header-max-length)"}),
        "uncommitted-work": ("feat(export): add TSV export",
                             "## Summary\n\nAdds `--format tsv` to `widget export`.\n", "Opened.",
                             {"Flagged the uncommitted cli.py change (notes.md)", "Body describes only what's pushed"}),
        "mixed-concerns": ("feat(export): add JSON export", "## Summary\n\nAdds JSON export.\n", "Opened.",
                           {"Suggested splitting the unrelated change (notes.md)"}),
        "misleading-subjects": ("chore: tidy export code", "## Summary\n\nTidies the export code.\n", "Opened.",
                                {"Title type is fix", "Body describes the dropped-last-row bug"}),
        "repo-template": ("fix(config): treat a config without [widget] as empty",
                          "## Summary\n\nFixes a crash on empty config.\n", "Opened.",
                          {"Body keeps the template's headings", "Bug fix box ticked"}),
    }

    def test_bad_runs_fail_the_matching_checks(self):
        for name, (title, body, notes, fails) in self.PR_BAD.items():
            with self.subTest(case=name):
                self.assertEqual(self.open_pr(name, title, body, notes), fails)

    def test_session_link_in_body_fails_the_attribution_check(self):
        body = FEATURE_BODY + "\nhttps://claude.ai/code/session_01ABC\n"
        self.assertEqual(self.open_pr("feature-from-branch", "feat(export): add JSON export", body, "Opened."),
                         {"PR description and new commits carry no agent attribution"})

    def test_attribution_trailer_on_a_new_commit_fails_the_attribution_check(self):
        case = next(c for c in cases("pr") if c["name"] == "uncommitted-work")
        run_dir = self.iteration / f"eval-{case['id']}-uncommitted-work" / "with_skill" / "run-1"
        repo = run_dir / "outputs" / "repo"
        build_pr_fixture(case["fixture"], repo)
        run(["git", "commit", "-qam", "feat(cli): add --format tsv\n\nCo-Authored-By: Claude <noreply@anthropic.com>"], repo)
        run(["git", "push", "-q", "-u", "origin", "HEAD"], repo)
        run([str(repo.parent / "bin" / "gh"), "pr", "create", "--title", "feat(export): add TSV export",
             "--body", "## Summary\n\nAdds `to_tsv` and `--format tsv`.\n"], repo)
        (run_dir / "outputs" / "notes.md").write_text("cli.py was uncommitted; committed it first.")
        with contextlib.redirect_stdout(io.StringIO()):
            self.grade.main(self.iteration)
        failed = {e["text"] for e in json.loads((run_dir / "grading.json").read_text())["expectations"] if not e["passed"]}
        self.assertEqual(failed, {"PR description and new commits carry no agent attribution"})

    def test_new_pr_instead_of_editing_the_open_one_fails(self):
        case = next(c for c in cases("pr") if c["name"] == "existing-pr-update")
        run_dir = self.iteration / f"eval-{case['id']}-existing-pr-update" / "with_skill" / "run-1"
        repo = run_dir / "outputs" / "repo"
        build_pr_fixture(case["fixture"], repo)
        (repo.parent / "gh" / "pr.json").unlink()  # as if the agent never looked for the open PR
        run(["git", "push", "-q", "origin", "HEAD"], repo)
        run([str(repo.parent / "bin" / "gh"), "pr", "create", "--title", "feat(export): retry uploads",
             "--body", "Retries uploads with backoff."], repo)
        (run_dir / "outputs" / "notes.md").write_text("Opened a PR.")
        with contextlib.redirect_stdout(io.StringIO()):
            self.grade.main(self.iteration)
        failed = {e["text"] for e in json.loads((run_dir / "grading.json").read_text())["expectations"] if not e["passed"]}
        self.assertIn("Existing PR #57 updated with gh pr edit, no new PR", failed)
        self.assertIn("Body still covers the S3 upload", failed)

    def test_unpushed_retries_flagged_in_notes_pass(self):
        case = next(c for c in cases("pr") if c["name"] == "existing-pr-update")
        run_dir = self.iteration / f"eval-{case['id']}-existing-pr-update" / "with_skill" / "run-1"
        repo = run_dir / "outputs" / "repo"
        build_pr_fixture(case["fixture"], repo)
        run([str(repo.parent / "bin" / "gh"), "pr", "edit", "57", "--body", UPLOAD_BODY], repo)
        (run_dir / "outputs" / "notes.md").write_text("The two retry commits are not pushed yet. Push them?")
        with contextlib.redirect_stdout(io.StringIO()):
            self.grade.main(self.iteration)
        failed = {e["text"] for e in json.loads((run_dir / "grading.json").read_text())["expectations"] if not e["passed"]}
        self.assertEqual(failed, set())

    def test_cli_wiring_named_as_left_out_passes(self):
        body = "## Summary\n\nAdds `to_tsv`. Wiring it into `export` (`--format tsv`) follows separately.\n"
        self.assertEqual(self.open_pr("uncommitted-work", "feat(export): add TSV export", body,
                                      "cli.py has uncommitted changes."), set())

    def test_cli_named_as_not_wired_up_yet_passes(self):
        # wording from iteration 4's with_skill runs, which left cli.py uncommitted
        body = ("## Changes\n\n- New `to_tsv(rows)`.\n- Not reachable from the CLI yet; `widget export` still writes CSV only.\n"
                "- The CLI doesn't call it yet.\n")
        self.assertEqual(self.open_pr("uncommitted-work", "feat(export): add TSV export", body,
                                      "cli.py has uncommitted changes."), set())

    def test_checks_are_the_assertions_listed_in_cases_json(self):
        for case in cases("pr"):
            with self.subTest(case=case["name"]):
                run_dir = self.iteration / f"eval-{case['id']}-{case['name']}" / "with_skill" / "run-1"
                build_pr_fixture(case["fixture"], run_dir / "outputs" / "repo")
                with contextlib.redirect_stdout(io.StringIO()):
                    self.grade.main(self.iteration)
                result = json.loads((run_dir / "grading.json").read_text())
                self.assertEqual([e["text"] for e in result["expectations"]], case["assertions"])


README_NEW = """# notify-service

Sends transactional emails for the Acme apps through SendGrid.

## Quick start

**Prerequisites:** Node 22 (see `.nvmrc`), Docker.

```sh
npm ci
cp .env.example .env
docker compose up -d db
npm run db:migrate
npm run dev
```

Run the tests with `npm test`.

## Configuration

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `DATABASE_URL` | yes | in `.env.example` | Postgres connection |
| `SENDGRID_API_KEY` | yes | | SendGrid key |
| `MAIL_FROM` | no | `no-reply@example.com` | Sender address |
| `PORT` | no | `3000` | HTTP port |
"""


class ReadmeGrader(unittest.TestCase):
    """Grades runs built from the real fixtures, with README.md written by hand."""

    def setUp(self):
        self.grade = load_grader("readme")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.iteration = Path(tmp.name) / "iteration-1"

    def grade_readme(self, name, edit):
        case = next(c for c in cases("readme") if c["name"] == name)
        run_dir = self.iteration / f"eval-{case['id']}-{case['name']}" / "with_skill" / "run-1"
        repo = run_dir / "outputs" / "repo"
        subprocess.run(["bash", str(EVALS / "readme" / "fixtures" / case["fixture"]), str(repo)],
                       check=True, capture_output=True)
        path = repo / "README.md"
        path.write_text(edit(path.read_text() if path.exists() else ""))
        (run_dir / "outputs" / "notes.md").write_text(f"```markdown\n{path.read_text()}```\n")
        with contextlib.redirect_stdout(io.StringIO()):
            self.grade.main(self.iteration)
        result = json.loads((run_dir / "grading.json").read_text())
        return case, result, {e["text"] for e in result["expectations"] if not e["passed"]}

    def test_good_new_readme_passes_every_check(self):
        _, _, failed = self.grade_readme("new-readme", lambda _: README_NEW)
        self.assertEqual(failed, set())

    def test_invented_start_and_copied_secret_fail(self):
        bad = README_NEW.replace("npm run dev", "npm start").replace("| SendGrid key", "| e.g. SG.live-4f9c2e7a1b8d6053")
        _, _, failed = self.grade_readme("new-readme", lambda _: bad)
        self.assertEqual(failed, {
            "Every npm command in the README exists in package.json",
            "No secret value copied from .env",
            "Database started and migrated before the app runs",
        })

    def test_warning_that_npm_start_is_gone_counts_as_correct(self):
        text = README_NEW + "\nThere is no `npm start` script; use `npm run dev`.\n"
        _, _, failed = self.grade_readme("new-readme", lambda _: text)
        self.assertEqual(failed, set())

    def test_npm_start_in_a_code_block_fails_even_beside_a_negation(self):
        text = README_NEW + "\nDon't forget:\n\n```sh\nnpm start   # not dev\n```\n"
        _, _, failed = self.grade_readme("new-readme", lambda _: text)
        self.assertEqual(failed, {"Every npm command in the README exists in package.json"})

    def test_long_readme_fails_concise(self):
        _, _, failed = self.grade_readme("new-readme", lambda _: README_NEW + "\nLorem ipsum." * 300)
        self.assertEqual(failed, {"Concise (at most 600 words)"})

    def fix_stale(self, text):
        return (text.replace("You need Node 18.", "You need Node 22 and Docker.")
                .replace("npm install", "npm ci")
                .replace("npm start", "docker compose up -d db\nnpm run db:migrate\nnpm run dev")
                .replace("- `MAIL_FROM`: sender address",
                         "- `MAIL_FROM`: sender address\n- `SENDGRID_WEBHOOK_SECRET`: signs SendGrid event webhooks"))

    def test_good_stale_update_passes_every_check(self):
        _, _, failed = self.grade_readme("stale-readme", self.fix_stale)
        self.assertEqual(failed, set())

    def test_rewrite_that_drops_on_call_and_keeps_stale_lines_fails(self):
        _, _, failed = self.grade_readme("stale-readme", lambda text: text.split("## On-call")[0])
        self.assertEqual(failed, {
            "Every npm command in the README exists in package.json",
            "Node version updated to 22",
            "Migration step added before the app runs",
            "SENDGRID_WEBHOOK_SECRET documented",
            "On-call section kept as written",
            "Existing headings kept",
        })

    def test_checks_are_the_assertions_listed_in_cases_json(self):
        for case in cases("readme"):
            with self.subTest(case=case["name"]):
                case, result, _ = self.grade_readme(case["name"], lambda text: text)
                self.assertEqual([e["text"] for e in result["expectations"]], case["assertions"])


if __name__ == "__main__":
    unittest.main()
