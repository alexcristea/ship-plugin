#!/bin/bash
# A teammate's SSO commit is on origin/main but not on the stale local main; the branch starts from origin/main.
# Diffing against local main pulls the SSO change into the PR description.
source "$(dirname "$0")/../base.sh" "$1"
cat > widget/auth.py <<'P'
def login_with_sso(provider):
    return f"https://{provider}/oauth/authorize?client_id=widget"
P
git add -A; c 3 "feat(auth): add SSO login"
git push -q origin main
git reset -q --hard HEAD~1
git switch -q --no-track -c fix/tilde-output-dir origin/main
cat > widget/config.py <<'P'
import os
import tomllib


def load(path="widget.toml"):
    with open(path, "rb") as f:
        cfg = tomllib.load(f)["widget"]
    if "output_dir" in cfg:
        cfg["output_dir"] = os.path.expanduser(cfg["output_dir"])
    return cfg
P
git add -A; c 4 "fix(config): expand ~ in output_dir"
record_pr
