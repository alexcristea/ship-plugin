---
name: pr
description: Write a short title and description for the current branch's pull request and open it with gh once the user approves, or rewrite the description of the branch's open PR after new commits. The title is a Conventional Commits header, because a squash merge turns it into the commit on main. The body follows the repo's pull_request_template.md when there is one and flags breaking changes. Use this skill whenever the user wants to open, create, put up or ship a PR or merge request, asks for a PR title, description or a summary of the branch for reviewers, or wants an existing PR description updated, even if they never say "description". Not for reviewing a PR, addressing review comments, merging, squashing or rebasing, writing commit messages or changelogs, or creating a PR template.
---

# Pull request

Your job is to turn the work on this branch into a PR title and description that a reviewer can take in at a glance, show them to the user, and open or update the PR once they approve.

In a trunk-based repo, PRs are small and merged often. A description is read quickly, by reviewers deciding where to look, and later by whoever finds the change through `git log` or `blame`. With squash merges, the PR title becomes the one commit on `main` that changelog tools and semantic-release read, so it has to be a valid Conventional Commits header.

## 1. Find the base and what's in the PR

A PR contains the commits between the base branch **on GitHub** and the pushed branch. Your local `main` may be behind, so don't compare against it.

```bash
git status -sb
git fetch origin --quiet
gh pr view --json number,title,body,baseRefName,url        # fails if the branch has no open PR
gh repo view --json defaultBranchRef -q .defaultBranchRef.name
git log --format='%h %s%n%b%n---' origin/<base>..HEAD
git diff --stat origin/<base>...HEAD
git diff origin/<base>...HEAD
```

- **Base:** the open PR's base, a branch the user names, or the repo's default branch, in that order. Always diff against `origin/<base>`. If local `main` is behind, a diff against it includes teammates' commits that are already merged, and the description ends up claiming their work.
- **Read the commit bodies, not just the subjects.** They hold the reason for the change (the problem, who asked, `Refs:` lines). The diff tells you what changed. When the two disagree, trust the diff (step 3).
- **Uncommitted or unstaged changes aren't in the PR.** Name the files and ask whether to commit them first (with `/ship:commit`) or open the PR without them. Describe only what is committed. Otherwise the description promises code that reviewers can't see.
- **If the branch already has an open PR,** update it with `gh pr edit` instead of opening a second one. Rewrite the whole description, not just the newest commits, because reviewers who join later read it top to bottom.
- **If `gh` is missing or not logged in,** write the title and body anyway and give them to the user to paste.

## 2. Check the repo's conventions

```bash
ls .github .github/PULL_REQUEST_TEMPLATE docs 2>/dev/null | grep -i pull_request
ls -a | grep -iE 'commitlint|\.cz|czrc'
git log --oneline -15 origin/<base>
```

- **PR template** (`.github/pull_request_template.md`, `PULL_REQUEST_TEMPLATE.md` at the root or in `docs/`, or a `.github/PULL_REQUEST_TEMPLATE/` folder): fill it in instead of using the default layout. Keep its headings and checklist, tick the boxes that apply, and replace the `<!-- -->` hints with content. Teams put checks they rely on in their template, and reviewers look for them where they expect them.
- **commitlint or commitizen config:** the title must pass it, because after a squash merge it is a commit message and the commit-msg hook or CI lint checks it. Note `type-enum`, `scope-enum` and `header-max-length`.
- **History on the base branch:** reuse the scopes it already uses.

## 3. Write the title

