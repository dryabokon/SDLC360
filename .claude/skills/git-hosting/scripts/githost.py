#!/usr/bin/env python3
"""GitHub and GitLab from the command line: pull / merge requests, CI runs, issues, authenticated git.

Same commands for both hosts (and the same shape as the azure-devops skill). Read-only by default; the only
writes are `pr-create --apply` and `git push`. Nothing here merges, approves, comments or deletes.

    python githost.py whoami                          host, repository, user
    python githost.py prs     [--mine | --reviewing] [--state open|closed|merged|all] [--top N]
    python githost.py pr      N|URL                   reviews / approvals, CI checks, unresolved threads
    python githost.py pr-create --source B [--target B] --title T (--body-file F | --body B) [--draft] [--apply]
    python githost.py runs    [--failed] [--branch B] [--top N]          CI runs (Actions / pipelines)
    python githost.py run     ID|URL|last-failed [--branch B] [--log-lines N]
                              failed jobs (first to fail first), their errors, error lines from the log, log tail
    python githost.py issues  [--mine] [--state open|closed|all] [--top N]
    python githost.py issue   N|URL
    python githost.py git     <git args...>           run git with the token as an HTTP header (push, fetch, ...)

The repository comes from --repo (owner/name or group/project), a URL argument, or `git remote get-url origin`
of the current folder. Every command takes --json, --repo, --remote, --timeout.

Configuration - environment variables, or a .env file in the current directory or any parent:
    GH_TOKEN (or GITHUB_TOKEN)     GitHub token; optional for reading public repositories (not for CI logs)
    GITLAB_TOKEN                   GitLab token; optional for public projects
    GITLAB_HOST                    GitLab URL when there is no git remote to infer it from (default https://gitlab.com)
Standard library only; Python 3.9+.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
ERROR_LINE = re.compile(r"(?i)\b(error|errors|failed|failure|fatal|exception|traceback|assert(ion)?error|panic|denied|"
                        r"not found|no such file|timed? ?out|exit(ed)? (with )?(code|status) [1-9])\b")
NOISE_LINE = re.compile(r"(?i)^##\[(group|endgroup|section|command)\]|\b0 (errors?|failed|failures)\b|"
                        r"\"errors?\":\s*(\[\]|0|null)|--fail|ignore.?errors|continue-on-error|set -e")


class Fail(SystemExit):
    def __init__(self, msg: str):
        super().__init__(f"error: {msg}")


# ------------------------------------------------------------------ configuration

def load_dotenv() -> None:
    """First .env from the current directory upwards; never overrides variables already set."""
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


def parse_remote(url: str) -> tuple[str, str]:
    """git remote / web URL -> (host, 'owner/name' or 'group/sub/project')."""
    url = url.strip()
    m = re.match(r"^(?:ssh://)?git@([^:/]+)[:/](.+?)(?:\.git)?/?$", url) or \
        re.match(r"^https?://(?:[^@/]+@)?([^/]+)/(.+?)(?:\.git)?/?$", url)
    if not m:
        raise Fail(f"cannot read a host and repository from {url!r}")
    host, path = m.group(1), m.group(2)
    path = re.split(r"/-/|/(?:pull|pulls|issues|actions|commit|tree|blob)/", path)[0].strip("/")
    return host.lower(), path


def url_target(url: str) -> dict:
    """Web URL of a PR / MR / run / pipeline / issue -> what it points to."""
    host, repo = parse_remote(url)
    out = {"host": host, "repo": repo}
    for kind, rx in (("pr", r"/(?:pull|-/merge_requests)/(\d+)"), ("run", r"/actions/runs/(\d+)|/-/pipelines/(\d+)"),
                     ("issue", r"/(?:-/)?issues/(\d+)"), ("job", r"/-/jobs/(\d+)")):
        m = re.search(rx, url)
        if m:
            out.update(kind=kind, id=int(next(g for g in m.groups() if g)))
            break
    return out


class _SameHostAuthRedirect(urllib.request.HTTPRedirectHandler):
    """Follow redirects, but never carry credentials to another host (GitHub sends logs via a signed blob URL)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and urllib.parse.urlparse(newurl).netloc != urllib.parse.urlparse(req.full_url).netloc:
            for h in ("Authorization", "Private-token", "PRIVATE-TOKEN"):
                new.headers.pop(h, None)
                new.unredirected_hdrs.pop(h, None)
        return new


OPENER = urllib.request.build_opener(_SameHostAuthRedirect)


