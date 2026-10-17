# Contributing to ship

This guide covers the repo layout, how to develop and test the plugin locally, and the conventions the project follows.

## Repository layout

```
ship-plugin/
├── .claude-plugin/
│   └── plugin.json                  # plugin manifest
├── skills/
│   └── commit/                      # ships with the plugin; keep it free of test material
│       ├── SKILL.md
│       └── references/spec.md
├── evals/                           # eval definitions: run Claude, cost money (committed)
│   ├── shared/
│   │   └── common.sh                # fixture setup shared by every skill
│   └── commit/
│       ├── cases.json               # behavior evals: prompt, fixture, assertions
│       ├── triggers.json            # 20 queries for checking the description
│       ├── fixtures/                # one script per eval; each builds a throwaway git repo
│       ├── grade.py                 # grades a finished iteration from its git repos
│       └── baseline.json            # last recorded scores, to compare changes against
├── tests/                           # deterministic checks of the eval tooling; no Claude
│   ├── test_fixtures.sh
│   └── test_grade.py
├── .eval-runs/                      # eval run output, one folder per skill (gitignored)
├── README.md
├── CONTRIBUTING.md
└── LICENSE
```

Evals and tests stay outside `skills/`. Claude can read anything in the skill folder while running the skill, so expected answers placed there could leak into real use.

The three kinds of file are kept apart because they run at different times:

- **`tests/`** is fast and free. Run it on every change.
- **`evals/`** runs Claude, so it is slow and costs money. Run it when a skill or its description changes.
- **`.eval-runs/`** is generated output with nested git repos. It is never committed. Only the summary in `baseline.json` is.

## Local development

1. Clone the repo.
2. Start Claude Code with the working tree loaded as a plugin, from a scratch repo rather than this one:

   ```sh
   cd /path/to/some/scratch-repo
   claude --plugin-dir /absolute/path/to/ship-plugin
   ```

3. After editing `SKILL.md`, restart the session so the new version loads. `references/spec.md` is read when the skill needs it, so changes to it apply on the next use.

## Changing the skill

Follow the TDD loop: add or tighten an eval that fails for the behavior you want, then change `SKILL.md` until it passes.

### Writing the description

The `description` in the frontmatter is all Claude sees when deciding whether to use the skill. Text in the body is read only after the skill has triggered, so trigger phrases there do nothing.

- Say what the skill does, and when to use it, in the words users actually say ("commit this", "what should I call this commit").
- Claude tends to under-trigger skills, so be explicit and a little pushy.
- Watch the near misses: squashing, undoing a commit, writing a changelog and setting up commitlint are git tasks that should *not* trigger the skill.
- Re-run the trigger eval (below) whenever you change the description.

### Writing the body

- Explain the reason behind a rule rather than writing it in capitals. For example, "pushing publishes the commit to others" is more useful than "NEVER PUSH".
- Rules belong in `SKILL.md`. Spec detail belongs in `references/spec.md`.
- Keep examples copy-paste valid. Every example message must pass `@commitlint/config-conventional`.

## Testing

### Tests

The tests check the eval tooling itself: every fixture builds, every case in `cases.json` has a fixture and a grader, and `grade.py` scores a known-good and a known-bad commit correctly. A bug in a grader would otherwise make every benchmark wrong without anyone noticing.

```sh
bash tests/test_fixtures.sh
python3 -m unittest discover -s tests
```

Run one test with `python3 -m unittest discover -s tests -k test_bad_commit_fails_the_matching_checks`.

CI (`.github/workflows/ci.yml`) runs these tests on Ubuntu and macOS, and runs `claude plugin validate .`, on every push to `main` and every pull request. It doesn't run the evals, because they need Claude and cost money.

### Behavior evals

Each entry in `evals/<skill>/cases.json` names a fixture, a user prompt and its assertions. The fixtures cover:

