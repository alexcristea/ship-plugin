#!/bin/bash
# notify-service with no README at all. Setup needs Node 22, a Docker Postgres and a migration before
# `npm run dev`; there is no `npm start`.
source "$(dirname "$0")/../base.sh" "$1"
record_state
