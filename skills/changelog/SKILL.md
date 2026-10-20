---
name: changelog
description: Create or update the project's CHANGELOG.md from git history, turning commits since the last release tag (Conventional Commits or not) into reader-facing entries in Keep a Changelog format, or in whatever format the file already uses. Use this skill whenever the user wants a changelog written, started, caught up, or checked, says things like "update the changelog", "add this to CHANGELOG.md", "what changed since v1.2? put it in the changelog", "we don't have a changelog, make one", or wants entries moved into a version section for an upcoming release ("get the changelog ready for 1.3.0"). Accepts an optional version or bump (1.3.0, major, minor, patch) to cut a release section. Not for writing commit messages, tagging or publishing releases, or configuring tools like semantic-release or release-please.
argument-hint: "[version | major | minor | patch]"
---

# Changelog

Your job is to turn the commits since the last release into `CHANGELOG.md` entries that a user of the project can read, show the user the change, and leave it for them to review.

A changelog is for people deciding whether to upgrade and what will break, not a copy of `git log`. In a trunk-based repo every commit on `main` could be released, so the changelog is what tells readers which of those commits matter to them. For format rules, the type mapping and SemVer details, read `references/format.md`.

Arguments: `$ARGUMENTS`

- **No arguments:** add new entries to the `## [Unreleased]` section.
- **A version** (`1.3.0`, `v2.0.0`): also cut a release section with that version (step 6).
- **A bump** (`major`, `minor`, `patch`): work out the version from the last tag, then cut it.
- The user can ask for the same thing in plain words ("get the changelog ready for 1.3.0"). Treat that the same as an argument.

## 1. Check whether a tool owns the changelog

Some repos generate `CHANGELOG.md` with a tool. A hand edit there gets overwritten on the next release, or conflicts with the tool's release PR, so the user ends up with two sources of truth. Look for:

- release-please: `release-please-config.json`, `.release-please-manifest.json`
- semantic-release with `@semantic-release/changelog`: `.releaserc*`, `release.config.*`, or a `"release"` key in `package.json`
- changesets: a `.changeset/` directory
- git-cliff: `cliff.toml`; standard-version / commit-and-tag-version: `.versionrc*`; auto-changelog: `"auto-changelog"` in `package.json`

```bash
ls -a | grep -iE 'release-please|releaserc|release\.config|changeset|cliff\.toml|versionrc'; grep -nE '"(release|auto-changelog)"|semantic-release' package.json 2>/dev/null
```

If a tool owns the file, don't edit it. Tell the user which tool generates it and how its changelog gets updated (for example, release-please writes it in the release PR it opens after changes land on `main`). If the commits since the last release wouldn't produce the entries they expect, such as a fix committed as `chore`, say so, because that is the part they can still change. Stop there unless they ask you to edit the file anyway.

## 2. Find what is new

```bash
git describe --tags --abbrev=0            # last release tag reachable from HEAD
git log <tag>..HEAD --format='%h %s%n%b%n---'
git remote get-url origin                 # for compare links
```

- **No tags:** use the whole history.
- **Check against the file, not only the tag.** If `[Unreleased]` already lists some of these changes, or the newest version heading in the file is newer than the last tag (a release written but not yet tagged), only add what is missing. Duplicate entries are worse than missing ones, because readers stop trusting the list.
- Read the full message, not just the subject. The body and footers carry `BREAKING CHANGE:` notes and `Refs:` / `(#123)` references.
- With squash merges, each commit on `main` is usually one PR. Keep its `(#123)` reference on the entry.

## 3. Sort the commits

Map each commit by its effect on users. The full table is in `references/format.md`. In short:

| Commit | Section |
|---|---|
| `feat` | Added |
| `fix` | Fixed |
| `perf`, a `refactor` users can notice | Changed |
| a deprecation | Deprecated |
| a removed feature, endpoint, flag or option | Removed |
| a fix for a vulnerability | Security |
| `!` in the header or a `BREAKING CHANGE:` footer | Breaking changes callout (also in its own section) |
| `docs`, `test`, `ci`, `build`, `chore`, `style` | left out, unless users see the effect |

