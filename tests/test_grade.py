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

    def grade_commit(self, message):
        subprocess.run(["git", "-C", str(self.repo), "commit", "-q", "-m", message], check=True)
        (self.run_dir / "outputs" / "notes.md").write_text(f"```\n{message}\n```\n")
        with contextlib.redirect_stdout(io.StringIO()):
            self.grade.main(self.iteration)
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


if __name__ == "__main__":
    unittest.main()
