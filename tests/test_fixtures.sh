#!/bin/bash
# Builds every eval fixture into a scratch directory and checks that each one produced a git repo.
# usage: bash tests/test_fixtures.sh
set -u
root="$(cd "$(dirname "$0")/.." && pwd)"
out="$(mktemp -d)"; trap 'rm -rf "$out"' EXIT
fail=0; n=0
for f in "$root"/evals/*/fixtures/*.sh; do
  [ -e "$f" ] || continue
  n=$((n + 1))
  name="$(basename "$(dirname "$(dirname "$f")")")/$(basename "$f" .sh)"
  repo="$out/$name/repo"
  if bash "$f" "$repo" >/dev/null 2>&1 && git -C "$repo" rev-parse -q --verify HEAD >/dev/null; then
    echo "ok   $name"
  else
    echo "FAIL $name"; fail=1
  fi
done
[ "$n" -gt 0 ] || { echo "FAIL no fixtures found under evals/*/fixtures"; exit 1; }
exit $fail