- **Breaking changes are the most important entries.** Check both markers. A `BREAKING CHANGE:` footer without `!` in the header is still breaking, and it is easy to miss if you only read subjects. List each breaking change in the callout with its migration step taken from the footer, so readers know what to change, not just that something changed.
- **"Unless users see the effect"** covers things like a raised minimum runtime (`build`) or a changed install command (`docs`). If an upgrading user has to do something, it belongs in the changelog.
- **Reverts:** if a commit and its revert are both in the range, leave out both. If the reverted commit was already released, the revert is an entry, for example under Removed or Fixed.
- **Non-conventional messages** ("Fixed crash on empty config", "Update stuff"): decide from the message and, when that isn't enough, the diff (`git show --stat <sha>`, then the files). List the ones you weren't sure about when you report back.

## 4. Write the entries

Write for someone upgrading, not for the person who wrote the code:

- Describe the effect, not the implementation: "CSV export quotes fields that contain commas", not "use csv.writer in to_csv".
- One entry per change a user would notice. Merge commits that are parts of the same change.
- Keep the scope only if it helps the reader (`**cli:**` in a project with a CLI and a library). Keep PR and issue references.
- Match the voice of the entries already in the file (tense, punctuation, backticks for code).

## 5. Edit the file

**If the file exists, follow its format.** Use its headings, bullet style and link style, even if it isn't Keep a Changelog. A file in conventional-changelog style (`### Features`, `### Bug Fixes`, `* **scope:** …`) gets new entries in that style. Mixing two formats in one file makes it harder to read and breaks tools that parse it.

**If there is no file,** create one in Keep a Changelog 1.1.0 format (header template in `references/format.md`):

```markdown
## [Unreleased]

### ⚠ Breaking changes

- `--out` is now `--output`. Rename the flag in scripts that call the CLI.

### Added

- CSV export for the invoice list (#482).

### Fixed

- `dateRange` includes the end date again.
```

- Keep the order: Breaking changes callout first, then Added, Changed, Deprecated, Removed, Fixed, Security. Leave out empty sections.
- **Never edit released sections.** They record what shipped in each version, and people link to them. If you spot a mistake in one, mention it to the user instead of fixing it silently.
- Update the link definitions at the bottom (`[Unreleased]: …/compare/v1.2.0...HEAD`) using the `origin` URL. Formats for GitHub and GitLab are in `references/format.md`. If there is no remote, leave them out rather than inventing a URL.

## 6. Cut a version (only when asked)

Do this only when the arguments or the user ask for a version. Otherwise everything stays in `[Unreleased]`, so that whoever releases decides when a version is cut.

1. Work out the version the commits call for: major if there is any breaking change, minor if there is any `feat`, otherwise patch. In `0.x`, a breaking change bumps the minor version.
2. If the user named a version that doesn't match (for example `1.3.0` with a breaking change in the range), use their version, and tell them clearly what SemVer calls for and why. They may have a reason, such as a policy or a version that is already announced, but they should decide knowing about the mismatch.
3. Rename `## [Unreleased]` to `## [x.y.z] - YYYY-MM-DD` (today's date), and add a new empty `## [Unreleased]` above it.
4. Update the links: `[Unreleased]` compares `vx.y.z...HEAD`, and `[x.y.z]` compares the previous tag with `vx.y.z`. Follow the tag naming the repo uses (`v1.2.0` or `1.2.0`).

Don't create the tag, bump the version in `package.json` / `pyproject.toml` / other manifests, or publish. Those are release steps, and they're hard to undo once others pull them. Mention which ones are left for the user.

## 7. Report back

Show the user the change as a diff in a fenced code block (`git diff CHANGELOG.md`, or the whole file if it's new). Then list:

- commits you left out and why, in one line (for example "skipped 3 ci/test/chore commits")
- commits you weren't sure how to classify
- a version mismatch, if there is one

Leave the file uncommitted so the user can edit the wording first. Offer to commit it with `docs(changelog): add unreleased changes`, or `chore(release): x.y.z` for a cut version, and follow the repo's commit conventions if they ask. Never push or tag.
