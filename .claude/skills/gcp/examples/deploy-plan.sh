#!/usr/bin/env bash
# Plans only - nothing is changed: deploy a folder to Cloud Run behind Google sign-in, roll back, upload to a bucket.
# Each prints the exact gcloud commands; add --apply to run one for real.
# Run from the skill folder:   cd skills/gcp && bash examples/deploy-plan.sh
# Uses this skill's own folder as the "app" so it runs anywhere; point --source at your app instead.
set -e

python scripts/gcp.py deploy demo-app --source . --access iap --max 1 --memory 512Mi
SERVICE=${SERVICE:-$(python scripts/gcp.py services --json | python -c "import sys,json; r=json.load(sys.stdin); print(r[0]['service'] if r else '')")}
[ -n "$SERVICE" ] && python scripts/gcp.py rollback "$SERVICE" || echo "(no service to plan a rollback for)"
BUCKET=${BUCKET:-$(python scripts/gcp.py buckets --json | python -c "import sys,json; r=json.load(sys.stdin); print(r[0]['bucket'] if r else '')")}
[ -n "$BUCKET" ] && python scripts/gcp.py upload examples "gs://$BUCKET/skill-example" || echo "(no bucket to plan an upload for)"
