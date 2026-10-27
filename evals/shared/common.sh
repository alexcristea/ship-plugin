# usage: source common.sh <repo_path>
set -e
# REPO is deleted below, and an empty path resolves to the current directory
[ -n "${1:-}" ] || { echo "usage: source common.sh <repo_path>" >&2; return 1 2>/dev/null || exit 1; }
SHARED="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$(dirname "$1")" 2>/dev/null && pwd || (mkdir -p "$(dirname "$1")" && cd "$(dirname "$1")" && pwd))/$(basename "$1")"; rm -rf "$REPO"; mkdir -p "$REPO"; cd "$REPO"
git init -q -b main
git config user.name "Test User"; git config user.email "test@example.com"
git config commit.gpgsign false
c() { GIT_AUTHOR_DATE="2026-01-0$1T10:00:00" GIT_COMMITTER_DATE="2026-01-0$1T10:00:00" git commit -q -m "$2"; }
# in-place sed for both BSD (macOS) and GNU (Linux) sed: sedi <script> <file>
sedi() { sed -i.bak "$1" "$2" && rm -f "$2.bak"; }
# record HEAD and tags once the fixture is built, so the grader can tell what the agent changed
record_state() { git config fixture.head "$(git rev-parse HEAD)"; git config fixture.tags "$(git tag | tr '\n' ' ')"; }
# origin is a bare repo next to the repo, by its local path, so pushes stay offline, nothing pretends to be
# GitHub, and the grader can read what was pushed: local_origin
local_origin() {
  local bare; bare="$(dirname "$REPO")/origin.git"
  rm -rf "$bare"; git init -q --bare "$bare"
  git remote add origin "$bare"
}
# stand-in GitHub CLI at <outputs>/bin/gh that records PR calls in <outputs>/gh/: fake_gh
fake_gh() {
  local out; out="$(dirname "$REPO")"
  rm -rf "$out/bin" "$out/gh"; mkdir -p "$out/bin" "$out/gh"
  cp "$SHARED/fake_gh.py" "$out/bin/gh"; chmod +x "$out/bin/gh"
}
# the branch already has an open PR; its gh JSON comes on stdin: open_pr <<'J' {...} J
open_pr() { cat > "$(dirname "$REPO")/gh/pr.json"; }
