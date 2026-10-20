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
        path.write_text(edit(path.read_text()))
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


if __name__ == "__main__":
    unittest.main()
