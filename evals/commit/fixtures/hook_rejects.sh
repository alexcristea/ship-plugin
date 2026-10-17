#!/bin/bash
# A commit-msg hook that really runs: header <= 50, lowercase subject,
# and a required "Refs: PROJ-<n>" footer (the ticket is in the branch name).
source "$(dirname "$0")/../../shared/common.sh" "$1"
mkdir -p uploader
cat > .commitlintrc.json <<'J'
{
  "extends": ["@commitlint/config-conventional"],
  "rules": {
    "header-max-length": [2, "always", 50],
    "references-empty": [2, "never"]
  },
  "parserPreset": { "parserOpts": { "issuePrefixes": ["PROJ-"] } }
}
J
cat > uploader/client.py <<'P'
import urllib.request


def upload(url, data):
    req = urllib.request.Request(url, data=data, method="PUT")
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status
P
git add -A; c 1 "chore: initial uploader"
git checkout -q -b feature/PROJ-482-retry-uploads
git commit -q --allow-empty -m "test(uploader): add upload smoke test

Refs: PROJ-470"
cat > .git/hooks/commit-msg <<'H'
#!/bin/sh
msg="$1"; header=$(head -n1 "$msg"); fail=0
if [ ${#header} -gt 50 ]; then echo "✖ header must not be longer than 50 characters, current length is ${#header} [header-max-length]"; fail=1; fi
echo "$header" | grep -Eq '^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(\([a-z0-9-]+\))?!?: [a-z]' || { echo "✖ header must match type(scope): lowercase subject [type-enum/subject-case]"; fail=1; }
grep -Eq '^Refs: PROJ-[0-9]+' "$msg" || { echo "✖ references may not be empty (expected a 'Refs: PROJ-<n>' footer) [references-empty]"; fail=1; }
[ $fail -eq 0 ] || { echo "✖ found problems — commit rejected (commitlint)"; exit 1; }
H
chmod +x .git/hooks/commit-msg
cat > uploader/client.py <<'P'
import time
import urllib.error
import urllib.request

RETRYABLE = {502, 503, 504}


def upload(url, data, attempts=3, backoff=0.5):
    """PUT data to url, retrying transient failures with exponential backoff."""
    for i in range(attempts):
        req = urllib.request.Request(url, data=data, method="PUT")
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status
        except urllib.error.HTTPError as e:
            if e.code not in RETRYABLE or i == attempts - 1:
                raise
        except urllib.error.URLError:
            if i == attempts - 1:
                raise
        time.sleep(backoff * 2 ** i)
P
git add -A
