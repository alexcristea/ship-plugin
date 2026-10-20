#!/bin/bash
# 1.3.0 is written in the changelog but was never tagged; the last tag is still v1.2.0. One fix landed after it.
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
git add -A; c 2 "feat(export): add JSON export"
sedi 's/^## \[Unreleased\]$/## [Unreleased]\
\
## [1.3.0] - 2026-01-03\
\
### Added\
\
- JSON export for reports./' CHANGELOG.md
sedi 's#^\[Unreleased\]: .*#[Unreleased]: https://github.com/acme/widget/compare/v1.3.0...HEAD\
[1.3.0]: https://github.com/acme/widget/compare/v1.2.0...v1.3.0#' CHANGELOG.md
git add -A; c 3 "chore(release): 1.3.0"
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
git add -A; c 4 "fix(config): expand ~ in output_dir"
record_state
