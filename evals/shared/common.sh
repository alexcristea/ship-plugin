# usage: source common.sh <repo_path>
set -e
REPO="$(cd "$(dirname "$1")" 2>/dev/null && pwd || (mkdir -p "$(dirname "$1")" && cd "$(dirname "$1")" && pwd))/$(basename "$1")"; rm -rf "$REPO"; mkdir -p "$REPO"; cd "$REPO"
git init -q -b main
git config user.name "Test User"; git config user.email "test@example.com"
git config commit.gpgsign false
c() { GIT_AUTHOR_DATE="2026-01-0$1T10:00:00" GIT_COMMITTER_DATE="2026-01-0$1T10:00:00" git commit -q -m "$2"; }
# in-place sed for both BSD (macOS) and GNU (Linux) sed: sedi <script> <file>
sedi() { sed -i.bak "$1" "$2" && rm -f "$2.bak"; }
