#!/bin/bash
# release-please owns CHANGELOG.md: hand edits would be overwritten or conflict with its release PR.
source "$(dirname "$0")/../../shared/common.sh" "$1"
git remote add origin https://github.com/acme/widget.git
mkdir -p widget
cat > release-please-config.json <<'P'
{
  "packages": { ".": { "release-type": "python", "changelog-path": "CHANGELOG.md" } }
}
P
echo '{ ".": "1.2.0" }' > .release-please-manifest.json
cat > widget/export.py <<'P'
def to_csv(rows):
    return "\n".join(",".join(str(v) for v in row) for row in rows)
P
cat > CHANGELOG.md <<'P'
# Changelog

## [1.2.0](https://github.com/acme/widget/compare/v1.1.0...v1.2.0) (2026-01-01)


### Features

* **export:** add CSV export for reports
P
git add -A; c 1 "chore(main): release 1.2.0"; git tag v1.2.0
cat >> widget/export.py <<'P'


def to_json(rows):
    import json
    return json.dumps(rows)
P
git add -A; c 2 "feat(export): add JSON export"
echo 'def expand(p): import os; return os.path.expanduser(p)' > widget/paths.py
git add -A; c 3 "fix(config): expand ~ in output_dir"
record_state
