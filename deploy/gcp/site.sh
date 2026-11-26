#!/usr/bin/env bash
# SDLC360 on Cloud Run behind Google sign-in (Identity-Aware Proxy).
#   bash deploy/gcp/site.sh            # what is online, and who may open it
#   bash deploy/gcp/site.sh deploy     # build and publish; run it again after a change
#   bash deploy/gcp/site.sh remove     # take it offline (the bucket with the runs stays)
#   bash deploy/gcp/site.sh seed [target...]   # assess the default projects here and put them online: the reference set
#                                      # (assessment/calibration/reference-set.json) and SDLC360_SEED
#   bash deploy/gcp/site.sh sessions   # the demo of the Claude Code tabs: the numbers of the sessions in your working copies
#                                      # (SDLC360_SEED_SESSIONS) kept with their latest runs, then online; no text leaves
# Settings: .env (see .env.example). Who may open it: SDLC360_SITE_VIEWERS, comma separated
# (domain:example.com, user:someone@example.com, group:team@example.com); default only you.
# What runs where (docs/deploy-gcp.md):
#   service sdlc360       one instance at most: scan jobs live in its memory; CPU stays on so a scan finishes
#                         after the request that started it
#   bucket <project>-sdlc360-runs   runs/ mounted at /mnt/runs: every assessment survives and is shared
#   secret sdlc360-git-token        SDLC360_GIT_TOKEN, read only, to clone from SDLC360_GIT_HOSTS
#   account sdlc360-site            reads and writes the bucket, reads the secret; nothing else
# Idle, it costs nothing but the bucket: Cloud Run stops the instance.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# Settings: the environment, else ./.env (see .env.example), with the names of the gcp skill
if [ -f "$ROOT/.env" ]; then
    while IFS= read -r line || [ -n "$line" ]; do
        line="${line%$'\r'}"
        case "$line" in ''|\#*) continue ;; *=*) ;; *) continue ;; esac
        key="${line%%=*}"; value="${line#*=}"
        [ -n "$value" ] && [ -z "${!key+x}" ] && export "$key=$value"
    done < "$ROOT/.env"
fi
GCP_PROJECT="${GOOGLE_CLOUD_PROJECT:?set GOOGLE_CLOUD_PROJECT in .env}"
export CLOUDSDK_CORE_PROJECT="$GCP_PROJECT"
R="${GOOGLE_CLOUD_REGION:-us-central1}"
SERVICE=sdlc360
IMAGE="$R-docker.pkg.dev/$GCP_PROJECT/sdlc360/web:latest"
SA="sdlc360-site@$GCP_PROJECT.iam.gserviceaccount.com"
BUCKET="${SDLC360_BUCKET:-$GCP_PROJECT-sdlc360-runs}"
SECRET=sdlc360-git-token
LOGS="$ROOT/.cache/deploy"
# The repositories shown by default next to the reference set (space separated URLs)
SEED_EXTRA="${SDLC360_SEED:-}"

# url=working copy: whose Claude Code sessions (on this machine) the demo shows for that repository
SEED_SESSIONS="${SDLC360_SEED_SESSIONS:-}"

quiet() { local out; out="$("$@" 2>&1)" || { echo "$out" >&2; return 1; }; }
url() { gcloud run services describe "$SERVICE" --region "$R" --format='value(status.url)' 2>/dev/null || true; }

status() {
    local address
    address="$(url)"
    if [ -z "$address" ]; then echo "$SERVICE offline. Publish it with: bash deploy/gcp/site.sh deploy"; return 0; fi
    echo "$SERVICE online   $address"
    echo "May open it (sign-in with a Google account):"
    gcloud beta iap web get-iam-policy --region "$R" --resource-type=cloud-run --service="$SERVICE" \
        --flatten='bindings[].members' --format='value(bindings.members)' 2>/dev/null | sed 's/^/  /' || true
}

grant() {  # grant <member> <role>: a new service account takes some seconds to be known everywhere
    local try
    for try in 1 2 3 4 5 6; do
        quiet gcloud projects add-iam-policy-binding "$GCP_PROJECT" --member="$1" --role="$2" --condition=None > /dev/null 2>&1 && return 0
        sleep 10
    done
    echo "Could not give $2 to $1" >&2; exit 1
}

