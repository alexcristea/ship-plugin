#!/bin/bash
# Existing CHANGELOG.md in conventional-changelog style (Features / Bug Fixes), with no tool that generates it.
source "$(dirname "$0")/../../shared/common.sh" "$1"
git remote add origin https://github.com/acme/widget.git
mkdir -p widget
cat > widget/export.py <<'P'
import csv
import io


def to_csv(rows):
    out = io.StringIO()
    csv.writer(out, lineterminator="\n").writerows(rows)
    return out.getvalue().rstrip("\n")
P
cat > CHANGELOG.md <<'P'
# Changelog

## [1.2.0](https://github.com/acme/widget/compare/v1.1.0...v1.2.0) (2026-01-01)


### Features

* **export:** add CSV export for reports


### Bug Fixes

* **export:** quote fields containing commas

## [1.1.0](https://github.com/acme/widget/compare/v1.0.0...v1.1.0) (2025-12-01)


### Features

* **config:** load settings from widget.toml
P
git add -A; c 1 "chore(release): 1.2.0"; git tag v1.2.0
cat >> widget/export.py <<'P'


def to_json(rows):
    import json
    return json.dumps(rows)
P
git add -A; c 2 "feat(export): add JSON export"
cat > widget/config.py <<'P'
import os
import tomllib


def load(path="widget.toml"):
    with open(path, "rb") as f:
        cfg = tomllib.load(f).get("widget", {})
    if "output_dir" in cfg:
        cfg["output_dir"] = os.path.expanduser(cfg["output_dir"])
    return cfg
P
git add -A; c 3 "fix(config): expand ~ in output_dir"
record_state
