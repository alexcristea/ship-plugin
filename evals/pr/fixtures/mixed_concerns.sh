#!/bin/bash
# feat/json-export also carries an unrelated config fix: a branch that should be two PRs.
source "$(dirname "$0")/../base.sh" "$1"
git switch -q -c feat/json-export
cat >> widget/export.py <<'P'


def to_json(rows):
    import json
    return json.dumps(rows)
P
git add -A; c 3 "feat(export): add JSON export"
cat > widget/config.py <<'P'
import os
import tomllib


def load(path="widget.toml"):
    with open(path, "rb") as f:
        cfg = tomllib.load(f)["widget"]
    if "output_dir" in cfg:
        cfg["output_dir"] = os.path.expanduser(cfg["output_dir"])
    return cfg
P
git add -A; c 4 "fix(config): expand ~ in output_dir"
record_pr