deploy() {
    local viewers number builder stage member secrets=()
    viewers="${SDLC360_SITE_VIEWERS:-user:$(gcloud config get-value account 2>/dev/null)}"
    mkdir -p "$LOGS"
    echo "== services: Cloud Run, Cloud Build, Artifact Registry, IAP, Secret Manager ($GCP_PROJECT, $R)"
    quiet gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
        iap.googleapis.com secretmanager.googleapis.com
    gcloud artifacts repositories describe sdlc360 --location="$R" > /dev/null 2>&1 \
        || quiet gcloud artifacts repositories create sdlc360 --location="$R" --repository-format=docker > /dev/null

    echo "== identity: sdlc360-site (the runs bucket, the git token)"
    gcloud iam service-accounts describe "$SA" > /dev/null 2>&1 \
        || quiet gcloud iam service-accounts create sdlc360-site --display-name="SDLC360 hosted app" > /dev/null

    echo "== runs: gs://$BUCKET"
    gcloud storage buckets describe "gs://$BUCKET" > /dev/null 2>&1 \
        || quiet gcloud storage buckets create "gs://$BUCKET" --location="$R" --uniform-bucket-level-access --public-access-prevention
    quiet gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" --member="serviceAccount:$SA" \
        --role=roles/storage.objectUser > /dev/null

    if [ -n "${SDLC360_GIT_TOKEN:-}" ]; then
        echo "== git host token: secret $SECRET (a new version when it changed)"
        gcloud secrets describe "$SECRET" > /dev/null 2>&1 \
            || quiet gcloud secrets create "$SECRET" --replication-policy=automatic > /dev/null
        if [ "$(gcloud secrets versions access latest --secret="$SECRET" 2>/dev/null || true)" != "$SDLC360_GIT_TOKEN" ]; then
            printf '%s' "$SDLC360_GIT_TOKEN" | quiet gcloud secrets versions add "$SECRET" --data-file=- > /dev/null
        fi
    fi
    if gcloud secrets describe "$SECRET" > /dev/null 2>&1; then
        quiet gcloud secrets add-iam-policy-binding "$SECRET" --role=roles/secretmanager.secretAccessor \
            --member="serviceAccount:$SA" > /dev/null
        secrets=(--set-secrets="SDLC360_GIT_TOKEN=$SECRET:latest")
    else
        echo "   no SDLC360_GIT_TOKEN: only public repositories can be assessed"
    fi

    echo "== image $IMAGE (Cloud Build; only sdlc.py, src/ and assessment/ are uploaded)"
    builder="$(gcloud builds get-default-service-account --region="$R" 2>/dev/null | tail -1)"
    quiet gcloud artifacts repositories add-iam-policy-binding sdlc360 --location="$R" --role=roles/artifactregistry.writer \
        --member="serviceAccount:${builder##*/}" > /dev/null
    stage="$(mktemp -d)"
    cp -r "$ROOT/sdlc.py" "$ROOT/src" "$ROOT/assessment" "$ROOT/Dockerfile" "$ROOT/.dockerignore" "$stage/"
    find "$stage" -name __pycache__ -prune -exec rm -rf {} +
    rm -rf "$stage"/assessment/references/*/local
    gcloud builds submit "$stage" --region="$R" --tag="$IMAGE" --quiet > "$LOGS/build.log" 2>&1 \
        || { tail -20 "$LOGS/build.log"; rm -rf "$stage"; exit 1; }
    rm -rf "$stage"

    echo "== publish behind the sign-in"
    number="$(gcloud projects describe "$GCP_PROJECT" --format='value(projectNumber)')"
    quiet gcloud beta services identity create --service=iap.googleapis.com > /dev/null 2>&1 || true
    # Git Bash: keep /mnt/runs as it is, not rewritten into a Windows path (only this argument; no effect elsewhere)
    MSYS2_ARG_CONV_EXCL="--add-volume-mount" quiet gcloud run deploy "$SERVICE" --image="$IMAGE" --region="$R" --service-account="$SA" \
        --execution-environment=gen2 --no-cpu-throttling --cpu=2 --memory=2Gi --timeout=300 \
        --min-instances=0 --max-instances=1 --concurrency=40 \
        --add-volume="name=runs,type=cloud-storage,bucket=$BUCKET,mount-options=implicit-dirs" --add-volume-mount="volume=runs,mount-path=/mnt/runs" \
        --set-env-vars="SDLC360_GIT_HOSTS=${SDLC360_GIT_HOSTS:-}" "${secrets[@]}" \
        --no-allow-unauthenticated --iap --quiet > /dev/null
    quiet gcloud run services add-iam-policy-binding "$SERVICE" --region="$R" --role=roles/run.invoker \
        --member="serviceAccount:service-$number@gcp-sa-iap.iam.gserviceaccount.com" > /dev/null
    for member in ${viewers//,/ }; do
        quiet gcloud beta iap web add-iam-policy-binding --region="$R" --resource-type=cloud-run --service="$SERVICE" \
            --member="$member" --role=roles/iap.httpsResourceAccessor > /dev/null
    done
    echo; status
}

python_here() { local py; py="$(ls "$ROOT"/.venv/Scripts/python.exe "$ROOT"/.venv/bin/python 2>/dev/null | head -1 || true)"; echo "${py:-python}"; }

attach_sessions() {   # attach_sessions <run folder name> <url>: the demo sessions of that repository, when mapped
    local pair folder
    for pair in $SEED_SESSIONS; do
        [ "${pair%%=*}" = "$2" ] || continue
        folder="${pair#*=}"; folder="$(cygpath -w "$folder" 2>/dev/null || echo "$folder")"   # Windows Python, Git Bash
        (cd "$ROOT" && "$(python_here)" sdlc.py attach-sessions "runs/$1" --folder "$folder" --origin seed) | sed 's/^/   /'
        quiet gcloud storage cp "$ROOT/runs/$1/agent_sessions.json" "gs://$BUCKET/$1/agent_sessions.json"
    done
}

sessions() {   # the mapped repositories: their latest run here gets the sessions
    local pair url name d
    export SDLC360_GIT_TOKEN="${SDLC360_GIT_TOKEN:-${GITLAB_TOKEN:-}}"   # the clones of SDLC360_GIT_HOSTS, here only
    for pair in $SEED_SESSIONS; do
        url="${pair%%=*}"; name="${url##*/}"
        d="$(ls -d "$ROOT"/runs/*_"$name" 2>/dev/null | tail -1 || true)"
        [ -n "$d" ] || { echo "== $url: no run here; assess it first: bash deploy/gcp/site.sh seed $url"; continue; }
        echo "== $url ($(basename "$d"))"
        attach_sessions "$(basename "$d")" "$url"
    done
}