| Eval                               | What it checks                                                                  |
|------------------------------------|----------------------------------------------------------------------------------|
| `bugfix-no-config`                 | No config: falls back to the default types and reuses the scope from the log      |
| `commitlint-breaking-flag-rename`  | Follows `type-enum`, `scope-enum` and `header-max-length`; marks a renamed CLI flag as breaking |
| `unstaged-mixed-with-secret`       | Doesn't commit `.env`; splits an unrelated docs fix into its own commit           |
| `hook-rejects-missing-ticket`      | Reacts to a commit-msg hook rejection without `--no-verify`; adds `Refs:` from the branch |
| `hidden-breaking-in-refactor`      | Catches a breaking change in a "just a refactor" and commits the staged code unmodified |
| `revert-feature-under-later-fix`   | Reverts one commit and keeps a later fix                                          |
| `fix-messages-one-pushed`          | Rewords only the unpushed commit; doesn't force-push                              |

The evals run through the [skill-creator](https://github.com/anthropics/claude-plugins-official) plugin. In Claude Code, ask it to run the next iteration of the `commit` evals from `evals/commit/cases.json`, with `.eval-runs/commit/` as the workspace. Name both paths: by default skill-creator looks for `evals/evals.json` inside the skill and writes to `<skill>-workspace/`. For each eval and each configuration (`with_skill`, `without_skill`), it:

1. Builds the fixture repo:

   ```sh
   bash evals/commit/fixtures/<fixture>.sh \
     .eval-runs/commit/iteration-<N>/eval-<id>-<name>/<config>/run-1/outputs/repo
   ```

2. Runs a subagent on the prompt inside that repo. The user isn't available during the run, so the agent writes what it would have shown or asked to `outputs/notes.md` and continues as if the answer were "yes, go ahead". It must not push.
3. Grades the finished iteration:

   ```sh
   python3 evals/commit/grade.py .eval-runs/commit/iteration-<N> --model <model-id>
   ```

`grade.py` checks the resulting git history, tree and remote, then writes a `grading.json` next to each run. It also writes `run.json` in the iteration folder with the skill's commit SHA, whether `skills/<skill>/` had uncommitted changes, the model, and the time, so an old iteration can still be traced to what it tested. Use skill-creator's `aggregate_benchmark` and the eval viewer to compare the configurations.

When a change to the skill is accepted, update `evals/<skill>/baseline.json` with the new pass rates, SHA, model and date.

#### Adding an eval

1. Write `fixtures/<name>.sh`. Source `../../shared/common.sh`, create the history and stage the changes.
   - Fixtures must build on both macOS and Linux. To edit a file in place, use `sedi <script> <file>` from `common.sh`, not `sed -i`, which takes different arguments in BSD and GNU sed.
   - If the fixture doesn't start with two commits, record the starting count with `git config fixture.base <n>`.
   - Record anything the grader compares against with `git config fixture.<key>`. Git config keys can't contain underscores, so use names like `fixture.stagedtree`.
2. Add an entry to `cases.json` with `id`, `name`, `fixture`, `prompt` and `assertions`.
3. Add an `eval_<name>()` check function to `grade.py`, and register it in `SPECIFIC`.
4. Run `tests/`. They fail if the fixture doesn't build or the case has no grader.
5. Run the eval with and without the skill. A useful eval is one the without-skill run sometimes fails. If both configurations always pass, the eval doesn't tell them apart.

### Trigger eval

`evals/commit/triggers.json` has 10 queries that should trigger the skill and 10 near misses. Run it from skill-creator's `skills/skill-creator` directory:

```sh
python3 -m scripts.run_eval \
  --eval-set /abs/path/evals/commit/triggers.json \
  --skill-path /abs/path/skills/commit \
  --num-workers 1 --runs-per-query 2 --timeout 60 --verbose
```

Keep `--num-workers 1`. With parallel workers, every run writes a near-identical temporary skill into the same commands folder. Claude then picks another run's copy and the result is recorded as a miss, which made recall look like ~10% when it was really 95%. For the same reason, skill-creator's `run_loop` description optimizer isn't usable here yet.

A full serial run makes about 40 `claude -p` calls. Run it from a scratch directory that has its own `.claude/`, so the temporary commands don't land in `~/.claude/commands`.

## Commit messages

This repo uses Conventional Commits, with `ship` as the scope:

```
feat(ship): flag diffs that contradict the user's description
test(ship): add trigger eval set for the skill description
```

Use the plugin to write them.

## Pull requests

- Keep each PR to one concern. Changes to skill behavior should come with the eval that covers them.
- Include before and after eval scores for changes to `SKILL.md`, and trigger eval results for changes to the description.
- Update the README in the same PR when behavior changes.
