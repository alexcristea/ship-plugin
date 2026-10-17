# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`ship` is a Claude Code plugin of git workflow skills. There is no build step and no application code: the product is prompt text in `skills/<name>/SKILL.md` (plus optional `references/`), and the manifest is `.claude-plugin/plugin.json`. Today there is one skill, `commit` (invoked as `/ship:commit`), which writes Conventional Commits 1.0.0 messages. More skills (pr, changelog, release, …) are planned, each in its own `skills/<name>/` folder with a matching `tests/<name>/` suite.

## Layout rules that aren't obvious

- **Eval material never goes under `skills/`.** Claude can read everything in a skill folder at runtime, so expected answers there would leak into real use. Evals live in `tests/<skill>/`.
- **Rules go in `SKILL.md`, spec detail in `references/spec.md`.** `SKILL.md` is loaded when the skill triggers; `references/` is read on demand.
- **Only the frontmatter `description` drives triggering.** Trigger phrases in the body do nothing. Near misses (squash, undo a commit, write a changelog, set up commitlint) must *not* trigger `commit`.
- Example commit messages in the skill must pass `@commitlint/config-conventional`.
- Explain the reason behind a rule instead of writing it in capitals.

## Commands

Validate the plugin manifest and layout:

```sh
claude plugin validate .
```

Try the plugin by hand (from a scratch repo, not this one; restart the session after editing `SKILL.md`):

```sh
claude --plugin-dir /absolute/path/to/this/repo
```

Build one eval fixture (a throwaway git repo) without running Claude:

```sh
bash tests/commit/fixtures/<fixture>.sh /path/to/scratch/<fixture>/repo
```

Grade a finished eval iteration (writes `grading.json` per run, prints pass counts):

```sh
python3 tests/commit/grade.py commit-workspace/iteration-<N>
```

Trigger eval for the description, run from skill-creator's `skills/skill-creator` directory. Keep `--num-workers 1`: parallel workers write near-identical temp skills to the same commands folder and corrupt results. Run from a scratch dir with its own `.claude/`.

```sh
python3 -m scripts.run_eval \
  --eval-set /abs/path/tests/commit/evals/trigger_eval.json \
  --skill-path /abs/path/skills/commit \
  --num-workers 1 --runs-per-query 2 --timeout 60 --verbose
```

## How the eval suite fits together

Behavior evals are run through the skill-creator plugin ("run the next iteration of the `commit` evals"), comparing `with_skill` and `without_skill`. Output goes to `<skill>-workspace/` (gitignored). The pieces are linked by name:

1. `tests/commit/evals/evals.json` — each entry has `id`, `name`, `fixture`, `prompt`, `assertions`.
2. `tests/commit/fixtures/<fixture>.sh` — sources `common.sh` (creates the repo, provides `c <day> <msg>` for dated commits), builds history and stages changes. Values the grader needs are stored with `git config fixture.<key>` (no underscores in keys). Fixtures are assumed to start with 2 commits; otherwise set `git config fixture.base <n>`.
3. Run dirs are `iteration-<N>/eval-<id>-<name>/<config>/run-1/outputs/repo`; the agent writes what it would have asked the user to `outputs/notes.md` and must not push.
4. `tests/commit/grade.py` — derives the eval name from the directory, runs `common()` checks plus the function registered for that name in `SPECIFIC`, by inspecting git history, tree and remote.

Adding an eval means touching all three: fixture script, `evals.json` entry, and an `eval_<name>()` function registered in `SPECIFIC`. A useful eval is one the baseline sometimes fails.

## Workflow conventions

- TDD for skill changes: add or tighten an eval that fails, then change `SKILL.md` until it passes. PRs changing `SKILL.md` include before/after eval scores; description changes include trigger eval results.
- Update `README.md` in the same change when behavior changes.
- Commits use Conventional Commits; see `CONTRIBUTING.md` for the scope.
