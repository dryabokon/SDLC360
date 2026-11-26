# SDLC360 on GCP (hosted)

The same app as `./start.sh`, published on Cloud Run behind Google sign-in (Identity-Aware Proxy).
Everyone allowed by `SDLC360_SITE_VIEWERS` (for example `domain:example.com`) opens one URL, assesses
a repository by its URL and sees every assessment made so far.

```bash
bash deploy/gcp/site.sh            # what is online, and who may open it
bash deploy/gcp/site.sh deploy     # build and publish; again after every change
bash deploy/gcp/site.sh remove     # offline; the runs bucket stays
bash deploy/gcp/site.sh seed       # the default projects: assessed here, then put in the bucket
```

Settings live in `.env` (see `.env.example`): `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_REGION`, `SDLC360_SITE_VIEWERS`,
`SDLC360_GIT_HOSTS`, `SDLC360_GIT_TOKEN`, `SDLC360_SEED`, `SDLC360_SEED_SESSIONS`, and `CLOUDSDK_CONFIG` to use a gcloud
login other than your default one. The same `.env` serves the `gcp` skill (`.claude/skills/gcp`): its `services`,
`service sdlc360`, `logs sdlc360 --errors` and `rollback` work on the hosted app; `site.sh deploy` stays the way to
publish it (it uploads only `sdlc.py`, `src/` and `assessment/`, and grants the viewers).

The default projects in the project list are the reference set (`assessment/calibration/reference-set.json`) and
the repositories in `SDLC360_SEED` (none by default). `seed` assesses them on your
machine with 8 history points, keeps them in your `runs/` and copies each run to the bucket; run it again to refresh.

## What the hosted app does differently

`SDLC360_CLOUD=1` (set in the `Dockerfile`, read by `src/hosting.py`) turns the local tool into a shared one:

| Local (`./start.sh`) | Hosted |
|---|---|
| binds 127.0.0.1, rejects foreign `Host` / `Origin` | binds `0.0.0.0:$PORT`; requires IAP's signed-in user header and a same-site `Origin` |
| GitHub URLs and local folders | GitHub URLs and `https://<host>/<group>/.../<repo>` for the hosts in `SDLC360_GIT_HOSTS` only |
| folder browser | off: `/api/fs`, `/api/shutdown`, `/v1/*` answer 404 |
| Claude Code efficiency and Timeline from the logs on this machine | from sessions added in the browser, see below |
| `runs/` in the checkout | Cloud Storage bucket `<project>-sdlc360-runs` mounted at `/mnt/runs` |

Repositories of `SDLC360_GIT_HOSTS` are cloned with `SDLC360_GIT_TOKEN` (Secret Manager `sdlc360-git-token`). Git gets it
through `GIT_CONFIG_*` variables: it is not in a command line, an error message, a remote URL or `.git/config`, and it is
sent to the hosts in `SDLC360_GIT_HOSTS` only. Use a token with `read_repository` only, ideally of a technical account:
whoever can open the app can assess every repository that token can read.

## Claude Code efficiency without installing anything

The hosted app cannot read anyone's `~/.claude/projects`, so the numbers come to it:

- **Your project**: open it (assessed by URL), tab **Claude Code efficiency**, **Choose folder**, pick the project's
  folder under `%USERPROFILE%\.claude\projects`. The browser parses the logs itself (`parseSession` in
  `src/template.html`, the same as `agent_usage.parse_session`; `tests/unit/test_agent_upload.py` runs both on one log)
  and sends only numbers, times and skill names. The server checks them field by field (`agent_usage.clean_sessions`),
  joins them with the repository's commits and keeps both in the run (`agent_sessions.json`). Everyone who opens the
  app sees the result.
- **The demo**: `bash deploy/gcp/site.sh sessions` does the same for the repositories in `SDLC360_SEED_SESSIONS`
  (`url=working copy` pairs, none by default) with `python sdlc.py attach-sessions`,
  marks them `seed` (the app does not replace them) and copies them to the bucket. `seed` does it after each scan.

## Shape on Cloud Run

- One instance at most (`--max-instances=1`): scan jobs and the one-scan-at-a-time lock live in its memory.
- CPU always allocated (`--no-cpu-throttling`): a scan runs in a thread after the request that started it returns.
- 2 vCPU, 2 GiB: clones go to the instance's in-memory disk (`/tmp/repos`), blobless.
- Idle it scales to zero; the next visitor waits for a cold start of a few seconds.

## Known limits

- Profiles saved on the Criteria page and repositories added to the calibration set are written into the image
  (`assessment/`), so they are lost on the next deploy or cold start. Commit them to the repository instead.
- The service URL: `bash deploy/gcp/site.sh` prints it.
- Re-render of an old run reads the bucket through Cloud Storage FUSE: slower than a local disk, fine for this size.
