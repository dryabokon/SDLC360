#!/usr/bin/env python3
"""Google Cloud for app work: Cloud Run services, their logs, deploys and rollbacks, buckets, secrets, Cloud SQL.

Read commands run straight away. Commands that change something (deploy, rollback, upload, secret-set) print the
exact gcloud commands they would run and do nothing else unless --apply is given - so a person can read, copy or
run the same plan by hand.

    python gcp.py whoami                                  account, project, region, enabled APIs that matter here
    python gcp.py services                                Cloud Run services: URL, revision, last deploy
    python gcp.py service NAME                            image, traffic, scaling, env names, secrets, mounts, access
    python gcp.py logs    NAME [--errors] [--since 1h] [--limit 50]
    python gcp.py deploy  NAME (--source DIR | --image IMAGE) [--env K=V]... [--secret ENV=SECRET[:VERSION]]...
                          [--mount BUCKET:/path] [--access public|private|iap] [--service-account SA]
                          [--min N] [--max N] [--cpu C] [--memory M] [--timeout S] [--cpu-always-on] [--repo R] [--apply]
    python gcp.py rollback NAME [--to REVISION] [--apply]   send all traffic to the previous (or given) revision
    python gcp.py buckets
    python gcp.py ls      gs://BUCKET[/PREFIX] [--limit N]
    python gcp.py upload  LOCAL gs://BUCKET[/PREFIX] [--apply]    rsync a folder (or copy a file)
    python gcp.py secrets                                  names and versions, never values
    python gcp.py secret-set NAME --from-env KEY [--env-file .env] [--apply]   value piped from .env, never printed
    python gcp.py sql                                      Cloud SQL instances

Every command takes --json, --project, --region.

Configuration - environment variables, or a .env file in the current directory or any parent:
    GOOGLE_CLOUD_PROJECT   project (default: gcloud config)
    GOOGLE_CLOUD_REGION    region for Cloud Run (default: gcloud config run/region, else europe-west1)
    GCP_ACCOUNT            gcloud account to use (default: the active one)
Authentication is your gcloud sign-in (`gcloud auth login`). Standard library only; Python 3.9+.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

# The APIs a source deploy needs; secrets and IAP add theirs.
DEPLOY_APIS = ["run.googleapis.com", "cloudbuild.googleapis.com", "artifactregistry.googleapis.com"]
AR_REPO = "cloud-run"  # Artifact Registry repository the skill builds into (one per region)


class Fail(SystemExit):
    def __init__(self, msg: str):
        super().__init__(f"error: {msg}")


# ------------------------------------------------------------------ configuration

def load_dotenv() -> None:
    for folder in [Path.cwd(), *Path.cwd().parents]:
        env = folder / ".env"
        if env.is_file():
            for line in env.read_text(encoding="utf-8").splitlines():
                m = re.match(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$", line)
                if m and not line.lstrip().startswith("#"):
                    val = m.group(2)
                    if len(val) >= 2 and val[0] == val[-1] and val[0] in "'\"":
                        val = val[1:-1]
                    else:
                        val = re.sub(r"\s+#.*$", "", val)
                    os.environ.setdefault(m.group(1), val)
            return


def short_error(stderr: str) -> str:
    """gcloud errors run to dozens of lines of YAML; keep the line that says what is wrong."""
    text = stderr.strip()
    if "SERVICE_DISABLED" in text or "has not been used in project" in text:
        api = re.search(r"service:\s*([\w.]+)|(\w[\w.]*\.googleapis\.com)", text)
        name = (api.group(1) or api.group(2)) if api else "an API"
        return f"{name} is not enabled in this project (enable it only if you mean to use it)"
    if "RESOURCE_EXHAUSTED" in text or " 429" in text:
        return "rate-limited by Google (quota per minute) - try again in a minute"
    if "Reauthentication" in text or "gcloud auth login" in text or "invalid_grant" in text:
        return "the gcloud sign-in has expired - run `gcloud auth login`"
    m = re.search(r"ERROR: \([^)]*\) (.+)", text)
    return (m.group(1) if m else text.splitlines()[-1] if text else "unknown error")[:400]


class G:
    """Runs gcloud for one project / region / account."""

    def __init__(self, a):
        self.exe = shutil.which("gcloud")
        if not self.exe:
            raise Fail("gcloud not found - install the Google Cloud SDK and run `gcloud auth login`")
        self.wsl_windows = bool(os.environ.get("WSL_DISTRO_NAME")) and self.exe.startswith("/mnt/")
        self.project = a.project or os.environ.get("GOOGLE_CLOUD_PROJECT") or self.config("core/project")
        if not self.project:
            raise Fail("no project: set GOOGLE_CLOUD_PROJECT (env or .env) or pass --project")
        self.region = a.region or os.environ.get("GOOGLE_CLOUD_REGION") or self.config("run/region") or "europe-west1"
        self.account = os.environ.get("GCP_ACCOUNT") or None

    def config(self, key: str) -> str | None:
        res = subprocess.run([self.exe, "config", "get-value", key], capture_output=True, text=True, timeout=60)
        return res.stdout.strip() or None

    def base(self) -> list[str]:
        b = [f"--project={self.project}", "--quiet"]
        return b + [f"--account={self.account}"] if self.account else b

    def path(self, p: str) -> str:
        """Paths for gcloud: a Windows gcloud called from WSL needs Windows paths."""
        if self.wsl_windows and not p.startswith("gs://"):
            return subprocess.run(["wslpath", "-w", str(Path(p).resolve())], capture_output=True, text=True).stdout.strip()
        return str(Path(p).resolve()) if not p.startswith("gs://") else p

    def json(self, *args: str, ok_missing: bool = False):
        res = subprocess.run([self.exe, *args, *self.base(), "--format=json"], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=300, env={**os.environ, "MSYS_NO_PATHCONV": "1"})
        if res.returncode:
            if ok_missing and re.search(r"NOT_FOUND|[Nn]ot found|does not exist|[Cc]annot find|404", res.stderr):
                return None
            raise Fail(short_error(res.stderr))
        return json.loads(res.stdout or "null")

    def cmdline(self, *args: str) -> list[str]:
        return ["gcloud", *args, *self.base()]

    def run(self, argv: list[str], stdin_bytes: bytes | None = None) -> None:
        """Execute one planned command (argv starts with 'gcloud'), streaming its output."""
        res = subprocess.run([self.exe, *argv[1:]], input=stdin_bytes, env={**os.environ, "MSYS_NO_PATHCONV": "1"})
        if res.returncode:
            raise Fail(f"step failed (exit {res.returncode}): {shell(argv)}")


def shell(argv: list[str]) -> str:
    return " ".join(shlex.quote(x) for x in argv)


def table(rows: list[dict], cols: list[str], width: int = 60) -> str:
    if not rows:
        return "(none)"
    w = {c: min(max(len(c), *(len(str(r.get(c, ""))) for r in rows)), width) for c in cols}
    line = lambda r: "  ".join(str(r.get(c, ""))[:w[c]].ljust(w[c]) for c in cols).rstrip()
    return "\n".join([line({c: c for c in cols}), line({c: "-" * w[c] for c in cols})] + [line(r) for r in rows])


def human_size(n) -> str:
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "-"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return "-"


def when(ts: str | None) -> str:
    m = re.match(r"(\d{4}-\d\d-\d\d)T(\d\d:\d\d)", ts or "")
    return f"{m.group(1)} {m.group(2)}" if m else "-"


def plan_output(steps: list[tuple[str, list[str]]], applied: bool, notes: list[str]):
    out = {"applied": applied, "steps": [{"why": why, "command": shell(argv)} for why, argv in steps], "notes": notes}

    def show(o):
        head = "Done:" if o["applied"] else "Plan (nothing was changed; add --apply to run it):"
        lines = [head] + [f"\n# {s['why']}\n{s['command']}" for s in o["steps"]]
        return "\n".join(lines + ([""] + [f"note: {n}" for n in o["notes"]] if o["notes"] else []))
    return out, show


# ------------------------------------------------------------------ read commands

def cmd_whoami(a):
    g = G(a)
    account = g.account or g.config("core/account")
    enabled = {s["config"]["name"] for s in (g.json("services", "list", "--enabled") or [])}
    watch = ["run.googleapis.com", "cloudbuild.googleapis.com", "artifactregistry.googleapis.com", "storage.googleapis.com",
             "secretmanager.googleapis.com", "iap.googleapis.com", "sqladmin.googleapis.com", "bigquery.googleapis.com",
             "logging.googleapis.com"]
    out = {"account": account, "project": g.project, "region": g.region,
           "enabled": [x.split(".")[0] for x in watch if x in enabled],
           "not enabled": [x.split(".")[0] for x in watch if x not in enabled]}
    return out, lambda o: "\n".join(f"{k:<12} {', '.join(v) if isinstance(v, list) else v}" for k, v in o.items())


def cmd_services(a):
    g = G(a)
    rows = []
    for s in g.json("run", "services", "list") or []:
        md, st = s["metadata"], s.get("status", {})
        ready = next((c.get("status") for c in st.get("conditions", []) if c.get("type") == "Ready"), "?")
        rows.append({"service": md["name"], "region": md.get("labels", {}).get("cloud.googleapis.com/location"),
                     "ready": {"True": "yes", "False": "NO"}.get(ready, ready), "url": st.get("url"),
                     "revision": st.get("latestReadyRevisionName"),
                     "deployed": when(next((c.get("lastTransitionTime") for c in st.get("conditions", [])
                                            if c.get("type") == "Ready"), None)),
                     "by": md.get("annotations", {}).get("serving.knative.dev/lastModifier")})
    return rows, lambda o: table(o, ["service", "region", "ready", "revision", "deployed", "by", "url"])


def cmd_service(a):
    g = G(a)
    s = g.json("run", "services", "describe", a.name, f"--region={g.region}")
    md, spec, st = s["metadata"], s["spec"]["template"], s.get("status", {})
    c = spec["spec"]["containers"][0]
    ann = {**md.get("annotations", {}), **spec["metadata"].get("annotations", {})}
    env, secrets = [], []
    for e in c.get("env", []):
        ref = (e.get("valueFrom") or {}).get("secretKeyRef")
        if ref:
            secrets.append(f"{e['name']} <- secret {ref.get('name')}:{ref.get('key', 'latest')}")
        else:
            env.append(e["name"])  # names only: values may be sensitive
    mounts = []
    vols = {v["name"]: v for v in spec["spec"].get("volumes", [])}
    for vm in c.get("volumeMounts", []):
        v = vols.get(vm["name"], {})
        src = (v.get("csi") or {}).get("volumeAttributes", {}).get("bucketName") or (v.get("secret") or {}).get("secretName") or "?"
        mounts.append(f"{vm['mountPath']} <- {src}")
    policy = g.json("run", "services", "get-iam-policy", a.name, f"--region={g.region}") or {}
    invokers = [m for b in policy.get("bindings", []) if b.get("role") == "roles/run.invoker" for m in b.get("members", [])]
    iap = ann.get("run.googleapis.com/iap-enabled") == "true"
    access = "PUBLIC (allUsers may invoke)" if "allUsers" in invokers else \
        "Google sign-in (IAP)" if iap else "private (IAM: " + (", ".join(invokers) or "no invokers") + ")"
    lim = c.get("resources", {}).get("limits", {})
    out = {"service": a.name, "region": g.region, "url": st.get("url"), "image": c.get("image"),
           "service account": spec["spec"].get("serviceAccountName"),
           "traffic": [f"{t.get('percent', 0)}% -> {t.get('revisionName') or 'latest'}" for t in st.get("traffic", [])],
           "scaling": f"min {ann.get('autoscaling.knative.dev/minScale', 0)}, max {ann.get('autoscaling.knative.dev/maxScale', '?')}",
           "resources": f"cpu {lim.get('cpu', '?')}, memory {lim.get('memory', '?')}, timeout {spec['spec'].get('timeoutSeconds', '?')}s"
                        + (", cpu always on" if ann.get("run.googleapis.com/cpu-throttling") == "false" else ""),
           "access": access, "ingress": md.get("annotations", {}).get("run.googleapis.com/ingress", "all"),
           "env (names)": env, "secrets": secrets, "mounts": mounts}
    revs = g.json("run", "revisions", "list", f"--service={a.name}", f"--region={g.region}", "--limit=5") or []
    out["revisions"] = [{"revision": r["metadata"]["name"], "created": when(r["metadata"].get("creationTimestamp")),
                         "image": r["spec"]["containers"][0]["image"].rsplit("/", 1)[-1]} for r in revs]

    def show(o):
        lines = [f"{k:<16} {', '.join(v) if isinstance(v, list) else v}" for k, v in o.items()
                 if k != "revisions" and v not in ([], None, "")]
        return "\n".join(lines + ["", "Recent revisions:", table(o["revisions"], ["revision", "created", "image"])])
    return out, show


def cmd_logs(a):
    g = G(a)
    flt = f'resource.type="cloud_run_revision" AND resource.labels.service_name="{a.name}"'
    if a.errors:
        flt += ' AND (severity>=ERROR OR httpRequest.status>=500)'
    entries = g.json("logging", "read", flt, f"--freshness={a.since}", f"--limit={a.limit}", "--order=desc") or []
    rows = []
    for e in reversed(entries):
        hr = e.get("httpRequest") or {}
        if hr:
            msg = f"{hr.get('requestMethod', '')} {hr.get('status', '')} {hr.get('requestUrl', '')} {hr.get('latency', '')}"
        else:
            p = e.get("jsonPayload") or {}
            msg = e.get("textPayload") or p.get("message") or p.get("msg") or json.dumps(p)[:300]
        rows.append({"time": when(e.get("timestamp")) + e.get("timestamp", "")[16:19], "severity": e.get("severity", "-"),
                     "message": " ".join(str(msg).split())[:300]})
    note = f"{len(rows)} entries, last {a.since}" + (" (errors and 5xx only)" if a.errors else "")
    return rows, lambda o: (table(o, ["time", "severity", "message"], 300) + f"\n\n{note}") if o else f"(no log entries: {note})"


def cmd_buckets(a):
    g = G(a)
    rows = [{"bucket": b["name"], "location": b.get("location"), "class": b.get("default_storage_class") or b.get("storageClass"),
             "public access": b.get("public_access_prevention", "inherited"),
             "uniform": b.get("uniform_bucket_level_access")} for b in g.json("storage", "buckets", "list") or []]
    return rows, lambda o: table(o, ["bucket", "location", "class", "public access", "uniform"])


def cmd_ls(a):
    g = G(a)
    if not a.url.startswith("gs://"):
        raise Fail("give gs://BUCKET[/PREFIX]")
    pattern = a.url.rstrip("/") + ("/**" if a.url.count("/") <= 3 or a.url.endswith("/") else "**")
    items = g.json("storage", "objects", "list", pattern, f"--limit={a.limit + 1}") or []
    bucket_prefix = "gs://" + a.url[5:].split("/", 1)[0] + "/"
    rows = [{"object": re.sub(r"#\d+$", "", (i.get("url") or i.get("storage_url") or i.get("name", "")).replace(bucket_prefix, "", 1)),
             "size": human_size(i.get("size")), "updated": when(i.get("update_time") or i.get("updated"))}
            for i in items[:a.limit]]
    more = f"\n(first {a.limit} shown; --limit for more)" if len(items) > a.limit else ""
    return rows, lambda o: table(o, ["object", "size", "updated"], 100) + more


def cmd_secrets(a):
    g = G(a)
    rows = []
    for s in g.json("secrets", "list") or []:
        name = s["name"].rsplit("/", 1)[-1]
        vers = g.json("secrets", "versions", "list", name, "--filter=state=enabled", "--limit=50") or []
        rows.append({"secret": name, "enabled versions": len(vers), "latest": when(vers[0].get("createTime")) if vers else "-",
                     "created": when(s.get("createTime"))})
    return rows, lambda o: table(o, ["secret", "enabled versions", "latest", "created"])


def cmd_sql(a):
    g = G(a)
    try:
        inst = g.json("sql", "instances", "list") or []
    except Fail as e:
        if "sqladmin" in str(e):
            return [], lambda o: "No Cloud SQL here: the Cloud SQL Admin API is not enabled in this project."
        raise
    rows = [{"instance": i["name"], "version": i.get("databaseVersion"), "tier": i.get("settings", {}).get("tier"),
             "state": i.get("state"), "region": i.get("region"),
             "public ip": next((x["ipAddress"] for x in i.get("ipAddresses", []) if x.get("type") == "PRIMARY"), "-")}
            for i in inst]
    return rows, lambda o: table(o, ["instance", "version", "tier", "state", "region", "public ip"])


# ------------------------------------------------------------------ change commands (plan, then --apply)

def cmd_deploy(a):
    g = G(a)
    if bool(a.source) == bool(a.image):
        raise Fail("give exactly one of --source DIR (build with Cloud Build) or --image IMAGE")
    steps: list[tuple[str, list[str]]] = []
    notes: list[str] = []
    enabled = {s["config"]["name"] for s in (g.json("services", "list", "--enabled") or [])}
    apis = list(DEPLOY_APIS if a.source else DEPLOY_APIS[:1])
    if a.secret:
        apis.append("secretmanager.googleapis.com")
    if a.access == "iap":
        apis.append("iap.googleapis.com")
    missing = [x for x in apis if x not in enabled]
    if missing:
        steps.append(("enable the APIs this deploy needs", g.cmdline("services", "enable", *missing)))

    image = a.image
    if a.source:
        src = Path(a.source)
        if not (src / "Dockerfile").is_file():
            notes.append("no Dockerfile in --source: Cloud Build will use Google buildpacks to detect the language")
        if not (src / ".gcloudignore").is_file():
            notes.append("no .gcloudignore: everything in the folder except .gitignore'd files is uploaded - "
                         "add one listing .env, .git, .venv, data you do not need")
        # An existing service keeps building into the repository its current image lives in.
        current = g.json("run", "services", "describe", a.name, f"--region={g.region}", ok_missing=True)
        cur_image = ((current or {}).get("spec", {}).get("template", {}).get("spec", {}).get("containers") or [{}])[0].get("image", "")
        m = re.match(r"^([\w-]+-docker\.pkg\.dev/[^/]+/[^/]+)/", cur_image)
        if a.repo:
            registry = f"{g.region}-docker.pkg.dev/{g.project}/{a.repo}"
        elif m:
            registry = m.group(1)
            notes.append(f"building into the service's existing repository {registry}")
        else:
            registry = f"{g.region}-docker.pkg.dev/{g.project}/{AR_REPO}"
        repo_name = registry.rsplit("/", 1)[-1]
        if not g.json("artifacts", "repositories", "describe", repo_name, f"--location={g.region}", ok_missing=True):
            steps.append((f"Artifact Registry repository for images ({repo_name}, {g.region})",
                          g.cmdline("artifacts", "repositories", "create", repo_name, f"--location={g.region}",
                                    "--repository-format=docker")))
        image = f"{registry}/{a.name}:{time.strftime('%Y%m%d-%H%M%S')}"
        steps.append(("build the image in Cloud Build (the source is uploaded, not your local Docker)",
                      g.cmdline("builds", "submit", g.path(a.source), f"--tag={image}")))

    for s in a.secret or []:
        env_name, _, ref = s.partition("=")
        secret_name = ref.split(":")[0]
        if not g.json("secrets", "describe", secret_name, ok_missing=True):
            raise Fail(f"secret {secret_name!r} does not exist - create it first: gcp.py secret-set {secret_name} --from-env {env_name}")
    if a.service_account and not g.json("iam", "service-accounts", "describe", a.service_account, ok_missing=True):
        steps.append(("dedicated service account (no roles until you grant them)",
                      g.cmdline("iam", "service-accounts", "create", a.service_account.split("@")[0])))

    deploy = ["run", "deploy", a.name, f"--image={image}", f"--region={g.region}"]
    if a.service_account:
        deploy.append(f"--service-account={a.service_account}")
        for s in a.secret or []:
            steps.append((f"let the service account read secret {s.split('=')[1].split(':')[0]}",
                          g.cmdline("secrets", "add-iam-policy-binding", s.split("=")[1].split(":")[0],
                                    f"--member=serviceAccount:{a.service_account}", "--role=roles/secretmanager.secretAccessor")))
    deploy += {"public": ["--allow-unauthenticated"], "private": ["--no-allow-unauthenticated"],
               "iap": ["--no-allow-unauthenticated", "--iap"]}[a.access]
    if a.env:
        deploy.append("--update-env-vars=" + ",".join(a.env))
    if a.secret:
        deploy.append("--update-secrets=" + ",".join(x if ":" in x.split("=", 1)[1] else x + ":latest" for x in a.secret))
    for m in a.mount or []:
        bucket, _, mpath = m.partition(":")
        vol = re.sub(r"[^a-z0-9-]", "-", bucket.lower())[:40]
        deploy += ["--execution-environment=gen2", f"--add-volume=name={vol},type=cloud-storage,bucket={bucket}",
                   f"--add-volume-mount=volume={vol},mount-path={mpath}"]
    for flag, val in (("--min-instances", a.min), ("--max-instances", a.max), ("--cpu", a.cpu),
                      ("--memory", a.memory), ("--timeout", a.timeout)):
        if val is not None:
            deploy.append(f"{flag}={val}")
    if a.cpu_always_on:
        deploy.append("--no-cpu-throttling")  # work that continues after the response (background jobs) keeps CPU
    steps.append(("deploy a new revision (traffic moves to it when it is ready)", g.cmdline(*deploy)))
    if a.access == "public":
        notes.append("--access public: anyone on the internet can call this URL")
    if a.access == "iap":
        notes.append("IAP: grant people with `gcloud iap web add-iam-policy-binding --resource-type=cloud-run "
                     f"--service={a.name} --region={g.region} --member=user:EMAIL --role=roles/iap.httpsResourceAccessor`")
    if a.apply:
        for why, argv in steps:
            print(f"\n== {why}\n$ {shell(argv)}", file=sys.stderr)
            g.run(argv)
    return plan_output(steps, a.apply, notes)


def cmd_rollback(a):
    g = G(a)
    s = g.json("run", "services", "describe", a.name, f"--region={g.region}")
    serving = [t.get("revisionName") for t in s.get("status", {}).get("traffic", []) if t.get("percent")]
    target = a.to
    if not target:
        revs = g.json("run", "revisions", "list", f"--service={a.name}", f"--region={g.region}", "--limit=10") or []
        ready = [r["metadata"]["name"] for r in revs
                 if any(c.get("type") == "Ready" and c.get("status") == "True" for c in r.get("status", {}).get("conditions", []))]
        older = [r for r in ready if r not in serving]
        if not older:
            raise Fail(f"no other ready revision to roll back to (serving: {', '.join(serving)})")
        target = older[0]
    steps = [(f"send 100% of traffic to {target} (now serving: {', '.join(serving)})",
              g.cmdline("run", "services", "update-traffic", a.name, f"--region={g.region}", f"--to-revisions={target}=100"))]
    notes = ["new deploys move traffic to the new revision again; to stay pinned, deploy with --no-traffic"]
    if a.apply:
        for why, argv in steps:
            print(f"\n== {why}\n$ {shell(argv)}", file=sys.stderr)
            g.run(argv)
    return plan_output(steps, a.apply, notes)


def cmd_upload(a):
    g = G(a)
    if not a.dest.startswith("gs://"):
        raise Fail("destination must be gs://BUCKET[/PREFIX]")
    src = Path(a.local)
    if not src.exists():
        raise Fail(f"{a.local} does not exist")
    argv = g.cmdline("storage", "rsync", g.path(a.local), a.dest, "--recursive") if src.is_dir() else \
        g.cmdline("storage", "cp", g.path(a.local), a.dest)
    files = sum(1 for p in src.rglob("*") if p.is_file()) if src.is_dir() else 1
    steps = [(f"{'sync' if src.is_dir() else 'copy'} {files} file(s) to {a.dest} (rsync uploads only what changed; "
              "it never deletes without --delete-unmatched-destination-objects)", argv)]
    if a.apply:
        print(f"$ {shell(argv)}", file=sys.stderr)
        g.run(argv)
    return plan_output(steps, a.apply, [])


def read_env_value(env_file: str, key: str) -> str:
    path = Path(env_file)
    if not path.is_file():
        raise Fail(f"{env_file} not found")
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(rf"\s*(?:export\s+)?{re.escape(key)}\s*=\s*(.*)\s*$", line)
        if m:
            v = m.group(1).strip()
            return v[1:-1] if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"" else v
    raise Fail(f"{key} is not in {env_file}")


def cmd_secret_set(a):
    g = G(a)
    value = read_env_value(a.env_file, a.from_env)  # never printed
    if not value:
        raise Fail(f"{a.from_env} is empty in {a.env_file}")
    steps = []
    if not g.json("secrets", "describe", a.name, ok_missing=True):
        steps.append((f"create secret {a.name}", g.cmdline("secrets", "create", a.name, "--replication-policy=automatic")))
    steps.append((f"add a new version from {a.from_env} in {a.env_file} (piped on stdin; the value is never shown)",
                  g.cmdline("secrets", "versions", "add", a.name, "--data-file=-")))
    if a.apply:
        for why, argv in steps:
            print(f"$ {shell(argv)}", file=sys.stderr)
            g.run(argv, stdin_bytes=value.encode() if "--data-file=-" in argv else None)
    return plan_output(steps, a.apply, ["services read it as --secret ENV=NAME (latest) on the next deploy"])


# ------------------------------------------------------------------ main

def main() -> int:
    load_dotenv()
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="machine-readable output")
    common.add_argument("--project", help="project (default: GOOGLE_CLOUD_PROJECT, then gcloud config)")
    common.add_argument("--region", help="region (default: GOOGLE_CLOUD_REGION, then gcloud config run/region)")

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, fn, help_):
        s = sub.add_parser(name, parents=[common], help=help_)
        s.set_defaults(fn=fn)
        return s

    add("whoami", cmd_whoami, "account, project, region, enabled APIs")
    add("services", cmd_services, "Cloud Run services")
    add("service", cmd_service, "one Cloud Run service in detail").add_argument("name")
    s = add("logs", cmd_logs, "logs of a Cloud Run service"); s.add_argument("name")
    s.add_argument("--errors", action="store_true"); s.add_argument("--since", default="1h"); s.add_argument("--limit", type=int, default=50)
    s = add("deploy", cmd_deploy, "build and deploy to Cloud Run (plan unless --apply)"); s.add_argument("name")
    s.add_argument("--source"); s.add_argument("--image"); s.add_argument("--env", action="append", metavar="K=V")
    s.add_argument("--secret", action="append", metavar="ENV=SECRET[:VERSION]"); s.add_argument("--mount", action="append", metavar="BUCKET:/path")
    s.add_argument("--access", choices=["public", "private", "iap"], default="private")
    s.add_argument("--service-account"); s.add_argument("--min", type=int); s.add_argument("--max", type=int)
    s.add_argument("--cpu"); s.add_argument("--memory"); s.add_argument("--timeout", type=int)
    s.add_argument("--cpu-always-on", action="store_true", help="keep CPU after the response (background work)")
    s.add_argument("--repo", help="Artifact Registry repository (default: the service's current one, else cloud-run)")
    s.add_argument("--apply", action="store_true")
    s = add("rollback", cmd_rollback, "traffic back to the previous revision (plan unless --apply)"); s.add_argument("name")
    s.add_argument("--to"); s.add_argument("--apply", action="store_true")
    add("buckets", cmd_buckets, "Cloud Storage buckets")
    s = add("ls", cmd_ls, "objects in a bucket"); s.add_argument("url"); s.add_argument("--limit", type=int, default=50)
    s = add("upload", cmd_upload, "sync a folder or copy a file to a bucket (plan unless --apply)")
    s.add_argument("local"); s.add_argument("dest"); s.add_argument("--apply", action="store_true")
    add("secrets", cmd_secrets, "Secret Manager secrets (names, versions)")
    s = add("secret-set", cmd_secret_set, "new secret version from a .env key (plan unless --apply)"); s.add_argument("name")
    s.add_argument("--from-env", required=True, metavar="KEY"); s.add_argument("--env-file", default=".env")
    s.add_argument("--apply", action="store_true")
    add("sql", cmd_sql, "Cloud SQL instances")

    a = p.parse_args()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    data, show = a.fn(a)
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str) if a.json else show(data))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
