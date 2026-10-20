#!/bin/bash
# No CHANGELOG.md and no tags. History mixes features, fixes, upkeep and two non-conventional messages.
source "$(dirname "$0")/../../shared/common.sh" "$1"
git remote add origin https://github.com/acme/widget.git
mkdir -p widget tests .github/workflows
cat > widget/config.py <<'P'
import tomllib


def load(path="widget.toml"):
    with open(path, "rb") as f:
        return tomllib.load(f)["widget"]
P
echo "# widget" > README.md
git add -A; c 1 "feat(config): load settings from widget.toml"
cat > widget/export.py <<'P'
def to_csv(rows):
    return "\n".join(",".join(str(v) for v in row) for row in rows)
P
git add -A; c 2 "feat(export): add CSV export for reports"
cat > .github/workflows/ci.yml <<'P'
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: python -m unittest
P
git add -A; c 3 "ci: run tests on Python 3.13"
sedi 's/return tomllib.load(f)\["widget"\]/return tomllib.load(f).get("widget", {})/' widget/config.py
git add -A; c 4 "Fixed crash on empty config file"
cat > tests/test_export.py <<'P'
import unittest

from widget.export import to_csv


class ToCsv(unittest.TestCase):
    def test_unicode_cells(self):
        self.assertEqual(to_csv([["café", "naïve"]]), "café,naïve")
P
git add -A; c 5 "test(export): cover unicode in CSV cells"
printf '# widget\n\nExport reports to CSV.\n' > README.md
git add -A; c 6 "Update README"
cat > widget/export.py <<'P'
import csv
import io


def to_csv(rows):
    out = io.StringIO()
    csv.writer(out, lineterminator="\n").writerows(rows)
    return out.getvalue().rstrip("\n")
P
git add -A; c 7 "fix(export): quote fields containing commas"
echo "ruff==0.6.0" > requirements-dev.txt
git add -A; c 8 "chore: bump dev dependencies"
record_state
