# Contributing to commits

This guide covers the repo layout, how to develop and test the plugin locally, and the conventions the project follows.

## Repository layout

```
commits-plugin/
├── .claude-plugin/
│   └── plugin.json                  # plugin manifest
├── skills/
│   └── conventional-commits/        # ships with the plugin; keep it free of test material
│       ├── SKILL.md
│       └── references/spec.md
├── tests/
│   └── conventional-commits/        # eval suite (committed)
│       ├── evals/
│       │   ├── evals.json           # behavior evals: prompt, fixture, assertions
│       │   └── trigger_eval.json    # 20 queries for checking the description
│       ├── fixtures/                # one script per eval; each builds a throwaway git repo
│       │   └── common.sh            # shared setup sourced by every fixture
│       └── grade.py                 # grades a finished iteration from its git repos
├── conventional-commits-workspace/  # eval run output (gitignored)
├── README.md
└── CONTRIBUTING.md
```

The eval suite stays outside `skills/`. Claude can read anything in the skill folder while running the skill, so expected answers placed there could leak into real use.

## Local development

1. Clone the repo.
2. Start Claude Code with the working tree loaded as a plugin, from a scratch repo rather than this one:

   ```sh
   cd /path/to/some/scratch-repo
   claude --plugin-dir /absolute/path/to/commits-plugin
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

### Behavior evals

Each entry in `evals/evals.json` names a fixture, a user prompt and its assertions. The fixtures cover:

| Eval                               | What it checks                                                                  |
|------------------------------------|----------------------------------------------------------------------------------|
| `bugfix-no-config`                 | No config: falls back to the default types and reuses the scope from the log      |
| `commitlint-breaking-flag-rename`  | Follows `type-enum`, `scope-enum` and `header-max-length`; marks a renamed CLI flag as breaking |
| `unstaged-mixed-with-secret`       | Doesn't commit `.env`; splits an unrelated docs fix into its own commit           |
| `hook-rejects-missing-ticket`      | Reacts to a commit-msg hook rejection without `--no-verify`; adds `Refs:` from the branch |
| `hidden-breaking-in-refactor`      | Catches a breaking change in a "just a refactor" and commits the staged code unmodified |
| `revert-feature-under-later-fix`   | Reverts one commit and keeps a later fix                                          |
| `fix-messages-one-pushed`          | Rewords only the unpushed commit; doesn't force-push                              |

The evals run through the [skill-creator](https://github.com/anthropics/claude-plugins-official) plugin. In Claude Code, ask it to run the next iteration of the `conventional-commits` evals. For each eval and each configuration (`with_skill`, `without_skill`), it:

1. Builds the fixture repo:

   ```sh
   bash tests/conventional-commits/fixtures/<fixture>.sh \
     conventional-commits-workspace/iteration-<N>/eval-<id>-<name>/<config>/run-1/outputs/repo
   ```

2. Runs a subagent on the prompt inside that repo. The user isn't available during the run, so the agent writes what it would have shown or asked to `outputs/notes.md` and continues as if the answer were "yes, go ahead". It must not push.
3. Grades the finished iteration:

   ```sh
   python3 tests/conventional-commits/grade.py conventional-commits-workspace/iteration-<N>
   ```

`grade.py` checks the resulting git history, tree and remote, then writes a `grading.json` next to each run. Use skill-creator's `aggregate_benchmark` and the eval viewer to compare the configurations.

To check fixtures without running Claude, build them all into a scratch directory:

```sh
for f in tests/conventional-commits/fixtures/*.sh; do
  [ "$(basename "$f")" = common.sh ] && continue
  bash "$f" "/tmp/cc-fixtures/$(basename "$f" .sh)/repo"
done
```

#### Adding an eval

1. Write `fixtures/<name>.sh`. Source `common.sh`, create the history and stage the changes.
   - If the fixture doesn't start with two commits, record the starting count with `git config fixture.base <n>`.
   - Record anything the grader compares against with `git config fixture.<key>`. Git config keys can't contain underscores, so use names like `fixture.stagedtree`.
2. Add an entry to `evals/evals.json` with `id`, `name`, `fixture`, `prompt` and `assertions`.
3. Add an `eval_<name>()` check function to `grade.py`, and register it in `SPECIFIC`.
4. Run the eval with and without the skill. A useful eval is one the baseline sometimes fails. If both configurations always pass, the eval doesn't tell them apart.

### Trigger eval

`evals/trigger_eval.json` has 10 queries that should trigger the skill and 10 near misses. Run it from skill-creator's `skills/skill-creator` directory:

```sh
python3 -m scripts.run_eval \
  --eval-set /abs/path/tests/conventional-commits/evals/trigger_eval.json \
  --skill-path /abs/path/skills/conventional-commits \
  --num-workers 1 --runs-per-query 2 --timeout 60 --verbose
```

Keep `--num-workers 1`. With parallel workers, every run writes a near-identical temporary skill into the same commands folder. Claude then picks another run's copy and the result is recorded as a miss, which made recall look like ~10% when it was really 95%. For the same reason, skill-creator's `run_loop` description optimizer isn't usable here yet.

A full serial run makes about 40 `claude -p` calls. Run it from a scratch directory that has its own `.claude/`, so the temporary commands don't land in `~/.claude/commands`.

## Commit messages

This repo uses Conventional Commits, with `commits` as the scope:

```
feat(commits): flag diffs that contradict the user's description
test(commits): add trigger eval set for the skill description
```

Use the plugin to write them.

## Pull requests

- Keep each PR to one concern. Changes to skill behavior should come with the eval that covers them.
- Include before and after eval scores for changes to `SKILL.md`, and trigger eval results for changes to the description.
- Update the README in the same PR when behavior changes.
