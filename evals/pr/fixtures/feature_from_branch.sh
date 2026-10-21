#!/bin/bash
# feat/482-json-export: a feature whose reason is only in the commit body, its test and a README line. Nothing breaks.
source "$(dirname "$0")/../base.sh" "$1"
git switch -q -c feat/482-json-export
cat > widget/export.py <<'P'
import csv
import io
import json


def to_csv(rows):
    out = io.StringIO()
    csv.writer(out, lineterminator="\n").writerows(rows)
    return out.getvalue()


def to_json(rows):
    return json.dumps(rows)
P
cat > widget/cli.py <<'P'
import argparse
import sys

from widget.export import to_csv, to_json


def main(argv=None):
    parser = argparse.ArgumentParser(prog="widget")
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export", help="export the rows of a report", allow_abbrev=False)
    export.add_argument("report")
    export.add_argument("--out", help="write to this file instead of stdout")
    export.add_argument("--format", choices=["csv", "json"], default="csv")
    args = parser.parse_args(argv)
    text = (to_json if args.format == "json" else to_csv)(load_rows(args.report))
    if args.out:
        with open(args.out, "w") as f:
            f.write(text)
    else:
        sys.stdout.write(text)


def load_rows(report):
    with open(report) as f:
        return [line.rstrip("\n").split("\t") for line in f]
P
git add -A; c 3 "feat(export): add JSON export

Finance reconciles reports in a spreadsheet tool that imports JSON but
not CSV, so they have been converting every export by hand.

Refs: #482"
cat >> tests/test_export.py <<'P'


class ToJson(unittest.TestCase):
    def test_writes_rows_as_arrays(self):
        from widget.export import to_json
        self.assertEqual(to_json([["a", "1"]]), '[["a", "1"]]')
P
git add -A; c 4 "test(export): cover JSON export"
cat >> README.md <<'P'

Add `--format json` to write JSON instead.
P
git add -A; c 5 "docs: mention --format json in README"
record_pr
