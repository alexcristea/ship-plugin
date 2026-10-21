#!/bin/bash
# The branch's commits say style/chore, but one of them fixes load_rows dropping a report's last row.
source "$(dirname "$0")/../base.sh" "$1"
sedi 's/        return \[line.rstrip("\\n").split("\\t") for line in f\]/        return [line.split("\\t") for line in f.read().split("\\n")[:-1]]/' widget/cli.py
git add -A; c 3 "refactor(cli): read the report in one go"
git push -q origin main
git switch -q -c tidy-export
sedi 's/^import sys$/import sys  # stdout for export/' widget/cli.py
git add -A; c 4 "style: format cli module"
sedi 's/        return \[line.split("\\t") for line in f.read().split("\\n")\[:-1\]\]/        return [line.split("\\t") for line in f.read().splitlines()]/' widget/cli.py
git add -A; c 5 "chore: tidy load_rows"
record_pr
