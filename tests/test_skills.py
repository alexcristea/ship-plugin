"""Checks the shipped skills without running Claude: frontmatter parses under strict YAML.

usage: python3 -m unittest discover -s tests
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"

# A plain (unquoted) YAML scalar may not contain ": " or " #", nor end with ":".
# Claude Code tolerates these, but GitHub and other strict parsers reject the whole frontmatter.
PLAIN_SCALAR_BREAKERS = re.compile(r": | #|:$")


def frontmatter(path):
    lines = path.read_text().splitlines()
    if lines[0] != "---":
        raise ValueError(f"{path}: no frontmatter")
    return lines[1:lines.index("---", 1)]


class FrontmatterIsStrictYaml(unittest.TestCase):
    def test_skills_exist(self):
        self.assertTrue(sorted(SKILLS.glob("*/SKILL.md")), "no skills/<name>/SKILL.md found")

    def test_description_is_a_folded_block_scalar(self):
        # Descriptions are long prose that gets edited during trigger tuning; a folded
        # scalar lets them contain ": " and " #" without the author thinking about YAML.
        for path in sorted(SKILLS.glob("*/SKILL.md")):
            with self.subTest(skill=path.parent.name):
                self.assertTrue("description: >-" in frontmatter(path),
                                f"{path.relative_to(ROOT)}: write description as 'description: >-' "
                                "with the text indented on the following lines")

    def test_plain_values_have_no_yaml_indicators(self):
        for path in sorted(SKILLS.glob("*/SKILL.md")):
            for number, line in enumerate(frontmatter(path), start=2):
                key, sep, value = line.partition(": ")
                if not sep or line.startswith((" ", "#")):
                    continue
                value = value.strip()
                if value[:1] in ("'", '"', ">", "|"):
                    continue
                with self.subTest(skill=path.parent.name, key=key):
                    match = PLAIN_SCALAR_BREAKERS.search(value)
                    self.assertIsNone(
                        match,
                        f"{path.relative_to(ROOT)}:{number} unquoted {key} contains {match and match.group()!r}; "
                        "use a folded block scalar (>-) or quote it",
                    )


if __name__ == "__main__":
    unittest.main()
