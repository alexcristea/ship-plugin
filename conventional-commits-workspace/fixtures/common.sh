# usage: source common.sh <repo_path>
set -e
REPO="$1"; rm -rf "$REPO"; mkdir -p "$REPO"; cd "$REPO"
git init -q -b main
git config user.name "Test User"; git config user.email "test@example.com"
git config commit.gpgsign false
c() { GIT_AUTHOR_DATE="2026-01-0$1T10:00:00" GIT_COMMITTER_DATE="2026-01-0$1T10:00:00" git commit -q -m "$2"; }
