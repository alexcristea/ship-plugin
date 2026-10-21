#!/bin/bash
# wip/yaml-config: non-conventional commits on a branch, in a repo whose commitlint config limits scopes and header length.
source "$(dirname "$0")/../base.sh" "$1"
cat > commitlint.config.js <<'P'
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'scope-enum': [2, 'always', ['config', 'export', 'cli', 'deps']],
    'header-max-length': [2, 'always', 72],
  },
};
P
git add -A; c 3 "build: add commitlint config"
git push -q origin main
git switch -q -c wip/yaml-config
cat > widget/config.py <<'P'
import tomllib
from pathlib import Path

import yaml


def load(path="widget.toml"):
    if Path(path).suffix in (".yaml", ".yml"):
        with open(path) as f:
            return yaml.safe_load(f)["widget"]
    with open(path, "rb") as f:
        return tomllib.load(f)["widget"]
P
git add -A; c 4 "wip"
cat >> README.md <<'P'

Settings are read from `widget.toml`, or from `widget.yaml` if you prefer YAML.
P
git add -A; c 5 "add yaml support"
cat > tests/test_config.py <<'P'
import tempfile
import unittest

from widget.config import load


class Load(unittest.TestCase):
    def test_reads_yaml(self):
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write("widget:\n  output_dir: out\n")
        self.assertEqual(load(f.name), {"output_dir": "out"})
P
git add -A; c 6 "fix tests"
record_pr
