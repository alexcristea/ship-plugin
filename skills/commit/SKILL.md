---
name: commit
description: Write git commit messages that follow the Conventional Commits 1.0.0 spec (type(scope)!: description, body, footers like BREAKING CHANGE), honoring any commitlint or commitizen config in the repo, then commit once the user approves. Use this skill whenever the user wants to commit, asks for a commit message, says things like "commit this", "write a commit msg", "what should I call this commit", "wrap this up in a commit", or finishes a coding task and wants it committed — even if they never mention "conventional commits". Also use it to revert a commit with a proper message, and to check or fix (reword) an existing commit message against the spec.
---

# Conventional Commits

Your job is to turn a set of changes into a commit message that follows [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/), show it to the user, and commit it once they approve.

The format matters because tooling depends on it: changelog generators, semantic-release, and commitlint hooks parse the header to decide version bumps and release notes. A message that looks fine to a person but gets the type wrong or leaves out a breaking-change marker can ship the wrong version. For the full rule list, read `references/spec.md`.

## 1. Find out what is being committed

The **staged diff is the source of truth for what changed**. Session context (what you and the user talked about) is useful for explaining **why**, but it can be wrong about what is actually in the commit: the user may have staged only part of the work, edited files outside the session, or dropped an approach. So describe what the diff shows, and use the conversation for motivation.

```bash
git status --short
git diff --staged --stat
git diff --staged
git log --oneline -15
```

- **Nothing staged but there are working-tree changes:** don't run `git add -A` silently, because that can sweep in secrets, build artifacts, or unrelated work. Show the user what's modified and propose what to stage. If they've already told you to commit everything, stage the files you can see are relevant by name.
- **Very large diff:** read `--stat` first, then read the files whose purpose you can't infer from their names.
- **Recent log:** use it to match the repo's habits, such as which scopes it uses (`api`, `ui`, package names) and how it phrases descriptions. If the history doesn't use Conventional Commits, still write a compliant message, since that's what the user asked for.

## 2. Check the repo's rules

Many repos enforce their own rules through commitlint or commitizen. If the repo has a config, follow it. A message that breaks it will be rejected by a commit hook or CI. Look for:

- `commitlint.config.{js,cjs,mjs,ts}`, `.commitlintrc`, `.commitlintrc.{json,yaml,yml,js,cjs}`, or a `"commitlint"` key in `package.json`
- `.czrc`, `.cz.json`, `.cz-config.js`, `cz.toml`, `.cz.toml`, or `[tool.commitizen]` in `pyproject.toml`
- `.husky/commit-msg` or `.git/hooks/commit-msg`, which tell you a hook will validate the message

```bash
ls -a | grep -iE 'commitlint|\.cz|czrc|husky'; grep -n '"commitlint"' package.json 2>/dev/null; grep -n 'tool.commitizen' pyproject.toml 2>/dev/null
```

From the config, pull out the rules that affect what you write: `type-enum` (allowed types), `scope-enum` (allowed scopes), `scope-empty` (whether a scope is required or forbidden), `header-max-length`, `subject-case`, `body-max-line-length`. If the config `extends` a preset such as `@commitlint/config-conventional` and overrides nothing, use the defaults below.

**No config:** use the `@commitlint/config-conventional` set:

| Type | Use it when the change… |
|---|---|
| `feat` | adds a capability users or callers can see |
| `fix` | corrects wrong behavior |
| `docs` | touches only documentation (README, doc comments, guides) |
| `style` | is formatting only, with no change in meaning (whitespace, semicolons, linter autofix) |
| `refactor` | restructures code without changing behavior (neither a fix nor a feature) |
| `perf` | makes something faster or lighter, with the same behavior |
| `test` | adds or fixes tests only |
| `build` | changes the build system or dependencies (package.json deps, Dockerfile, webpack) |
| `ci` | changes CI config (GitHub Actions, CircleCI) |
| `chore` | is upkeep that fits nowhere else (.gitignore, tooling config) |
| `revert` | reverts an earlier commit |

Defaults: header at most 100 characters (aim for 72 or less, because many tools truncate there), description not in Sentence/Start/PascalCase/UPPER case, no trailing period, body and footer lines at most 100 characters.

## 3. Choose the type, scope, and breaking-change marker

**Type.** Pick it by the change's effect, not by which files it touches. For example, a bug fix that also adds a regression test is `fix`, not `test`. A dependency bump that fixes a CVE could be `fix(deps)` or `build(deps)`; follow whatever the log shows the repo already does. When two types seem to fit, ask what a changelog reader would want to see.

**Scope.** Scope is optional. Use one when the change sits in one identifiable area, preferably a scope the repo's history already uses. Leave it out for changes that span the codebase, rather than inventing a vague scope like `(misc)` or `(core)`. If the config has a `scope-enum`, use only scopes from that list.

