---
name: readme
description: >-
  Create or update the project's README.md so a new teammate can go from a fresh clone to a running app and passing tests by following it top to bottom. Reads the manifests, scripts, CI config and .env.example to find the real setup, run and test commands, prerequisites and environment variables, and fixes what an existing README gets wrong while keeping its structure. Use this skill whenever the user wants a README written, started, fixed, refreshed or checked, says things like "write a README", "our README is out of date", "a new dev is starting, document how to set this up", "the setup steps in the README don't work anymore", or wants onboarding or getting-started docs for the repo. Not for changelogs, commit messages, PR descriptions, CONTRIBUTING.md or CLAUDE.md on their own, API reference or docstrings, or a GitHub profile README.
---

# README

Your job is to write or update `README.md` so that a new teammate can get the project running on day one without asking anyone, show the user the change, and leave it for them to review.

A README is an onboarding tool, not a brochure. The reader has just cloned the repo and wants to know three things, in order: what this is, how to get it running, and where to go next. Every command in it will be pasted into a terminal, so a wrong one costs the reader more than a missing one. Start from `references/template.md`. `references/example.md` shows a finished one.

## 1. Find out how the project really works

Read the files that run the project, not the old README. Old docs drift; scripts and CI are what actually runs.

```bash
git ls-files | head -100
ls -a
cat package.json pyproject.toml Cargo.toml go.mod Gemfile composer.json 2>/dev/null | head -80
cat Makefile justfile Taskfile.yml 2>/dev/null | head -60
cat .nvmrc .node-version .python-version .tool-versions .ruby-version 2>/dev/null
cat .env.example .env.sample .env.template 2>/dev/null
ls docker-compose*.yml compose*.yml .devcontainer 2>/dev/null
cat .github/workflows/*.yml .gitlab-ci.yml 2>/dev/null | head -80
ls docs CONTRIBUTING.md LICENSE* 2>/dev/null
```

Collect:

- **Prerequisites with versions:** from `engines`, `requires-python`, `.nvmrc`, `.tool-versions`, the CI image. Name services the app needs (Postgres, Redis) and how they're started, usually `docker compose up`.
- **Commands:** install, run, test, lint, migrate, seed. Take them from the scripts, Makefile or task runner, and check them against CI. Use the package manager the lockfile shows (`package-lock.json` → npm, `pnpm-lock.yaml` → pnpm, `uv.lock` → uv).
- **Environment variables:** names, defaults and purpose from `.env.example` or the code that reads them. Never open `.env` or copy values from it: it holds real secrets, and a README is read by everyone with access to the repo.
- **Layout:** the top-level folders and what lives in each.
- **Existing docs** to link to rather than repeat: `CONTRIBUTING.md`, `docs/`, an architecture note.

If you can run the setup cheaply (install, tests), do it, and fix the README to match what happened. If you can't, say which commands you didn't run.

## 2. Create or update

**No README, or a one-line stub:** write one from `references/template.md`.

**A README already exists:** update it, don't replace it. Keep its order, headings, tone and any section you can't verify from the code (deploy notes, on-call, team contacts), because those were written by people who know things the repo doesn't show. Then:

- Fix every command, version and path that no longer matches the project. These are the lines that make a new teammate stuck.
- Add what's missing for onboarding: usually prerequisites, environment variables or how to run the tests.
- Remove instructions for things that are gone (a deleted script, a retired service). Mention each removal when you report back.
- Leave alone what is still correct, even if you'd phrase it differently. A smaller diff is easier for the user to review.

## 3. Write it

- **First screen:** the name and one or two sentences on what the project does and who uses it. A reader should know whether they're in the right repo before scrolling.
- **Quick start is the core.** Numbered steps from a fresh clone to a running app and a passing test run, every command in a code block that can be pasted as is. Put one-time setup (install, copy `.env.example`, start the database, migrate) before the run command, in the order it has to happen.
- **Only real commands.** Every command must exist in the scripts, Makefile or toolchain you read in step 1. Don't write `npm start` because most projects have it; if the script is `dev`, write `npm run dev`. If you can't find how something is done (deploying, getting credentials), don't guess. Leave a `<!-- TODO: ... -->` in that spot and ask the user.
- **Environment variables** go in a table: name, whether it's required, default, what it's for and where to get it. Names only, never secret values.
- **Concise.** Aim for something a newcomer reads in five minutes, roughly 300 to 600 words for a typical service. Link to `CONTRIBUTING.md` or `docs/` for detail instead of copying it, since two copies drift apart. Leave out sections that would be empty, generic advice ("make sure you have git installed") and badges the repo doesn't already have.
- **Where to get help:** keep or add who owns the project and where to ask. If the repo doesn't say, leave a TODO for the user to fill in rather than inventing a channel.

## 4. Report back

Show the user the change as a diff in a fenced code block (`git diff README.md`, or the whole file if it's new). Then list:

- commands you couldn't verify, or didn't run
- the TODOs you left and what you need from them to fill each in
- anything you removed from an existing README and why

Leave the file uncommitted so the user can edit it first. Offer to commit it with `docs(readme): add setup and onboarding guide` (or `docs(readme): update setup steps`), following the repo's commit conventions if they ask. Keep the commit message agent-agnostic, as `/ship:commit` does. Never push.
