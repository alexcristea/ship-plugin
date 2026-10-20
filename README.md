# ship

A Claude Code plugin for trunk-based development: atomic commits, small PRs and a main branch that's always releasable. It has two skills: `commit` writes git commit messages following [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) and makes the commit once you approve the message, and `changelog` turns the commits since the last release into `CHANGELOG.md` entries.

You say "commit this". Claude reads the staged diff, checks the repo's commitlint or commitizen config, drafts a `type(scope)!: description` message with a body and footers where they help, shows it to you, and commits on your OK.

## What this plugin gives you

| Skill          | Purpose                                                                                       |
|----------------|-----------------------------------------------------------------------------------------------|
| `/ship:commit` | Draft a Conventional Commits message for the staged changes, then commit once you approve it. Also handles reverts and rewording existing messages. |
| `/ship:changelog [version \| major \| minor \| patch]` | Add the changes since the last release to `CHANGELOG.md` under `[Unreleased]`. With a version or bump, also cut a dated release section. |

You rarely need the slash commands. The skills trigger on ordinary requests such as "commit this", "what should I call this commit?", "update the changelog" or "get the changelog ready for 1.3.0", even when you never mention Conventional Commits.

## Prerequisites

- [Claude Code](https://docs.claude.com/claude-code)
- git

commitlint, commitizen and husky are optional. If the repo uses them, the skill follows their rules.

## Install

From a local clone:

```sh
git clone https://github.com/alexcristea/ship-plugin.git
claude --plugin-dir "$PWD/ship-plugin"
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
| "update the changelog"                                                    | Adds the commits since the last tag to `[Unreleased]`, written for users. Leaves out CI, test and chore commits, never edits released sections, and leaves the file uncommitted for you to review. |
| "we don't have a changelog, make one"                                     | Creates a Keep a Changelog `CHANGELOG.md` from the whole history. If a changelog already exists, it follows that file's format instead. |
| `/ship:changelog 1.3.0`                                                   | Moves `[Unreleased]` into a dated `[1.3.0]` section and updates the compare links. If the commits call for a different version (a breaking change in a minor), it tells you. It doesn't tag or bump `package.json`. |
| "update the changelog" in a repo using release-please or semantic-release | Leaves the file alone and explains which tool writes it, since a hand edit would be overwritten. |

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

```
skills/changelog/
├── SKILL.md              # the workflow: check for a changelog tool, find new commits, sort, write, cut a version, report
└── references/
    └── format.md         # Keep a Changelog and conventional-changelog layouts, type mapping, SemVer bumps, compare links
```

`changelog` builds on `commit`: the types, `!` markers and `BREAKING CHANGE:` footers that `commit` writes are what `changelog` sorts on. It also handles history that doesn't follow Conventional Commits, by reading the diff.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the repo layout, local development, and how to run the evals.

## License

[MIT](./LICENSE).
