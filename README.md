# ship

A Claude Code plugin with git workflow skills for shipping changes. Today it has one skill, `commit`, which writes git commit messages following [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) and makes the commit once you approve the message.

You say "commit this". Claude reads the staged diff, checks the repo's commitlint or commitizen config, drafts a `type(scope)!: description` message with a body and footers where they help, shows it to you, and commits on your OK.

## What this plugin gives you

| Skill          | Purpose                                                                                       |
|----------------|-----------------------------------------------------------------------------------------------|
| `/ship:commit` | Draft a Conventional Commits message for the staged changes, then commit once you approve it. Also handles reverts and rewording existing messages. |

You rarely need the slash command. The skill triggers on ordinary requests such as "commit this", "write a commit msg", "what should I call this commit?" or "wrap this up in a commit", even when you never mention Conventional Commits.

## Prerequisites

- [Claude Code](https://docs.claude.com/claude-code)
- git

commitlint, commitizen and husky are optional. If the repo uses them, the skill follows their rules.

## Install

From a local clone:

```sh
git clone <this-repo-url> ship
claude --plugin-dir /absolute/path/to/ship
```

## Use cases

| You say…                                                                  | What happens                                                                                       |
|---------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| "commit it"                                                               | Reads the staged diff, drafts a message, asks for approval, commits.                               |
| "what should I call this commit?"                                         | Gives you the message only. It doesn't commit unless you ask.                                      |
| "write a commit msg and commit, I haven't staged anything"                | Shows what's modified and proposes what to stage. It never runs `git add -A`, so it won't sweep in a `.env` or build output. |
| "just a refactor, no behavior change, commit it"                          | If the diff shows a renamed argument or a dropped export, it says so, points to the lines and marks the breaking change. It doesn't rewrite your code to match your description. |
| "the caching commit is serving stale data, revert it"                     | Reverts the commit and writes a `revert:` message that references the reverted SHA.                |
| "my last two commit messages are garbage, make them conventional"         | Rewords commits that haven't been pushed. For pushed ones, it explains that rewording needs a force-push and leaves the decision to you. |
| "is `Fixed stuff.` a valid conventional commit?"                          | Checks the message against the spec and the repo's config, then suggests a corrected one.          |

## What the skill follows

**The diff decides what changed.** Session context (what you and Claude discussed) explains *why*, and goes in the body. The staged diff decides *what*, because you may have staged only part of the work.

**Repo config comes first.** The skill looks for:

- `commitlint.config.*`, `.commitlintrc*`, or a `"commitlint"` key in `package.json`
- `.czrc`, `.cz.json`, `.cz-config.js`, `cz.toml`, or `[tool.commitizen]` in `pyproject.toml`
- `.husky/commit-msg` or `.git/hooks/commit-msg`

It applies the rules that shape a message: `type-enum`, `scope-enum`, `scope-empty`, `header-max-length`, `subject-case` and `body-max-line-length`. Without a config it uses the [`@commitlint/config-conventional`](https://github.com/conventional-changelog/commitlint/tree/master/@commitlint/config-conventional) types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore` and `revert`. Scopes follow what the repo's history already uses.

**Breaking changes are always marked**, with both `!` in the header and a `BREAKING CHANGE:` footer that explains how to migrate. A missing marker means semantic-release or a changelog tool ships the change as a minor or patch release.

**It stays local.** The skill never pushes, never passes `--no-verify`, and never amends a commit that has already been pushed. If a commit-msg hook rejects the message, it fixes the message and tries again.

## Example

```
feat(cli)!: rename --out flag to --output

Matches the long-form naming used by the other flags and the README.

BREAKING CHANGE: --out is no longer accepted. Use --output instead.
```

## How it works

```
skills/commit/
├── SKILL.md              # the workflow: inspect, check config, choose type, write, confirm, commit
└── references/
    └── spec.md           # condensed Conventional Commits 1.0.0 rules, SemVer mapping, revert convention
```

`SKILL.md` covers the workflow. Claude reads `references/spec.md` when it needs the exact rules, such as footer syntax or what counts as a breaking change.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the repo layout, local development, and how to run the evals.

## License

[MIT](./LICENSE).
