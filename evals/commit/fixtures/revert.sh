#!/bin/bash
# Revert a feature commit that sits underneath a later, unrelated fix.
source "$(dirname "$0")/../../_shared/common.sh" "$1"
cat > server.py <<'P'
def handle(path, params):
    if path == "/health":
        return "ok"
    return fetch(path, params)


def fetch(path, params):
    return {"path": path, "params": params}
P
git add -A; c 1 "feat(api): add /health endpoint"
cat > cache.py <<'P'
_store = {}


def cached(fn):
    def wrapper(*args):
        key = repr(args)
        if key not in _store:
            _store[key] = fn(*args)
        return _store[key]
    return wrapper
P
cat > server.py <<'P'
from cache import cached


def handle(path, params):
    if path == "/health":
        return "ok"
    return fetch(path, params)


@cached
def fetch(path, params):
    return {"path": path, "params": params}
P
git add -A; c 2 "feat(cache): add in-memory response caching"
sed -i '' 's/^def handle(path, params):$/def handle(path, params):\n    if not isinstance(params, dict):\n        raise ValueError("params must be a dict")/' server.py
git add -A; c 3 "fix(api): validate query params"
git config fixture.base 3
git config fixture.reverted "$(git rev-parse HEAD~1)"
