#!/bin/bash
# After v1.4.0: one breaking change marked only by a BREAKING CHANGE footer, one marked with `!`.
source "$(dirname "$0")/../../shared/common.sh" "$1"
git remote add origin https://github.com/acme/widget.git
mkdir -p widget
cat > widget/cli.py <<'P'
import argparse


def parser():
    p = argparse.ArgumentParser(prog="widget")
    p.add_argument("--output")
    return p
P
cat > widget/config.py <<'P'
import os
import tomllib


def load(path="widget.toml"):
    with open(path, "rb") as f:
        cfg = tomllib.load(f).get("widget", {})
    for key, value in os.environ.items():
        if key.startswith("WIDGET_"):
            cfg.setdefault(key[7:].lower(), value)
    return cfg
P
cat > widget/api.py <<'P'
ROUTES = {"/v1/reports": "reports_v1", "/v2/reports": "reports_v2"}
P
cat > CHANGELOG.md <<'P'
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.4.0] - 2026-01-01

### Added

- `/v2/reports` endpoint with paging.

### Deprecated

- `/v1/reports`. Use `/v2/reports` instead.

[Unreleased]: https://github.com/acme/widget/compare/v1.4.0...HEAD
[1.4.0]: https://github.com/acme/widget/releases/tag/v1.4.0
P
git add -A; c 1 "feat(api): add /v2/reports with paging"; git tag v1.4.0
sedi 's/    p.add_argument("--output")/    p.add_argument("--output")\
    p.add_argument("--quiet", action="store_true")/' widget/cli.py
git add -A; c 2 "feat(cli): add --quiet flag to suppress progress output"
sedi 's/cfg.setdefault(key\[7:\].lower(), value)/cfg[key[7:].lower()] = value/' widget/config.py
git add -A; c 3 "refactor(config): let environment variables override widget.toml

Matches twelve-factor conventions and makes container deploys simpler.

BREAKING CHANGE: a setting defined both in widget.toml and as a WIDGET_*
environment variable now takes the environment value. Unset the variable
to keep the value from widget.toml."
echo 'ROUTES = {"/v2/reports": "reports_v2"}' > widget/api.py
git add -A; c 4 "feat(api)!: remove the deprecated /v1/reports endpoint

BREAKING CHANGE: /v1/reports is gone. Call /v2/reports, which returns the
same fields plus paging."
cat >> widget/cli.py <<'P'


def main(argv=None):
    args, unknown = parser().parse_known_args(argv)
    if unknown:
        raise SystemExit(1)
    return args
P
git add -A; c 5 "fix(cli): exit with status 1 on unknown flags"
record_state
