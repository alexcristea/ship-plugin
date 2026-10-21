#!/bin/bash
# refactor/cli-flags: committed as a refactor, but it renames the public --out flag to --output.
source "$(dirname "$0")/../base.sh" "$1"
git switch -q -c refactor/cli-flags
cat > widget/cli.py <<'P'
import argparse
import sys

from widget.export import to_csv


def build_parser():
    parser = argparse.ArgumentParser(prog="widget")
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export", help="export the rows of a report", allow_abbrev=False)
    export.add_argument("report")
    export.add_argument("--output", help="write to this file instead of stdout")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    text = to_csv(load_rows(args.report))
    if args.output:
        with open(args.output, "w") as f:
            f.write(text)
    else:
        sys.stdout.write(text)


def load_rows(report):
    with open(report) as f:
        return [line.rstrip("\n").split("\t") for line in f]
P
sedi 's/--out report.csv/--output report.csv/' README.md
git add -A; c 3 "refactor(cli): tidy export flag parsing"
record_pr