class Host:
    """One API client; subclasses know GitHub and GitLab."""
    kind = ""

    def __init__(self, host: str, repo: str, timeout: float):
        self.host, self.repo, self.timeout = host, repo, timeout

    def call(self, url: str, params: dict | None = None, body=None, method: str | None = None,
             text: bool = False, headers: dict | None = None):
        params = {k: v for k, v in (params or {}).items() if v not in (None, "")}
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params, doseq=True)
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method or ("POST" if data else "GET"),
                                     headers={**self.auth(), "User-Agent": "skills-for-agents-githost",
                                              "Content-Type": "application/json", **(headers or {})})
        try:
            with OPENER.open(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            try:
                d = json.loads(detail)
                detail = d.get("message") or d.get("error") or detail
            except (ValueError, AttributeError):
                pass
            src = getattr(self, "token_source", None)
            hint = {401: (f" - the token from {src} was rejected (revoked or expired); replace it, or set "
                          f"{self.token_var} in .env, which wins") if src else f" - set {self.token_var}",
                    403: f" - not allowed or rate-limited; a {self.token_var} with more scopes may help",
                    404: f" - not found, or private and {self.token_var} is missing"}.get(e.code, "")
            raise Fail(f"HTTP {e.code} for {url.split('?')[0]}{hint}\n  {str(detail)[:300]}")
        except (urllib.error.URLError, TimeoutError) as e:
            raise Fail(f"cannot reach {self.host}: {getattr(e, 'reason', e)}")
        return raw if text else (json.loads(raw) if raw.strip() else {})


def tail_and_errors(log: str, n: int, known: list[str] | None = None) -> tuple[list[str], list[str]]:
    """The log tail up to the last `##[error]` (what follows is post-job cleanup), plus error-looking lines from
    anywhere in the log that are not already in the tail or in `known` (annotations shown separately)."""
    clean = [ANSI.sub("", re.sub(r"^\d{4}-\d\d-\d\dT[\d:.]+Z\s", "", l)).rstrip() for l in log.splitlines()]
    marks = [i for i, l in enumerate(clean) if "##[error]" in l]
    end = marks[-1] + 1 if marks else len(clean)
    tail = clean[max(0, end - n):end] if n else []
    seen = set(tail)
    fragments = [k.split(" ", 1)[-1].strip()[:60] for k in (known or []) if k.strip()]
    hits = [l.strip() for l in clean if ERROR_LINE.search(l) and not NOISE_LINE.search(l.strip()) and l not in seen
            and not any(f and f in l for f in fragments)]
    return tail, list(dict.fromkeys(hits))[-15:]


def when(ts: str | None) -> str:
    m = re.match(r"(\d{4}-\d\d-\d\d)T(\d\d:\d\d)", ts or "")
    return f"{m.group(1)} {m.group(2)}" if m else "-"


# ------------------------------------------------------------------ GitHub

class GitHub(Host):
    kind, token_var = "github", "GH_TOKEN"

    def __init__(self, host, repo, timeout):
        super().__init__(host, repo, timeout)
        self.api = "https://api.github.com" if host == "github.com" else f"https://{host}/api/v3"
        self.token_source = next((v for v in ("GH_TOKEN", "GITHUB_TOKEN") if os.environ.get(v)), None)
        self.token = os.environ.get(self.token_source, "") if self.token_source else ""

    def auth(self):
        h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        return {**h, "Authorization": f"Bearer {self.token}"} if self.token else h

    def r(self, path=""):
        return f"{self.api}/repos/{self.repo}{path}"

    def web(self, path=""):
        return f"https://{self.host}/{self.repo}{path}"

    def me(self):
        if not self.token:
            raise Fail("this needs GH_TOKEN")
        return self.call(f"{self.api}/user")["login"]

    def whoami(self):
        repo = self.call(self.r())
        user = None
        if self.token:
            try:
                user = self.me()
            except Fail:  # app tokens (GitHub Actions' GITHUB_TOKEN) may read the repo but not /user
                user = "(token works for the repository; it is not a user token)"
        return {"host": self.host, "repo": self.repo, "default branch": repo.get("default_branch"),
                "visibility": repo.get("visibility"), "user": user,
                "auth": f"token from {self.token_source}" if self.token else "anonymous"}

    def prs(self, a):
        q = f"repo:{self.repo} is:pr"
        q += {"open": " is:open", "closed": " is:closed is:unmerged", "merged": " is:merged", "all": ""}[a.state]
        if a.mine:
            q += " author:@me"
        if a.reviewing:
            q += " review-requested:@me"
        if (a.mine or a.reviewing) and not self.token:
            raise Fail("--mine / --reviewing need GH_TOKEN")
        items = self.call(f"{self.api}/search/issues", {"q": q, "per_page": a.top, "sort": "updated"})["items"]
        return [{"id": i["number"], "title": i["title"], "author": i["user"]["login"],
                 "state": ("merged" if (i.get("pull_request") or {}).get("merged_at") else i["state"])
                 + (" (draft)" if i.get("draft") else ""), "updated": when(i.get("updated_at"))} for i in items]

    def pr(self, n):
        p = self.call(self.r(f"/pulls/{n}"))
        out = {"id": n, "title": p["title"], "url": p["html_url"], "author": p["user"]["login"],
               "source": p["head"]["ref"], "target": p["base"]["ref"],
               "state": "merged" if p.get("merged") else p["state"] + (" (draft)" if p.get("draft") else ""),
               "mergeable": p.get("mergeable_state"), "description": (p.get("body") or "")[:1500]}
        reviews = {}
        for rv in self.call(self.r(f"/pulls/{n}/reviews"), {"per_page": 100}):
            if rv.get("state") != "COMMENTED" or rv["user"]["login"] not in reviews:
                reviews[rv["user"]["login"]] = rv["state"].lower().replace("_", " ")
        for u in p.get("requested_reviewers", []):
            reviews.setdefault(u["login"], "review requested")
        out["reviews"] = [{"who": k, "state": v} for k, v in reviews.items()]
        runs = self.call(self.r(f"/commits/{p['head']['sha']}/check-runs"), {"per_page": 100}).get("check_runs", [])
        out["checks"] = [{"name": c["name"], "status": c.get("conclusion") or c.get("status"),
                          "run": int(m.group(1)) if (m := re.search(r"/actions/runs/(\d+)", c.get("html_url") or "")) else None}
                         for c in runs]
        out["unresolved_threads"] = self.threads(n) if self.token else "needs GH_TOKEN (GraphQL)"
        return out

    def threads(self, n):
        owner, name = self.repo.split("/", 1)
        q = ("query($o:String!,$n:String!,$p:Int!){repository(owner:$o,name:$n){pullRequest(number:$p){"
             "reviewThreads(first:100){nodes{isResolved path line comments(first:1){nodes{author{login} body}}"
             " replies: comments{totalCount}}}}}}")
        data = self.call(f"{self.api}/graphql", body={"query": q, "variables": {"o": owner, "n": name, "p": n}})
        nodes = (((data.get("data") or {}).get("repository") or {}).get("pullRequest") or {}).get("reviewThreads", {}).get("nodes", [])
        return [{"file": t.get("path"), "line": t.get("line"),
                 "author": (t["comments"]["nodes"][0].get("author") or {}).get("login") if t["comments"]["nodes"] else None,
                 "comment": (t["comments"]["nodes"][0]["body"] if t["comments"]["nodes"] else "")[:400],
                 "replies": max(t["replies"]["totalCount"] - 1, 0)} for t in nodes if not t["isResolved"]]

    def default_branch(self):
        return self.call(self.r())["default_branch"]

    def branch_exists(self, b):
        try:
            self.call(self.r(f"/branches/{urllib.parse.quote(b, safe='')}"))
            return True
        except Fail:
            return False

    def open_pr_for(self, src, tgt):
        owner = self.repo.split("/")[0]
        found = self.call(self.r("/pulls"), {"head": f"{owner}:{src}", "base": tgt, "state": "open"})
        return (found[0]["number"], found[0]["title"], found[0]["html_url"]) if found else None

    def create_pr(self, src, tgt, title, body, draft):
        p = self.call(self.r("/pulls"), body={"head": src, "base": tgt, "title": title, "body": body, "draft": draft})
        return p["number"], p["html_url"]

    def runs(self, a):
        params = {"per_page": a.top, "branch": a.branch, "status": "failure" if a.failed else None}
        rs = self.call(self.r("/actions/runs"), params)["workflow_runs"]
        return [{"id": r["id"], "workflow": r["name"], "branch": r["head_branch"], "event": r["event"],
                 "status": r["status"], "result": r.get("conclusion") or "-", "by": (r.get("actor") or {}).get("login"),
                 "finished": when(r.get("updated_at"))} for r in rs]

    def last_failed(self, a):
        rs = self.call(self.r("/actions/runs"), {"per_page": 1, "status": "failure", "branch": a.branch})["workflow_runs"]
        if not rs:
            raise Fail("no failed run matches")
        return rs[0]["id"]

    def run(self, rid, a):
        r = self.call(self.r(f"/actions/runs/{rid}"))
        out = {"id": rid, "workflow": r["name"], "branch": r["head_branch"], "event": r["event"],
               "status": r["status"], "result": r.get("conclusion") or "-", "url": r["html_url"],
               "commit": (r.get("head_commit") or {}).get("message", "").splitlines()[0][:100] if r.get("head_commit") else ""}
        jobs = self.call(self.r(f"/actions/runs/{rid}/jobs"), {"per_page": 100, "filter": "latest"})["jobs"]
        if not jobs and out["result"] not in ("success", "-"):
            out["note"] = (f"no job ran: the workflow failed to start - usually an invalid workflow file "
                           f"({r.get('path')}) or a run waiting for approval; open the run page for the message")
        failed = sorted([j for j in jobs if j.get("conclusion") in ("failure", "timed_out", "cancelled")],
                        key=lambda j: j.get("completed_at") or "9999")
        out["failed_count"], out["failed"] = len(failed), []
        for j in failed[:a.max_steps]:
            step = next((s["name"] for s in j.get("steps", []) if s.get("conclusion") == "failure"), None)
            item = {"job": j["name"], "step": step, "result": j["conclusion"], "finished": when(j.get("completed_at")),
                    "errors": []}
            try:
                ann = self.call(self.r(f"/check-runs/{j['id']}/annotations"), {"per_page": 50})
                item["errors"] = list(dict.fromkeys(f"{x.get('path', '')}:{x.get('start_line', '')} {x.get('message', '')}".strip(": ")[:400]
                                                    for x in ann if x.get("annotation_level") == "failure"))[:10]
            except Fail:
                pass
            if a.log_lines and self.token:
                try:
                    log = self.call(self.r(f"/actions/jobs/{j['id']}/logs"), text=True)
                    item["log_tail"], item["log_errors"] = tail_and_errors(log, a.log_lines, item["errors"])
                except Fail as e:  # e.g. a token scoped to another repository: keep the rest of the answer
                    item["log_note"] = "job log not available with this token: " + str(e).splitlines()[0][7:120]
            elif a.log_lines:
                item["log_note"] = "GitHub serves job logs only with GH_TOKEN"
            out["failed"].append(item)
        return out

    def issues(self, a):
        params = {"state": "all" if a.state == "all" else a.state, "per_page": a.top, "sort": "updated"}
        if a.mine:
            params["assignee"] = self.me()
        items = [i for i in self.call(self.r("/issues"), params) if "pull_request" not in i]
        return [{"id": i["number"], "title": i["title"], "state": i["state"], "author": i["user"]["login"],
                 "assignees": ", ".join(x["login"] for x in i.get("assignees", [])) or "-",
                 "labels": ", ".join(x["name"] for x in i.get("labels", [])), "updated": when(i.get("updated_at"))}
                for i in items]

    def issue(self, n):
        i = self.call(self.r(f"/issues/{n}"))
        return {"id": n, "title": i["title"], "url": i["html_url"], "state": i["state"], "author": i["user"]["login"],
                "assignees": ", ".join(x["login"] for x in i.get("assignees", [])) or "-",
                "labels": ", ".join(x["name"] for x in i.get("labels", [])), "comments": i.get("comments"),
                "updated": when(i.get("updated_at")), "description": (i.get("body") or "")[:2000]}

    def git_header(self):
        if not self.token:
            raise Fail("git with a token needs GH_TOKEN")
        return "Authorization: Basic " + base64.b64encode(f"x-access-token:{self.token}".encode()).decode()


# ------------------------------------------------------------------ GitLab

class GitLab(Host):
    kind, token_var = "gitlab", "GITLAB_TOKEN"

    def __init__(self, host, repo, timeout):
        super().__init__(host, repo, timeout)
        self.api = f"https://{host}/api/v4"
        self.pid = urllib.parse.quote(repo, safe="")
        self.token = os.environ.get("GITLAB_TOKEN", "")
        self.token_source = "GITLAB_TOKEN" if self.token else None

    def auth(self):
        return {"PRIVATE-TOKEN": self.token} if self.token else {}

    def p(self, path=""):
        return f"{self.api}/projects/{self.pid}{path}"

    def me(self):
        if not self.token:
            raise Fail("this needs GITLAB_TOKEN")
        return self.call(f"{self.api}/user")["username"]

    def whoami(self):
        pr = self.call(self.p())
        return {"host": self.host, "repo": self.repo, "default branch": pr.get("default_branch"),
                "visibility": pr.get("visibility"), "user": self.me() if self.token else None,
                "auth": "token" if self.token else "anonymous"}

    def prs(self, a):
        state = {"open": "opened", "closed": "closed", "merged": "merged", "all": "all"}[a.state]
        params = {"state": state, "per_page": a.top, "order_by": "updated_at"}
        if a.mine:
            params["author_username"] = self.me()
        if a.reviewing:
            params["reviewer_username"] = self.me()
        return [{"id": m["iid"], "title": m["title"], "author": m["author"]["username"],
                 "state": m["state"] + (" (draft)" if m.get("draft") else ""), "updated": when(m.get("updated_at"))}
                for m in self.call(self.p("/merge_requests"), params)]

    def pr(self, n):
        m = self.call(self.p(f"/merge_requests/{n}"))
        out = {"id": n, "title": m["title"], "url": m["web_url"], "author": m["author"]["username"],
               "source": m["source_branch"], "target": m["target_branch"],
               "state": m["state"] + (" (draft)" if m.get("draft") else ""),
               "mergeable": m.get("detailed_merge_status") or m.get("merge_status"),
               "description": (m.get("description") or "")[:1500]}
        try:
            ap = self.call(self.p(f"/merge_requests/{n}/approvals"))
            out["reviews"] = [{"who": x["user"]["username"], "state": "approved"} for x in ap.get("approved_by", [])]
            out["approvals_left"] = ap.get("approvals_left")
        except Fail:
            out["reviews"] = []
        for r in m.get("reviewers", []):
            if r["username"] not in {x["who"] for x in out["reviews"]}:
                out["reviews"].append({"who": r["username"], "state": "review requested"})
        hp = m.get("head_pipeline") or {}
        out["checks"] = [{"name": f"pipeline {hp.get('id')}", "status": hp.get("status"), "run": hp.get("id")}] if hp else []
        try:
            disc = self.call(self.p(f"/merge_requests/{n}/discussions"), {"per_page": 100})
        except Fail:
            out["unresolved_threads"] = "needs GITLAB_TOKEN"
            return out
        out["unresolved_threads"] = [
            {"file": (d["notes"][0].get("position") or {}).get("new_path"),
             "line": (d["notes"][0].get("position") or {}).get("new_line"),
             "author": d["notes"][0]["author"]["username"], "comment": d["notes"][0]["body"][:400],
             "replies": len(d["notes"]) - 1}
            for d in disc if d.get("notes") and d["notes"][0].get("resolvable") and not d["notes"][0].get("resolved")]
        return out

    def default_branch(self):
        return self.call(self.p())["default_branch"]

    def branch_exists(self, b):
        try:
            self.call(self.p(f"/repository/branches/{urllib.parse.quote(b, safe='')}"))
            return True
        except Fail:
            return False

    def open_pr_for(self, src, tgt):
        found = self.call(self.p("/merge_requests"), {"source_branch": src, "target_branch": tgt, "state": "opened"})
        return (found[0]["iid"], found[0]["title"], found[0]["web_url"]) if found else None

    def create_pr(self, src, tgt, title, body, draft):
        m = self.call(self.p("/merge_requests"), body={"source_branch": src, "target_branch": tgt,
                                                       "title": ("Draft: " if draft else "") + title, "description": body})
        return m["iid"], m["web_url"]

    def runs(self, a):
        params = {"per_page": a.top, "ref": a.branch, "status": "failed" if a.failed else None}
        return [{"id": r["id"], "workflow": "pipeline", "branch": r["ref"], "event": r.get("source"), "status": r["status"],
                 "result": r["status"], "by": "-", "finished": when(r.get("updated_at"))}
                for r in self.call(self.p("/pipelines"), params)]

    def last_failed(self, a):
        rs = self.call(self.p("/pipelines"), {"per_page": 1, "status": "failed", "ref": a.branch})
        if not rs:
            raise Fail("no failed pipeline matches")
        return rs[0]["id"]

    def run(self, rid, a):
        r = self.call(self.p(f"/pipelines/{rid}"))
        out = {"id": rid, "workflow": "pipeline", "branch": r["ref"], "event": r.get("source"), "status": r["status"],
               "result": r["status"], "url": r["web_url"], "commit": r.get("sha", "")[:10]}
        jobs = self.call(self.p(f"/pipelines/{rid}/jobs"), {"per_page": 100, "scope[]": "failed"})
        jobs = [j for j in jobs if not j.get("allow_failure")] or jobs
        failed = sorted(jobs, key=lambda j: j.get("finished_at") or "9999")
        out["failed_count"], out["failed"] = len(failed), []
        for j in failed[:a.max_steps]:
            item = {"job": j["name"], "step": j.get("stage"), "result": j.get("failure_reason") or j["status"],
                    "finished": when(j.get("finished_at")), "errors": []}
            if a.log_lines:
                try:
                    log = self.call(self.p(f"/jobs/{j['id']}/trace"), text=True)
                    item["log_tail"], item["log_errors"] = tail_and_errors(log, a.log_lines)
                except Fail as e:
                    item["log_note"] = "job log needs GITLAB_TOKEN" if "401" in str(e) else str(e).splitlines()[0]
            out["failed"].append(item)
        return out

    def issues(self, a):
        state = {"open": "opened", "closed": "closed", "all": None}[a.state]
        params = {"state": state, "per_page": a.top, "order_by": "updated_at"}
        if a.mine:
            params["assignee_username"] = self.me()
        return [{"id": i["iid"], "title": i["title"], "state": i["state"], "author": i["author"]["username"],
                 "assignees": ", ".join(x["username"] for x in i.get("assignees", [])) or "-",
                 "labels": ", ".join(i.get("labels", [])), "updated": when(i.get("updated_at"))}
                for i in self.call(self.p("/issues"), params)]

    def issue(self, n):
        i = self.call(self.p(f"/issues/{n}"))
        return {"id": n, "title": i["title"], "url": i["web_url"], "state": i["state"], "author": i["author"]["username"],
                "assignees": ", ".join(x["username"] for x in i.get("assignees", [])) or "-",
                "labels": ", ".join(i.get("labels", [])), "comments": i.get("user_notes_count"),
                "updated": when(i.get("updated_at")), "description": (i.get("description") or "")[:2000]}

    def git_header(self):
        if not self.token:
            raise Fail("git with a token needs GITLAB_TOKEN")
        return "Authorization: Basic " + base64.b64encode(f"oauth2:{self.token}".encode()).decode()


# ------------------------------------------------------------------ resolve repository

def origin(remote: str) -> str | None:
    try:
        return subprocess.run(["git", "remote", "get-url", remote], capture_output=True, text=True,
                              timeout=10).stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        return None


def gitlab_host() -> str:
    return urllib.parse.urlparse(os.environ.get("GITLAB_HOST") or "https://gitlab.com").netloc


def client(a, url_info: dict | None = None) -> Host:
    """Where the repository lives: a URL argument > --repo (with --host) > the git remote of the current folder."""
    if url_info:
        host, repo = url_info["host"], url_info["repo"]
    elif a.repo and ("://" in a.repo or a.repo.startswith("git@")):
        host, repo = parse_remote(a.repo)
    elif a.repo:
        repo = a.repo.strip("/")
        if a.host == "gitlab":
            host = gitlab_host()
        elif a.host == "github":
            host = "github.com"
        else:
            remote = origin(a.remote)
            host = parse_remote(remote)[0] if remote else "github.com"
    else:
        remote = origin(a.remote)
        if not remote:
            raise Fail("no repository: run inside a git checkout, pass --repo owner/name (and --host github|gitlab), "
                       "or give a URL")
        host, repo = parse_remote(remote)
    is_gitlab = a.host == "gitlab" or (a.host != "github" and host != "github.com"
                                       and (host == gitlab_host() or "gitlab" in host))
    return GitLab(host, repo, a.timeout) if is_gitlab else GitHub(host, repo, a.timeout)


def ref_target(a, kind: str) -> tuple[Host, int]:
    ref = str(a.ref)
    if ref.isdigit():
        return client(a), int(ref)
    info = url_target(ref)
    if info.get("kind") != kind:
        raise Fail(f"that URL is not a {kind} link")
    return client(a, info), info["id"]


# ------------------------------------------------------------------ output

def table(rows: list[dict], cols: list[str]) -> str:
    if not rows:
        return "(none)"
    widths = {c: min(max(len(c), *(len(str(r.get(c, ""))) for r in rows)), 70) for c in cols}
    line = lambda r: "  ".join(str(r.get(c, ""))[:widths[c]].ljust(widths[c]) for c in cols).rstrip()
    return "\n".join([line({c: c for c in cols}), line({c: "-" * widths[c] for c in cols})] + [line(r) for r in rows])


def show_pr(o) -> str:
    lines = [f"#{o['id']}  {o['title']}", f"  {o['url']}",
             f"  {o['author']}: {o['source']} -> {o['target']}   {o['state']}, mergeable: {o['mergeable']}"]
    if o.get("approvals_left") is not None:
        lines.append(f"  approvals still needed: {o['approvals_left']}")
    lines += ["", "Reviews:" + ("" if o["reviews"] else " none")] + [f"  {r['who']}: {r['state']}" for r in o["reviews"]]
    # Only what needs attention is listed; passing and skipped checks are counted (full list: --json).
    quiet = {"success", "skipped", "neutral", "completed"}
    counts: dict[str, int] = {}
    for c in o["checks"]:
        counts[c["status"] or "-"] = counts.get(c["status"] or "-", 0) + 1
    lines += ["", "Checks: " + (", ".join(f"{v} {k}" for k, v in sorted(counts.items())) if counts else "none")]
    lines += [f"  {(c['status'] or '-'):<12} {c['name']}" + (f"  (run {c['run']})" if c.get("run") else "")
              for c in o["checks"] if (c["status"] or "-") not in quiet]
    th = o["unresolved_threads"]
    if isinstance(th, str):
        lines += ["", f"Unresolved threads: {th}"]
    else:
        lines += ["", f"Unresolved threads: {len(th)}"]
        for t in th:
            where = f"{t['file']}:{t['line']}" if t["file"] else "(general)"
            first = t["comment"].strip().splitlines()[0] if t["comment"].strip() else ""
            lines.append(f"  - {where}  {t['author']}: {first[:150]}" + (f"  [+{t['replies']} replies]" if t["replies"] else ""))
    if o["description"]:
        lines += ["", "Description:", "  " + o["description"].strip().replace("\n", "\n  ")]
    return "\n".join(lines)


def show_run(o) -> str:
    lines = [f"Run {o['id']}  {o['workflow']}  ({o['branch']}, {o['event']})", f"  {o['url']}",
             f"  {o['status']} / {o['result']}" + (f"  commit: {o['commit']}" if o.get("commit") else "")]
    if o["failed_count"] > len(o["failed"]):
        lines.append(f"  {o['failed_count']} failed jobs; showing the first {len(o['failed'])} to fail (--max-steps)")
    if o.get("note"):
        lines.append(f"\n{o['note']}")
    elif not o["failed"]:
        lines.append("\nNo failed jobs.")
    for j in o["failed"]:
        lines += ["", f"FAILED job: {j['job']}" + (f"  step: {j['step']}" if j.get("step") else "")
                  + f"  ({j['result']}, {j['finished']})"]
        lines += [f"  error: {e}" for e in j["errors"]]
        if j.get("log_note"):
            lines.append(f"  ({j['log_note']})")
        if j.get("log_errors"):
            lines += [f"  --- error-looking lines from the whole log ({len(j['log_errors'])}) ---"] + [
                f"  ! {l[:300]}" for l in j["log_errors"]]
        if j.get("log_tail"):
            lines += [f"  --- last {len(j['log_tail'])} log lines ---"] + [f"  | {l}" for l in j["log_tail"]]
    return "\n".join(lines)


def show_issue(o) -> str:
    lines = [f"#{o['id']}  {o['title']}", f"  {o['url']}",
             f"  {o['state']}, by {o['author']}, assigned: {o['assignees']}, {o['comments']} comments, updated {o['updated']}"]
    if o["labels"]:
        lines.append(f"  labels: {o['labels']}")
    if o["description"]:
        lines += ["", "  " + o["description"].strip().replace("\n", "\n  ")]
    return "\n".join(lines)


# ------------------------------------------------------------------ commands

def cmd_whoami(a):
    h = client(a)
    return h.whoami(), lambda o: "\n".join(f"{k:<16} {v}" for k, v in o.items() if v is not None)


def cmd_prs(a):
    return client(a).prs(a), lambda o: table(o, ["id", "title", "author", "state", "updated"])


def cmd_pr(a):
    h, n = ref_target(a, "pr")
    return h.pr(n), show_pr


def cmd_pr_create(a):
    h = client(a)
    tgt = a.target or h.default_branch()
    missing = [b for b in (a.source, tgt) if not h.branch_exists(b)]
    if missing:
        raise Fail(f"branch not found in {h.repo}: {', '.join(missing)} (push it first)")
    body = Path(a.body_file).read_text(encoding="utf-8") if a.body_file else (a.body or "")
    dup = h.open_pr_for(a.source, tgt)
    warning = f"an open request from {a.source} into {tgt} already exists: #{dup[0]} \"{dup[1]}\" - {dup[2]}" if dup else None
    if a.apply:
        if dup:
            raise Fail(warning)
        n, url = h.create_pr(a.source, tgt, a.title, body, a.draft)
        return {"created": n, "url": url}, lambda o: f"created #{o['created']}: {o['url']}"
    out = {"would_create": {"repo": h.repo, "host": h.host, "source": a.source, "target": tgt, "title": a.title,
                            "draft": a.draft, "body": f"<{len(body)} chars>"},
           "warning": warning, "note": "nothing was sent; repeat with --apply to create it"}
    return {k: v for k, v in out.items() if v}, lambda o: json.dumps(o, indent=2, ensure_ascii=False)


def cmd_runs(a):
    return client(a).runs(a), lambda o: table(o, ["id", "workflow", "branch", "event", "status", "result", "by", "finished"])


def cmd_run(a):
    if a.ref == "last-failed":
        h = client(a)
        rid = h.last_failed(a)
    else:
        h, rid = ref_target(a, "run")
    return h.run(rid, a), show_run


def cmd_issues(a):
    return client(a).issues(a), lambda o: table(o, ["id", "title", "state", "assignees", "labels", "updated"])


def cmd_issue(a):
    h, n = ref_target(a, "issue")
    return h.issue(n), show_issue


def cmd_git(a):
    h = client(a)
    args = [x for x in a.git_args if x != "--"]
    if not args:
        raise Fail("give git arguments, e.g.: githost.py git push -u origin my-branch")
    if args[0] == "push" and any(x in ("-f", "--force", "--force-with-lease") or x.startswith("--force") for x in args):
        raise Fail("force-push is refused here; run plain git yourself if you really mean it")
    key = f"http.https://{h.host}/.extraheader"
    # An empty value first resets headers configured elsewhere (actions/checkout stores its own), so exactly one
    # Authorization header is sent.
    cmd = ["git", "-c", "credential.helper=", "-c", f"{key}=", "-c", f"{key}={h.git_header()}", *args]
    print("$ git " + " ".join(args), file=sys.stderr)
    sys.exit(subprocess.run(cmd).returncode)  # the token travels as a header: never in the URL, .git/config or output


# ------------------------------------------------------------------ main

def main() -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="machine-readable output")
    common.add_argument("--repo", help="owner/name or group/project (default: from the git remote)")
    common.add_argument("--host", choices=["github", "gitlab"], help="force the host type")
    common.add_argument("--remote", default="origin", help="git remote to read (default origin)")
    common.add_argument("--timeout", type=float, default=30)

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, fn, help_):
        s = sub.add_parser(name, parents=[common], help=help_)
        s.set_defaults(fn=fn)
        return s

    add("whoami", cmd_whoami, "host, repository, user")
    s = add("prs", cmd_prs, "pull / merge requests")
    g = s.add_mutually_exclusive_group(); g.add_argument("--mine", action="store_true"); g.add_argument("--reviewing", action="store_true")
    s.add_argument("--state", default="open", choices=["open", "closed", "merged", "all"]); s.add_argument("--top", type=int, default=20)
    s = add("pr", cmd_pr, "one PR / MR"); s.add_argument("ref", help="number or URL")
    s = add("pr-create", cmd_pr_create, "open a PR / MR (dry run unless --apply)")
    s.add_argument("--source", required=True); s.add_argument("--target"); s.add_argument("--title", required=True)
    g = s.add_mutually_exclusive_group(required=True); g.add_argument("--body-file"); g.add_argument("--body")
    s.add_argument("--draft", action="store_true"); s.add_argument("--apply", action="store_true")
    s = add("runs", cmd_runs, "CI runs / pipelines")
    s.add_argument("--failed", action="store_true"); s.add_argument("--branch"); s.add_argument("--top", type=int, default=10)
    s = add("run", cmd_run, "one CI run: why it failed")
    s.add_argument("ref", help="run / pipeline id, URL, or last-failed"); s.add_argument("--branch")
    s.add_argument("--log-lines", type=int, default=30); s.add_argument("--max-steps", type=int, default=3)
    s = add("issues", cmd_issues, "issues")
    s.add_argument("--mine", action="store_true"); s.add_argument("--state", default="open", choices=["open", "closed", "all"])
    s.add_argument("--top", type=int, default=20)
    s = add("issue", cmd_issue, "one issue"); s.add_argument("ref", help="number or URL")
    s = add("git", cmd_git, "git with the token as an HTTP header"); s.add_argument("git_args", nargs=argparse.REMAINDER)

    a = p.parse_args()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    load_dotenv()
    data, show = a.fn(a)
    print(json.dumps(data, indent=2, ensure_ascii=False) if a.json else show(data))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
