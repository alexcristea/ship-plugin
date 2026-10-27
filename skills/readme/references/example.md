# README example

A finished README for a small Node service, written from `references/template.md`. Note what it leaves out: no badges, no feature list, no "How it works" (the service is small enough that the layout says it), and no generic advice. Every command is a script in its `package.json`.

````markdown
# billing-api

The HTTP API behind invoices and payments in the Acme dashboard. It stores invoices in Postgres and charges cards through Stripe.

## Quick start

**Prerequisites:** Node 22 (see `.nvmrc`), Docker for the local Postgres.

```sh
git clone git@github.com:acme/billing-api.git
cd billing-api
npm ci
cp .env.example .env          # then set STRIPE_API_KEY, see Configuration
docker compose up -d db
npm run db:migrate
npm run dev
```

Check it's up with `curl localhost:3000/health`, which returns `{"status":"ok"}`.

Run the tests (they use the same Docker database):

```sh
npm test
```

## Configuration

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `DATABASE_URL` | yes | in `.env.example` | Postgres connection. The default points at `docker compose`. |
| `STRIPE_API_KEY` | yes | | Stripe test-mode secret key. Ask in #billing-dev for the shared one. |
| `PORT` | no | `3000` | Port the API listens on. |
| `LOG_LEVEL` | no | `info` | `debug` logs every SQL query. |

## Common tasks

| Command | What it does |
|---|---|
| `npm run lint` | ESLint and Prettier check, as CI runs them |
| `npm run db:migrate:new <name>` | Create a new migration in `migrations/` |
| `npm run db:reset` | Drop, recreate and seed the local database |

## Project layout

```
src/routes/     HTTP handlers, one file per resource
src/services/   business logic; the only code that talks to Stripe
src/db/         queries and the connection pool
migrations/     SQL migrations, applied in filename order
test/           integration tests against the Docker database
```

## Development workflow

Branch from `main`, keep PRs small, and use Conventional Commits. CI runs lint and tests on every PR; merging to `main` deploys to staging, and a release tag deploys to production. Details in [CONTRIBUTING.md](./CONTRIBUTING.md).

## Troubleshooting

**`ECONNREFUSED 127.0.0.1:5432`**: the database isn't running. Start it with `docker compose up -d db`.

## Getting help

Owned by the Payments team. Ask in #billing-dev, or open an issue.
````
