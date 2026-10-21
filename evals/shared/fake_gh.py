#!/usr/bin/env python3
"""Stand-in for the GitHub CLI in evals: answers the gh calls a PR workflow makes, and records
`gh pr create` / `gh pr edit` instead of talking to GitHub.

fake_gh in common.sh copies this file to <outputs>/bin/gh. State lives in <outputs>/gh/:
  pr.json       the branch's open PR, if any (gh pr view prints it; create and edit write it)
  calls.jsonl   one line per pr create / pr edit call, for the grader
"""
import json
import re
import subprocess
import sys
from pathlib import Path

STATE = Path(__file__).resolve().parent.parent / "gh"
PR = STATE / "pr.json"
REPO = {"name": "widget", "owner": {"login": "acme"}, "nameWithOwner": "acme/widget",
        "url": "https://github.com/acme/widget", "defaultBranchRef": {"name": "main"}}
BOOLEAN = {"-d", "--draft", "-f", "--fill", "--fill-first", "--fill-verbose", "-w", "--web", "--dry-run", "-c", "--comments"}


def parse(args):
    """Split args into ({flag: value}, positionals). Flags take a value unless they are known booleans."""
    opts, pos, it = {}, [], iter(args)
    for a in it:
        if not a.startswith("-") or a == "-":
            pos.append(a)
        elif "=" in a:
            key, value = a.split("=", 1)
            opts[key] = value
        else:
            opts[a] = True if a in BOOLEAN else next(it, "")
    return opts, pos


def opt(opts, *names):
    return next((opts[n] for n in names if n in opts), None)


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout.strip()


def fail(message):
    print(message, file=sys.stderr)
    sys.exit(1)


def load_pr():
    return json.loads(PR.read_text()) if PR.exists() else None


def save(cmd, pr, **call):
    PR.write_text(json.dumps(pr, indent=2))
    with (STATE / "calls.jsonl").open("a") as f:
        f.write(json.dumps({"cmd": cmd, **call}) + "\n")


def body_from(opts):
    path = opt(opts, "-F", "--body-file")
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text() if path else opt(opts, "-b", "--body")


def show(data, opts, text):
    """Print data the way gh does: text without --json, else the requested fields, filtered by a simple --jq path."""
    fields = opt(opts, "--json")
    if not isinstance(fields, str):
        print(text)
        return
    data = {k: data.get(k) for k in fields.split(",")}
    jq = opt(opts, "-q", "--jq")
    if isinstance(jq, str) and re.fullmatch(r"(\.\w+)+", jq):
        for key in jq[1:].split("."):
            data = data.get(key) if isinstance(data, dict) else None
        print(data if isinstance(data, str) else json.dumps(data))
    else:
        print(json.dumps(data))


def branch():
    return git("branch", "--show-current")


def pr_view(opts):
    pr = load_pr()
    if not pr:
        fail(f'no pull requests found for branch "{branch()}"')
    show(pr, opts, f"{pr['title']} #{pr['number']}\n{pr['url']}\n\n{pr['body']}")


def pr_list(opts):
    prs, fields = [p for p in [load_pr()] if p], opt(opts, "--json")
    if isinstance(fields, str):
        print(json.dumps([{k: p.get(k) for k in fields.split(",")} for p in prs]))
        return
    for p in prs:
        print(f"#{p['number']}\t{p['title']}\t{p['headRefName']}\tOPEN")


def pr_create(opts):
    head, existing = branch(), load_pr()
    if existing:
        fail(f'a pull request for branch "{head}" into branch "main" already exists:\n{existing["url"]}')
    if not git("ls-remote", "origin", f"refs/heads/{head}"):
        fail("aborted: you must first push the current branch to a remote, or use the --head flag")
    title, body = opt(opts, "-t", "--title"), body_from(opts)
    if opt(opts, "-f", "--fill"):
        title, body = title or git("log", "-1", "--format=%s"), body if body is not None else git("log", "-1", "--format=%b")
    if not title or body is None:
        fail("must provide `--title` and `--body` (or `--fill`) when not running interactively")
    base = opt(opts, "-B", "--base") or "main"
    pr = {"number": 58, "title": title, "body": body, "url": f"{REPO['url']}/pull/58", "state": "OPEN",
          "headRefName": head, "baseRefName": base, "isDraft": bool(opt(opts, "-d", "--draft"))}
    save("create", pr, title=title, body=body, base=base, draft=pr["isDraft"])
    print(pr["url"])


def pr_edit(opts):
    pr = load_pr()
    if not pr:
        fail(f'no pull requests found for branch "{branch()}"')
    title, body = opt(opts, "-t", "--title"), body_from(opts)
    pr["title"] = title or pr["title"]
    pr["body"] = pr["body"] if body is None else body
    save("edit", pr, title=title, body=body)
    print(pr["url"])


def repo_view(opts):
    show(REPO, opts, f"{REPO['nameWithOwner']}\n{REPO['url']}")


def auth_status(opts):
    print("github.com\n  ✓ Logged in to github.com account test-user (keyring)", file=sys.stderr)


COMMANDS = {("pr", "view"): pr_view, ("pr", "list"): pr_list, ("pr", "create"): pr_create, ("pr", "edit"): pr_edit,
            ("repo", "view"): repo_view, ("auth", "status"): auth_status}


def main(argv):
    opts, pos = parse(argv)
    command = COMMANDS.get(tuple(pos[:2]))
    if not command:
        fail(f"gh {' '.join(argv)}: not available in this environment")
    command(opts)


if __name__ == "__main__":
    main(sys.argv[1:])
