#!/bin/bash
# Since v1.2.0: a feature, a fix, then a revert of that feature. The feature never shipped, so neither belongs in the changelog.
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


def to_xml(rows):
    cells = "".join("<row>" + "".join(f"<cell>{v}</cell>" for v in row) + "</row>" for row in rows)
    return f"<rows>{cells}</rows>"
P
git add -A; c 2 "feat(export): add XML export"
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
git revert --no-commit HEAD~1
c 4 "revert: feat(export): add XML export

The XML output doesn't escape cell values; it comes back once that's fixed.

This reverts commit $(git rev-parse --short HEAD~1)."
record_state
