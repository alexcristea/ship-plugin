# README template

Copy the block below and fill it in from the project. Each `<!-- -->` comment says what goes there; delete it once the section is written. Delete any section that doesn't apply rather than writing "N/A". Keep the order: a newcomer reads top to bottom, and the order follows what they need first.

````markdown
# <project-name>

<!-- One or two sentences: what it does, for whom, and where it runs. -->
<What it is> for <who uses it>. <One sentence on where it fits, e.g. "It serves the checkout pages and talks to Stripe and the orders service.">

## Quick start

<!-- From a fresh clone to a running app and passing tests. Every command must exist in the
     project's scripts, Makefile or toolchain. -->

**Prerequisites:** <runtime and version, from .nvmrc / engines / requires-python>, <services, e.g. Docker for Postgres>.

```sh
git clone <repo-url>
cd <project-name>
<install command>
cp .env.example .env          # then fill in the values marked required below
<start services, e.g. docker compose up -d>
<migrate / seed, if any>
<run command>
```

<Where to see it working, e.g. "Open http://localhost:3000. You should see the login page.">

Run the tests:

```sh
<test command>
```

## Configuration

<!-- Names from .env.example. Never real values. Say where to get each secret. -->

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `<NAME>` | yes | | <what it's for; where to get it> |
| `<NAME>` | no | `<default>` | <what it's for> |

## Common tasks

<!-- The commands a teammate runs in a normal week. Skip what Quick start already covers. -->

| Command | What it does |
|---|---|
| `<lint command>` | <...> |
| `<migration command>` | <...> |

## Project layout

<!-- Top-level folders only, one line each. -->

```
<dir>/      <what lives here>
<dir>/      <what lives here>
```

## How it works

<!-- Optional. 2–4 sentences on the main pieces and how a request flows through them.
     Link to docs/ for more rather than writing it here. -->

## Development workflow

<!-- How changes get to production: branch naming, commit convention, PR and review,
     what CI checks, how and when it deploys. Link to CONTRIBUTING.md if it exists. -->

## Troubleshooting

<!-- Optional. Only problems people actually hit, each with its fix. -->

**<symptom>**: <fix>.

## Getting help

<!-- Who owns this and where to ask. If the repo doesn't say, leave a TODO for the user. -->

<Team or owner>, <channel or issue tracker>.

## License

<!-- Only if the repo has a LICENSE file. -->

[<license>](./LICENSE)
````
