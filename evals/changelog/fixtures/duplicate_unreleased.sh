#!/bin/bash
# The JSON export commit already added its own [Unreleased] entry; the fix after it didn't.
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

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] - 2026-01-01

### Added

- CSV export for reports.

[Unreleased]: https://github.com/acme/widget/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/acme/widget/releases/tag/v1.2.0
P
git add -A; c 1 "feat(export): add CSV export for reports"; git tag v1.2.0
cat >> widget/export.py <<'P'


def to_json(rows):
    import json
    return json.dumps(rows)
P
sedi 's/^## \[Unreleased\]$/## [Unreleased]\
\
### Added\
\
- `to_json` exports reports as JSON./' CHANGELOG.md
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
