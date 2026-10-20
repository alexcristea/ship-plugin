#!/bin/bash
# Keep a Changelog file up to v1.2.0 (tagged), then a feature, a fix, a perf change and a CI-only commit.
source "$(dirname "$0")/../../shared/common.sh" "$1"
git remote add origin https://github.com/acme/widget.git
mkdir -p widget .github/workflows
cat > widget/config.py <<'P'
import tomllib


def load(path="widget.toml"):
    with open(path, "rb") as f:
        return tomllib.load(f).get("widget", {})
P
git add -A; c 1 "feat(config): load settings from widget.toml"; git tag v1.1.0
cat > widget/export.py <<'P'
import csv
import io


def to_csv(rows):
    out = io.StringIO()
    csv.writer(out, lineterminator="\n").writerows(rows)
    return out.getvalue().rstrip("\n")
P
git add -A; c 2 "feat(export): add CSV export for reports"
cat > CHANGELOG.md <<'P'
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] - 2026-01-03

### Added

- CSV export for reports.

### Fixed

- CSV export quotes fields that contain commas.

## [1.1.0] - 2026-01-01

### Added

- Settings are read from `widget.toml`.

[Unreleased]: https://github.com/acme/widget/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/acme/widget/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/acme/widget/releases/tag/v1.1.0
P
git add -A; c 3 "chore(release): 1.2.0"; git tag v1.2.0
cat >> widget/export.py <<'P'


def to_json(rows):
    import json
    return json.dumps(rows)
P
git add -A; c 4 "feat(export): add JSON export"
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
git add -A; c 5 "fix(config): expand ~ in output_dir"
cat > .github/workflows/ci.yml <<'P'
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
          cache: pip
      - run: python -m unittest
P
git add -A; c 6 "ci: cache pip downloads"
cat > widget/export.py <<'P'
import csv
import io
import json


def to_csv(rows, out=None):
    """Write rows to out as they are produced; without out, return the CSV text as before."""
    if out is None:
        buf = io.StringIO()
        to_csv(rows, buf)
        return buf.getvalue().rstrip("\n")
    csv.writer(out, lineterminator="\n").writerows(rows)


def to_json(rows):
    return json.dumps(rows)
P
git add -A; c 7 "perf(export): let to_csv stream rows to an output instead of building the file in memory"
record_state
