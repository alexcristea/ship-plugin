# Shared start for PR fixtures (sourced, not a fixture itself): the widget CLI on main in two commits,
# pushed to a local bare origin, with a fake gh next to the repo. usage: source base.sh <repo_path>
source "$(dirname "${BASH_SOURCE[0]}")/../shared/common.sh" "$1"
local_origin; fake_gh
mkdir -p widget tests
touch widget/__init__.py
cat > widget/config.py <<'P'
import tomllib


def load(path="widget.toml"):
    with open(path, "rb") as f:
        return tomllib.load(f)["widget"]
P
git add -A; c 1 "feat(config): load settings from widget.toml"
cat > widget/export.py <<'P'
import csv
import io


def to_csv(rows):
    out = io.StringIO()
    csv.writer(out, lineterminator="\n").writerows(rows)
    return out.getvalue()
P
cat > widget/cli.py <<'P'
import argparse
import sys

from widget.export import to_csv


def main(argv=None):
    parser = argparse.ArgumentParser(prog="widget")
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export", help="export the rows of a report", allow_abbrev=False)
    export.add_argument("report")
    export.add_argument("--out", help="write to this file instead of stdout")
    args = parser.parse_args(argv)
    text = to_csv(load_rows(args.report))
    if args.out:
        with open(args.out, "w") as f:
            f.write(text)
    else:
        sys.stdout.write(text)


def load_rows(report):
    with open(report) as f:
        return [line.rstrip("\n").split("\t") for line in f]
P
cat > tests/test_export.py <<'P'
import unittest

from widget.export import to_csv


class ToCsv(unittest.TestCase):
    def test_quotes_fields_with_commas(self):
        self.assertEqual(to_csv([["a,b", "1"]]), '"a,b",1\n')
P
cat > README.md <<'P'
# widget

Export a tab-separated report as CSV:

    widget export report.tsv --out report.csv
P
git add -A; c 2 "feat(cli): add export command"
git push -q -u origin main
# call last: what the grader compares the run against
record_pr() {
  git config fixture.head "$(git rev-parse HEAD)"
  git config fixture.branch "$(git branch --show-current)"
  git config fixture.originmain "$(git rev-parse origin/main)"
  git config fixture.originbranch "$(git rev-parse -q --verify "origin/$(git branch --show-current)" || true)"
}
