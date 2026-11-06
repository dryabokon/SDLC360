"""Local web app: pick a project (GitHub URL or local git folder), scan it, browse runs. Stdlib only, binds to localhost."""

from __future__ import annotations

import json
import logging
import os
import string
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .render import render_app
from .repo import check_target
from .runner import DEFAULT_CACHE, DEFAULT_RUNS, RUN_ID_RE, list_projects, run_scan

log = logging.getLogger("sdlc360")
JOBS: dict[str, dict] = {}
SCAN_LOCK = threading.Lock()  # one scan at a time: shared clone cache + CPU bound


def _start_job(target: str, history: int, runs_dir: Path, cache_dir: Path) -> str:
    jid = uuid.uuid4().hex[:12]
    job: dict = {"id": jid, "target": target, "history": history, "status": "queued", "messages": [], "run_id": None, "error": None}
    JOBS[jid] = job

    def work() -> None:
        with SCAN_LOCK:
            job["status"] = "running"
            try:
                rd = run_scan(
                    target, history_points=history, refresh=True, runs_dir=runs_dir, cache_dir=cache_dir, progress=lambda m: job["messages"].append(m)
                )
                job["run_id"], job["status"] = rd.name, "done"
            except Exception as e:
                log.exception("scan failed")
                job["error"], job["status"] = str(e), "error"

    threading.Thread(target=work, daemon=True).start()
    return jid


HIDDEN_DIRS = {"node_modules", "__pycache__", ".venv", "venv", "$recycle.bin", "system volume information", ".git"}


def browse(path: str | None, runs_dir: Path) -> dict:
    """Read-only folder listing for the local-folder picker: names only, git repos flagged."""

    def entry(p: Path) -> dict:
        return {"name": p.name or str(p), "path": str(p), "git": (p / ".git").exists()}

    if not path:
        roots = [entry(Path.home())]
        if os.name == "nt":
            roots += [{"name": f"{d}:", "path": f"{d}:\\", "git": False} for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
        else:
            roots.append({"name": "/", "path": "/", "git": False})
        recent = []
        for proj in list_projects(runs_dir):
            src = Path(proj["source"])
            if not proj["source"].startswith("github.com/") and src.parent.is_dir() and str(src.parent) not in recent:
                recent.append(str(src.parent))
        return {"path": None, "parent": None, "git": False, "dirs": roots, "recent": [entry(Path(r)) for r in recent[:6]]}
    p = Path(path).expanduser()
    if not p.is_dir():
        raise ValueError(f"Not a folder: {path}")
    p = p.resolve()
    dirs = []
    try:
        for child in sorted(p.iterdir(), key=lambda c: c.name.lower()):
            try:
                if child.is_dir() and not child.name.startswith(".") and child.name.lower() not in HIDDEN_DIRS:
                    dirs.append(entry(child))
            except OSError:
                continue
            if len(dirs) >= 500:
                break
    except PermissionError as e:
        raise ValueError(f"No permission to read {p}") from e
    parent = str(p.parent) if p.parent != p else ""
    return {"path": str(p), "parent": parent, "git": (p / ".git").exists(), "dirs": dirs}


LOCAL_HOSTS = {"127.0.0.1", "localhost", "[::1]"}


def local_request(host: str | None, origin: str | None) -> bool:
    """Guard against DNS rebinding (foreign Host) and cross-site requests (foreign Origin) to this local-only server."""
    hostname = (host or "").rsplit(":", 1)[0].lower() if not (host or "").startswith("[") else (host or "").split("]")[0] + "]"
    if hostname not in LOCAL_HOSTS:
        return False
    if origin:
        o = urlparse(origin)
        return (o.hostname or "") in {"127.0.0.1", "localhost", "::1"}
    return True


def make_handler(runs_dir: Path, cache_dir: Path):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # route to logging, quieter
            log.debug("%s - %s", self.address_string(), fmt % args)

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code: int = 200) -> None:
            self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def _guard(self) -> bool:
            if local_request(self.headers.get("Host"), self.headers.get("Origin")):
                return True
            self._json({"error": "forbidden: local requests only"}, 403)
            return False

        def do_GET(self) -> None:
            if not self._guard():
                return
            path = urlparse(self.path).path.rstrip("/") or "/"
            if path == "/":
                return self._send(200, render_app().encode("utf-8"), "text/html; charset=utf-8")
            if path == "/api/projects":
                return self._json(list_projects(runs_dir))
            if path == "/api/fs":
                q = parse_qs(urlparse(self.path).query).get("path", [""])[0]
                try:
                    return self._json(browse(q or None, runs_dir))
                except ValueError as e:
                    return self._json({"error": str(e)}, 400)
            parts = path.split("/")
            if len(parts) == 4 and parts[1:3] == ["api", "runs"] and RUN_ID_RE.match(parts[3]):
                f = runs_dir / parts[3] / "report.json"
                if f.exists():
                    return self._send(200, f.read_bytes(), "application/json; charset=utf-8")
                return self._json({"error": "run not found"}, 404)
            if len(parts) == 4 and parts[1:3] == ["api", "jobs"] and parts[3] in JOBS:
                return self._json(JOBS[parts[3]])
            self._json({"error": "not found"}, 404)

        def do_POST(self) -> None:
            if not self._guard():
                return
            if urlparse(self.path).path == "/api/shutdown":  # used by stop.sh
                self._json({"status": "stopping"})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            if urlparse(self.path).path != "/api/scan":
                return self._json({"error": "not found"}, 404)
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0) or 0)) or b"{}")
                target = str(body.get("target", "")).strip()
                history = max(0, min(24, int(body.get("history", 8))))
            except (ValueError, TypeError):
                return self._json({"error": "bad request"}, 400)
            try:
                info = check_target(target)
            except ValueError as e:
                return self._json({"error": str(e)}, 400)
            if any(j["status"] in ("queued", "running") for j in JOBS.values()):
                return self._json({"error": "Another scan is still running - wait for it to finish."}, 409)
            self._json({"job": _start_job(target, history, runs_dir, cache_dir), "kind": info["kind"], "display": info["display"]}, 202)

    return Handler


def serve(port: int = 8360, runs_dir: Path = DEFAULT_RUNS, cache_dir: Path = DEFAULT_CACHE, open_browser: bool = False) -> None:
    runs_dir.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(runs_dir, cache_dir))
    url = f"http://127.0.0.1:{port}/"
    log.info("SDLC 360 at %s  (runs: %s)", url, runs_dir)
    if open_browser:
        import webbrowser

        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