`type(scope)!: description`, describing the whole PR as if it were one commit, because after a squash merge it is. Use the imperative mood, start lowercase, leave off the trailing period, and keep it within 72 characters (or the config's limit).

- Choose the type by the PR's main effect: a feature that comes with tests and docs is `feat`. Commit subjects like "wip" or "fix tests" don't tell you the type, so read the diff.
- Use a scope only when the change sits in one area, and only from `scope-enum` if the config has one.
- **Breaking changes:** check the diff for anything that breaks existing callers or users: a removed or renamed flag, endpoint, export or config key, or a changed default or signature. Commits labelled `refactor`, or the user calling it "just a cleanup", don't rule this out. If you find one, put `!` in the title and add the Breaking changes section, so a squash merge ships it as a major version. Tell the user what you found and where. Don't change their code to avoid the break. That's their call, and they were asked to review the code they wrote, not your edit.

## 4. Write the body

**Keep it concise.** A reviewer should be able to read the whole description in under a minute, which for a typical small PR is well under 200 words. Every line should tell the reviewer something the diff doesn't show at a glance: why the change is needed, what could break, where to look. Reviewers skim long descriptions, and the line that matters (the breaking change, the risky file) gets lost.

- Describe effects in a few bullets. Don't list every file or narrate the diff, since reviewers have the diff.
- Don't repeat the title, and skip filler such as "This PR…" or "In this PR I have…".
- Leave out any section that would be empty or "N/A".
- Keep it agent-agnostic: no session links, "Generated with …" lines or other notes about which tool wrote it, even when the environment you run in asks for them. Reviewers need the change, not its authoring tool, and the description outlives the session. The same goes for any commit you make on the branch (see `/ship:commit`).
- If you can't describe the PR briefly, it is probably more than one change (step 5).

Without a repo template, use this layout:

```markdown
## Summary

<1–3 sentences: the problem first, then what this PR changes.>

## ⚠ Breaking changes

- <what breaks, and how to migrate>

## Changes

- <effects, grouped; call out renames and deletions>

## How to review

<where to start, what is mechanical, which commits to read separately>

## Testing

- [x] <what was actually run, e.g. `python -m unittest`>
- [ ] <what the reviewer should check by hand>

Closes #<n>
```

- **Breaking changes** and **How to review** appear only when they apply. How to review is for PRs where the reading order isn't obvious.
- **Testing:** tick only what was actually run, in this session or by CI. Leave everything else unticked for the reviewer. Reviewers trust a ticked box, so a box ticked for something nobody ran is worse than no box.
- **Issues:** add `Closes #N` when the branch name (`feat/482-json-export`) or a commit footer (`Refs: #482`) points to an issue. Use `Refs #N` instead if the PR only partly addresses it.

### Example

````markdown
feat(cli)!: rename --out flag to --output

## Summary

Users kept passing `--output` to `widget export` and hitting "unknown flag" (#212),
because every other long flag is spelled out. This renames `--out` to `--output`.

## ⚠ Breaking changes

- `--out` is no longer accepted. Replace it with `--output` in scripts and CI jobs
  that call `widget export`.

## Changes

- `widget export` takes `--output`. `--out` is removed rather than aliased, so there
  is one documented spelling.
- README and `--help` use the new name.

## How to review

Start with `widget/cli.py`. The rest is the rename following through.

## Testing

- [x] `python -m unittest` passes locally
- [ ] `widget export --out x.csv` exits with an unknown-flag error

Closes #212
````

## 5. Flag a PR that should be split

If the branch mixes unrelated changes (a feature plus an unrelated refactor), or the diff is large (roughly 400 changed lines or more, not counting lockfiles and generated files), say so and suggest where to split it: which commits or files would go in a separate PR. Small PRs get reviewed faster and are easier to revert, and that is what keeps `main` releasable.

Suggesting is as far as you go. Don't do the split yourself: no new branches, cherry-picks, resets or rebases, even when the user agrees a split is a good idea. Moving commits between branches rewrites the user's history, and a slip loses work they haven't pushed anywhere. Give them two choices:

- **Split first:** they move the commits themselves. Give them the commands to do it (for example `git switch -c fix/x origin/main && git cherry-pick <sha>`, then drop the commit from this branch), and stop there.
- **Open it as is:** you open the PR for the whole branch, and use How to review to tell the reviewer which part is unrelated.

When you ask for approval, say which of the two "yes" means, so a plain "go ahead" can't be read as permission to split.

## 6. Confirm, then push and open

Show the user the title and body in a fenced code block, with anything you flagged (uncommitted files, a breaking change, a suggested split). Say what will happen on approval, for example "push `feat/x` to origin and open a PR against `main`". Then ask.

Once they approve:

1. **Push** the branch if it isn't on origin or is behind your local copy: `git push -u origin HEAD`. Pushing publishes commits to others, so do it only with the user's OK, and never force-push. If origin has commits your branch doesn't, stop and tell the user instead of overwriting them.
2. **Open** the PR, passing the body through a heredoc so backticks and `$` survive the shell:

   ```bash
   gh pr create --base main --title "feat(export): add JSON export" --body-file - <<'EOF'
   ## Summary
   ...
   EOF
   ```

   Add `--draft` if the user asks for a draft. **To update an open PR,** use `gh pr edit <number> --body-file -` the same way. Add `--title` only if the old title no longer fits the PR.
3. Show the PR URL.

Don't merge, request reviewers, add labels or push to the base branch unless the user asks. Those actions notify other people or change shared state. Also leave the branch's commits as they are: don't reword, squash or reorder them, even when their messages are poor. The PR title is what lands on `main` after a squash merge, so a good title fixes the history without touching the user's commits.