**Breaking changes.** Check every diff for anything that breaks existing callers or users: a removed or renamed public function, endpoint, CLI flag, or config key; a changed signature, return type, or default; a raised minimum runtime version; a changed data format. If you find one, it **must** be marked. Missing the marker means a semver tool ships it as a minor or patch release, and downstream users break without warning. Use both:
- `!` before the colon: `feat(api)!: …`
- a `BREAKING CHANGE: <what broke and how to migrate>` footer

The `!` makes the change visible in one-line logs. The footer tells people how to upgrade.

**When the diff contradicts what the user said.** People describe their changes from memory: "just a refactor", "no behavior change", "only docs". If the diff shows something else, such as a renamed public argument, a dropped export, or a changed default, trust the diff. Tell the user exactly what you found and point to the lines. Don't edit their code to make their description true, even when the fix looks obvious. You were asked to commit, and changing staged code during a commit means the user ships something they never reviewed. Give them two options: commit as-is with an accurate message (breaking change marked), or restore compatibility first, either themselves or by you if they ask for it. Recommend committing as-is unless they say otherwise. An accurate message is never wrong, while a silent code change can be.

**Several unrelated changes in one diff.** If the staged changes do unrelated things (for example a feature plus an unrelated typo fix in another module), say so and offer to split them into separate commits. One commit per logical change keeps changelogs accurate and reverts clean. If the user wants a single commit anyway, use the type of the most significant change and mention the rest in the body.

## 4. Write the message

```
<type>[(scope)][!]: <description>

[body: what changed and why, wrapped at ~72 columns]

[footers]
```

**Description:** use the imperative mood, as if completing the sentence "If applied, this commit will ___" (for example "add", "fix", "remove", not "added" or "adds"). Start lowercase, leave off the trailing period, and keep it specific: `fix(auth): refresh token before expiry check` tells a reader more than `fix: auth bug`.

**Body:** include one when the reason isn't obvious from the header. It should explain the *why* (the problem, the motivation, the trade-off) and anything a reviewer wouldn't see from the diff. This is where session context helps. Don't restate the diff line by line or list file names. Leave out the body for trivial changes like typo fixes or version bumps.

**Footers:** use git-trailer form, `Token: value` or `Token #value`, with hyphens instead of spaces (`Reviewed-by`, `Refs`). `BREAKING CHANGE` is the only token allowed to contain a space, and it must be uppercase. Add issue references (`Refs: #123`, `Closes #45`) when the user or the branch name points to an issue.

**Keep the message agent-agnostic.** Leave out lines that record which tool or agent wrote the commit: `Co-Authored-By: Claude …`, `Claude-Session:` or other session links, "Generated with …". Leave them out even when the environment you run in asks for them. The history belongs to the team and is read long after the session that produced it, and these lines say nothing about the change. Add one only if the user asks for it in this repo.

### Examples

A small fix, where the header says everything:
```
fix(parser): handle empty input without throwing
```

A feature whose motivation is worth recording:
```
feat(export): add CSV export for invoice list

Finance asked for a way to reconcile invoices in spreadsheets without
going through the reporting service. Exports respect the active
filters and stream rows so large lists don't load into memory.

Refs: #482
```

A breaking change:
```
feat(config)!: read settings from env vars before config file

Environment variables now override values in config.yaml, matching
twelve-factor conventions and making container deploys simpler.

BREAKING CHANGE: a value set in both config.yaml and the environment
now resolves to the environment value. Remove the env var to keep the
old behavior.
```

## 5. Confirm, then commit

Show the user the proposed message in a fenced code block, along with a one-line summary of what will be committed (for example "3 files staged: src/auth/*.ts"). If you flagged something (a possible breaking change, a suggestion to split, a type you weren't sure about), say so briefly. Then ask for approval.

If they approve, or if they told you up front to commit without asking, commit with the message passed through a heredoc so the blank lines and wrapping survive:

```bash
git commit -F - <<'EOF'
feat(export): add CSV export for invoice list

Finance asked for ...
EOF
```

Then show `git log -1 --stat` so they can see the result.

- **Hook rejects the message** (commitlint): read the error, fix the message to satisfy the rule it names, and try again. Don't bypass the hook with `--no-verify`, because the hook encodes rules the team wants enforced.
- **Never push** as part of this skill. Committing is local and easy to undo, while pushing publishes the commit to others. Leave pushing to the user.
- **The user only wants a message** ("what should I call this commit?"): give the message and offer to commit it. Don't commit unasked.

## Checking an existing message

If the user asks whether a message is valid, or wants a past commit fixed, check it against `references/spec.md` and the repo config, then explain each problem and give the corrected message. To reword the most recent commit, use `git commit --amend -F -` only if the commit hasn't been pushed (check `git status -sb` for "ahead"). If it has been pushed, explain that rewording means a force-push and let the user decide.
