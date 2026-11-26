---
name: gcp
description: Run and ship apps on Google Cloud - Cloud Run services (URL, revision, traffic, scaling, who can access, secrets and bucket mounts), their error logs, deploying a folder to Cloud Run (Cloud Build + Artifact Registry, optional Google sign-in via IAP, secrets, bucket volumes), rolling back, buckets, Secret Manager and Cloud SQL. Anything that changes the cloud is printed as an exact gcloud plan first and runs only on confirmation. Use when the user mentions GCP, Google Cloud, Cloud Run, gcloud, deploying or rolling back a service, a bucket (gs://), secrets, Cloud SQL, or asks why their service returns errors.
license: MIT
compatibility: Requires Python 3.9+ (standard library only) and the Google Cloud SDK signed in (`gcloud auth login`). GOOGLE_CLOUD_PROJECT names the project.
---

# Google Cloud: Cloud Run, buckets, secrets, Cloud SQL

One CLI, `scripts/gcp.py`, over `gcloud`. Commands are relative to this skill's folder (in Claude Code:
`${CLAUDE_SKILL_DIR}`); run them from the user's project so its `.env` is found. For BigQuery use the bigquery skill.

```bash
python scripts/gcp.py whoami                      # account, project, region, which APIs are on - run this first
python scripts/gcp.py services                    # Cloud Run: ready?, revision, last deploy, URL
python scripts/gcp.py service NAME                # image, traffic, scaling, access, env names, secrets, mounts, revisions
python scripts/gcp.py logs NAME [--errors] [--since 1h] [--limit 50]
python scripts/gcp.py buckets;  python scripts/gcp.py ls gs://BUCKET[/PREFIX]
python scripts/gcp.py secrets                     # names and versions - never values
python scripts/gcp.py sql                         # Cloud SQL instances
# change something: prints the plan, runs it only with --apply
python scripts/gcp.py deploy NAME --source DIR [--access private|iap|public] [--secret ENV=SECRET]
                      [--mount BUCKET:/path] [--env K=V] [--service-account SA] [--max N] [--memory 1Gi]
                      [--cpu-always-on] [--apply]
python scripts/gcp.py rollback NAME [--to REVISION] [--apply]
python scripts/gcp.py upload LOCAL gs://BUCKET[/PREFIX] [--apply]
python scripts/gcp.py secret-set NAME --from-env KEY [--env-file .env] [--apply]
```

Every command takes `--json`, `--project`, `--region`.

## Configuration

`GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_REGION`, optional `GCP_ACCOUNT` - environment or the nearest `.env` (see
`.env.example`). Auth is the user's gcloud sign-in; on "sign-in has expired" ask them to run `gcloud auth login`.

## Rules

1. **Plan, show, then apply.** `deploy`, `rollback`, `upload`, `secret-set` print the exact gcloud commands and
   change nothing. Show the plan and its notes to the user; add `--apply` only after they confirm. Deploys cost
   money and replace what is serving.
2. **Secrets stay out of sight.** Put values into Secret Manager with `secret-set --from-env KEY` (piped from
   `.env`, never printed) and pass them as `--secret ENV=NAME`; never as `--env`, never in chat or logs.
3. **Private by default.** `--access private` unless the user wants otherwise; `iap` = Google sign-in for named
   people; `public` = anyone on the internet - say so when you plan it.
4. **Least privilege.** Prefer a dedicated `--service-account`; the plan grants it only the secrets it reads.
5. Never delete services, buckets, objects, secrets or databases through this skill - there are no commands for
   it on purpose; give the user the gcloud command if they ask.

## Typical requests

- **"Why does my service return 500?"** → `service NAME` (revision, image, env, secrets), then
  `logs NAME --errors --since 1h`; correlate the first errors with the latest revision's creation time. If the
  latest deploy is the cause, plan `rollback NAME`.
- **"Deploy this folder"** → `deploy NAME --source .` with the access, secrets and mounts the app needs; check the
  notes (Dockerfile, `.gcloudignore` so `.env` is not uploaded); existing services keep building into their
  current Artifact Registry repository.
- **"What's in the bucket / sync results to it"** → `ls`, then `upload ... ` (plan) → `--apply`.

## Examples

Run from this folder (`bash examples/<name>.sh`):
- `examples/status-tour.sh` - whoami, services, one service in detail with its recent errors, buckets, secrets, SQL.
- `examples/deploy-plan.sh` - plans for a deploy behind IAP, a rollback and an upload; nothing is changed.

## Gotchas

- Git Bash on Windows rewrites `/app/...` arguments into Windows paths; gcp.py sets `MSYS_NO_PATHCONV=1`. From WSL
  with the Windows gcloud, local paths are converted with `wslpath -w`.
- A Cloud Storage volume (`--mount`) needs the gen2 execution environment (added automatically) and the service
  account must be allowed to use the bucket (`roles/storage.objectUser`).
- IAP on a project without an organization needs an OAuth client made once in the console; each user must also be
  a test user of the OAuth app while it is in Testing.
- Logs can lag by up to a minute after a request.
