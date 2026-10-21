#!/bin/bash
# feat/tsv-export: to_tsv is committed, but the CLI wiring (--format tsv) is still an uncommitted edit to cli.py.
source "$(dirname "$0")/../base.sh" "$1"
git switch -q -c feat/tsv-export
cat >> widget/export.py <<'P'


def to_tsv(rows):
    return "".join("\t".join(map(str, row)) + "\n" for row in rows)
P
git add -A; c 3 "feat(export): add TSV export"
sedi 's/from widget.export import to_csv/from widget.export import to_csv, to_tsv/' widget/cli.py
sedi 's/    args = parser.parse_args(argv)/    export.add_argument("--format", choices=["csv", "tsv"], default="csv")\
    args = parser.parse_args(argv)/' widget/cli.py
sedi 's/    text = to_csv(load_rows(args.report))/    text = (to_tsv if args.format == "tsv" else to_csv)(load_rows(args.report))/' widget/cli.py
record_pr
