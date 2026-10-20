#!/bin/bash
# The user asks for 1.3.0, but the commits since v1.2.0 include a breaking change (SemVer says 2.0.0).
source "$(dirname "$0")/../../shared/common.sh" "$1"
git remote add origin https://github.com/acme/widget.git
mkdir -p src
cat > package.json <<'P'
{
  "name": "widget",
  "version": "1.2.0",
  "bin": { "widget": "src/cli.js" }
}
P
cat > src/cli.js <<'P'
const args = require("minimist")(process.argv.slice(2));
module.exports = { out: args.out };
P
cat > src/export.js <<'P'
exports.toCsv = (rows) => rows.map((r) => r.join(",")).join("\n");
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
echo 'exports.toJson = (rows) => JSON.stringify(rows);' >> src/export.js
git add -A; c 2 "feat(export): add JSON export"
sedi 's/out: args.out/output: args.output/' src/cli.js
git add -A; c 3 "feat(cli)!: rename --out flag to --output

BREAKING CHANGE: --out is no longer accepted. Use --output instead."
echo 'exports.path = (p) => p.replace(/^~/, require("os").homedir());' > src/paths.js
git add -A; c 4 "fix(cli): expand ~ in --output paths"
record_state
