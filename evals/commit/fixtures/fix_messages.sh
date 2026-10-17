#!/bin/bash
# Last two commits have bad messages; the older one is already pushed.
source "$(dirname "$0")/../../shared/common.sh" "$1"
git init -q --bare "$REPO.remote.git"
git remote add origin "$REPO.remote.git"
cat > parse.py <<'P'
def parse(line):
    key, value = line.split("=", 1)
    return key.strip(), value.strip()
P
git add -A; c 1 "feat: add key=value parser"
echo "# kvparse" > README.md; git add -A; c 2 "WIP"
git push -q -u origin main
cat > parse.py <<'P'
def parse(line):
    if not line or "=" not in line:
        return None
    key, value = line.split("=", 1)
    return key.strip(), value.strip()
P
git add -A; c 3 "Updated things."
git config fixture.base 2
git config fixture.pushed "$(git rev-parse HEAD~1)"
git config fixture.tree "$(git rev-parse HEAD^{tree})"
