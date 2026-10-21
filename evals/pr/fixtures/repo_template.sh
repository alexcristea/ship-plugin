#!/bin/bash
# fix/empty-config-crash in a repo with .github/pull_request_template.md: the body should follow the template.
source "$(dirname "$0")/../base.sh" "$1"
mkdir -p .github
cat > .github/pull_request_template.md <<'P'
## Description

<!-- What does this change, and why? -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change

## How has this been tested?

<!-- Commands you ran, and anything reviewers should check by hand. -->

## Checklist

- [ ] Tests added or updated
- [ ] README updated if behavior changed
P
git add -A; c 3 "docs: add pull request template"
git push -q origin main
git switch -q -c fix/empty-config-crash
cat > widget/config.py <<'P'
import tomllib


def load(path="widget.toml"):
    with open(path, "rb") as f:
        return tomllib.load(f).get("widget", {})
P
cat > tests/test_config.py <<'P'
import tempfile
import unittest

from widget.config import load


class Load(unittest.TestCase):
    def test_file_without_widget_table_is_empty(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write("[report]\nname = 'x'\n")
        self.assertEqual(load(f.name), {})
P
git add -A; c 4 "fix(config): treat a widget.toml without a [widget] table as empty

A new project's widget.toml often has only [report] settings, and
load() raised KeyError on it."
record_pr