seed() {   # assessed on this machine (into runs/, so the local app has them too), then copied to the bucket
    local py target before d failed=0
    py="$(ls "$ROOT"/.venv/Scripts/python.exe "$ROOT"/.venv/bin/python 2>/dev/null | head -1 || true)"; py="${py:-python}"
    # clones of SDLC360_GIT_HOSTS here use your GitLab token (local only; the hosted app has its own read-only one)
    export SDLC360_GIT_TOKEN="${SDLC360_GIT_TOKEN:-${GITLAB_TOKEN:-}}"
    local targets=("$@")   # given: only these; else the reference set and SEED_EXTRA
    [ ${#targets[@]} -gt 0 ] || targets=($("$py" -c "import json,sys;print(' '.join(r['target'] for r in json.load(open(sys.argv[1]))['repos']))"                       "$ROOT/assessment/calibration/reference-set.json") $SEED_EXTRA)
    for target in "${targets[@]}"; do
        echo "== $target"
        before="$(ls "$ROOT/runs")"
        if ! (cd "$ROOT" && "$py" sdlc.py scan "$target" --history 8 --refresh > "$LOGS/seed.log" 2>&1); then
            tail -3 "$LOGS/seed.log"; failed=$((failed + 1)); continue
        fi
        for d in $(comm -13 <(echo "$before") <(ls "$ROOT/runs")); do
            quiet gcloud storage rsync --recursive "$ROOT/runs/$d" "gs://$BUCKET/$d"
            echo "   online: $d"
            attach_sessions "$d" "$target"
        done
    done
    [ "$failed" = 0 ] || echo "$failed could not be assessed (see above)"
}

remove() {
    gcloud run services delete "$SERVICE" --region="$R" --quiet 2>/dev/null && echo "removed $SERVICE" || true
    echo "Offline. The runs stay in gs://$BUCKET; the image in Artifact Registry sdlc360."
}

case "${1:-status}" in
    status) status ;;
    deploy) deploy ;;
    remove) remove ;;
    seed) mkdir -p "$LOGS"; shift; seed "$@" ;;
    sessions) sessions ;;
    *) echo "Unknown command: $1 (deploy | remove | seed | sessions; without a command: what is online)" >&2; exit 2 ;;
esac
