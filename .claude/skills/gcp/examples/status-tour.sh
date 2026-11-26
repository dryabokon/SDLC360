#!/usr/bin/env bash
# A read-only tour of a project: who and where, Cloud Run services, one service in detail, its recent errors,
# buckets, secrets (names only), Cloud SQL.
# Run from the skill folder:   cd skills/gcp && bash examples/status-tour.sh
# Needs gcloud signed in and GOOGLE_CLOUD_PROJECT (env or .env). Pick the service with SERVICE=name.
set -e

python scripts/gcp.py whoami
python scripts/gcp.py services
SERVICE=${SERVICE:-$(python scripts/gcp.py services --json | python -c "import sys,json; r=json.load(sys.stdin); print(r[0]['service'] if r else '')")}
if [ -n "$SERVICE" ]; then
  python scripts/gcp.py service "$SERVICE"
  python scripts/gcp.py logs "$SERVICE" --errors --since 7d --limit 10
fi
python scripts/gcp.py buckets
python scripts/gcp.py secrets
python scripts/gcp.py sql
