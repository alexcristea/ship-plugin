# Changelog formats and rules

## Keep a Changelog 1.1.0 (default for new files)

Source: https://keepachangelog.com/en/1.1.0/

Header for a new file:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
```

Rules:

- Newest version first. `## [Unreleased]` is always at the top.
- Version headings: `## [1.3.0] - 2026-10-20` (ISO 8601 date). A withdrawn release is marked `## [1.2.1] - 2026-10-01 [YANKED]`.
- Sections, in this order, each only if it has entries: `### Added`, `### Changed`, `### Deprecated`, `### Removed`, `### Fixed`, `### Security`.
- This plugin adds a `### ⚠ Breaking changes` callout above them. Each breaking change is listed there with its migration step, and also in the section it belongs to (usually Changed or Removed).
- Entries are `- ` bullets, one change each, written for users.
- Link definitions go at the bottom of the file, newest first.

## Commit type to section

| Commit | Section | Notes |
|---|---|---|
| `feat` | Added | A new capability. If it replaces old behavior, Changed. |
| `fix` | Fixed | A fix for a vulnerability goes under Security. |
| `perf` | Changed | Only if users can notice it (speed, memory, size). |
| `refactor` | Changed, or left out | Left out unless behavior users see changes. |
| `revert` | Removed or Fixed | Only if the reverted commit was released. Otherwise leave out both. |
| `docs`, `test`, `ci`, `build`, `chore`, `style` | left out | Unless the effect reaches users: a raised minimum runtime, a new install step, a dropped platform. |
| any type with `!` or a `BREAKING CHANGE:` / `BREAKING-CHANGE:` footer | Breaking changes callout | Also list it under Changed or Removed. Take the migration step from the footer. |
| a deprecation (message or diff adds a deprecation warning) | Deprecated | Name the replacement. |

## conventional-changelog style

Used by semantic-release, release-please, standard-version and commit-and-tag-version. When an existing file uses it, follow it:

```markdown
## [1.3.0](https://github.com/acme/widget/compare/v1.2.0...v1.3.0) (2026-10-20)


### ⚠ BREAKING CHANGES

* **cli:** --out is no longer accepted. Use --output instead.

### Features

* **export:** add JSON export ([a1b2c3d](https://github.com/acme/widget/commit/a1b2c3d))


### Bug Fixes

* **cli:** expand ~ in --output paths (#57)
```

- Sections: `⚠ BREAKING CHANGES`, `Features`, `Bug Fixes`, `Performance Improvements`, `Reverts`. The other types are hidden by default.
- Entries are `* **scope:** subject`, usually the commit subject as written.
- Unreleased changes have no standard heading in this style. Use `## Unreleased` above the newest version, unless the file already does something else.

## SemVer bump

Source: https://semver.org/spec/v2.0.0.html

| Commits since the last release include | 1.x and later | 0.x |
|---|---|---|
| a breaking change | major (`2.0.0`) | minor (`0.5.0`) |
| a `feat`, no breaking change | minor (`1.3.0`) | minor, or patch if the project treats 0.x features as patches |
| only fixes and other changes | patch (`1.2.1`) | patch |

Pre-releases (`1.3.0-rc.1`) sort before `1.3.0`. Only cut one when the user asks for it.

## Compare links

Use the `origin` URL, converting SSH form (`git@github.com:acme/widget.git`) to HTTPS and dropping `.git`. Use the tag names as the repo spells them (`v1.2.0` or `1.2.0`).

| Host | Unreleased | Version | First version |
|---|---|---|---|
| GitHub | `[Unreleased]: https://github.com/o/r/compare/v1.3.0...HEAD` | `[1.3.0]: https://github.com/o/r/compare/v1.2.0...v1.3.0` | `[1.0.0]: https://github.com/o/r/releases/tag/v1.0.0` |
| GitLab | `[Unreleased]: https://gitlab.com/o/r/-/compare/v1.3.0...HEAD` | `[1.3.0]: https://gitlab.com/o/r/-/compare/v1.2.0...v1.3.0` | `[1.0.0]: https://gitlab.com/o/r/-/tags/v1.0.0` |

For other hosts, or with no remote, leave out the links rather than guessing a URL format.

## Tools that own the changelog

| Tool | Detected by | How its changelog is updated |
|---|---|---|
| release-please | `release-please-config.json`, `.release-please-manifest.json` | Writes it in the release PR it opens after changes land on `main` |
| semantic-release | `.releaserc*`, `release.config.*`, `"release"` in `package.json`, with `@semantic-release/changelog` | Writes it during the release run in CI |
| changesets | `.changeset/` | `npx changeset` adds a change file; `changeset version` writes the changelog |
| git-cliff | `cliff.toml` | `git cliff -o CHANGELOG.md` (or `--unreleased --prepend`) |
| standard-version / commit-and-tag-version | `.versionrc*`, the package in `devDependencies` | Writes it when the release command runs |
| auto-changelog | `"auto-changelog"` in `package.json` | `npx auto-changelog` |
