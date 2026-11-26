"""Repository access: resolve a target (local path / GitHub URL / owner/repo), index files, query git."""

from __future__ import annotations

import fnmatch
import os
import re
import subprocess
from datetime import UTC, datetime
from functools import cached_property
from pathlib import Path, PurePosixPath

from . import hosting

SKIP_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".tox",
    ".idea",
    ".next",
    "target",
    ".gradle",
}
BINARY_EXT = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".jar",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".mp4",
    ".mp3",
    ".wav",
    ".bin",
    ".pt",
    ".pth",
    ".onnx",
    ".pkl",
    ".parquet",
    ".npy",
    ".npz",
    ".h5",
    ".webp",
    ".svgz",
    ".class",
    ".pyc",
    ".whl",
    ".7z",
    ".db",
    ".sqlite",
}
SOURCE_EXT = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".scala",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
    ".m",
    ".dart",
    ".ex",
    ".exs",
    ".clj",
    ".lua",
    ".r",
    ".jl",
    ".vue",
    ".svelte",
    ".fs",
    ".sh",
    ".ps1",
}

GITHUB_RE = re.compile(r"^(?:https?://github\.com/|git@github\.com:)?([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")


def hosted_match(target: str) -> tuple[str, str] | None:
    """(host, group/.../repo) for https://<host>/<group>/.../<repo> on one of hosting.git_hosts(), else None."""
    m = re.match(r"^(?:https?://)?([\w.-]+)/((?:[\w.-]+/)+[\w.-]+?)(?:\.git)?/?$", target)
    if m and m.group(1).lower() in hosting.git_hosts() and ".." not in m.group(2):
        return m.group(1).lower(), m.group(2)
    return None


def run_git(cwd: Path, *args: str, check: bool = True, env: dict[str, str] | None = None) -> str:
    res = subprocess.run(
        ["git", "-c", "core.longpaths=true", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, **env} if env else None,
    )
    if check and res.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {res.stderr.strip()}")
    return res.stdout


def check_target(target: str) -> dict:
    """Validate a scan target without side effects. Returns {kind, display} or raises ValueError with a user-facing message."""
    target = (target or "").strip().strip('"')
    if not target:
        raise ValueError("Enter a GitHub URL, owner/repo, or the path of a local git folder.")
    hosted = hosted_match(target)
    if hosted:
        return {"kind": "hosted", "display": hosted[1]}
    if hosting.cloud():  # one server for many people: its own disk is never a target
        m = GITHUB_RE.match(target)
        if m and not re.match(r"^[A-Za-z]:", target):
            return {"kind": "github", "display": f"{m.group(1)}/{m.group(2)}"}
        raise ValueError(f"Use a repository URL: https://github.com/owner/repo, owner/repo or https://{hosting.git_hosts()[0]}/group/repo.")
    p = Path(target).expanduser()
    if p.exists():
        if not p.is_dir():
            raise ValueError(f"{target} is a file, not a folder.")
        top = run_git(p, "rev-parse", "--show-toplevel", check=False).strip()
        if not top:
            raise ValueError(f"{target} is not a git repository (history is needed for the assessment).")
        return {"kind": "local", "display": Path(top).name}
    m = GITHUB_RE.match(target)
    if m and not re.match(r"^[A-Za-z]:", target):
        return {"kind": "github", "display": f"{m.group(1)}/{m.group(2)}"}
    if re.match(r"^([A-Za-z]:[\\/]|/|~|\.)", target):
        raise ValueError(f"Folder not found: {target}")
    raise ValueError("Not recognised. Use https://github.com/owner/repo, owner/repo, or an existing local git folder.")


def refresh_clone(dest: Path, ref: str | None = None, env: dict | None = None) -> None:
    """Move a cached clone to `ref`, or to the newest commit of the remote's default branch.

    `git fetch origin` alone writes every branch to FETCH_HEAD; on a detached clone none is marked for merge and
    `checkout FETCH_HEAD` took the first branch by name (an old release branch of rich from 2022).
    """
    if ref:
        run_git(dest, "fetch", "--quiet", "origin", env=env)
        run_git(dest, "checkout", "--quiet", ref)
    else:
        run_git(dest, "fetch", "--quiet", "origin", "HEAD", env=env)  # the default branch, whatever it is called
        run_git(dest, "checkout", "--quiet", "--detach", "FETCH_HEAD")


WORKING_COPY = "working-copy"  # --ref for a local folder: the files as they are now, uncommitted changes included
STALE_FETCH_DAYS = 7  # a local folder's remote branches are as old as its last fetch; older than this is said in the report


def _commit_time(root: Path, ref: str) -> int | None:
    sha = run_git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", check=False).strip()
    if not sha:
        return None
    ts = run_git(root, "log", "-1", "--format=%ct", sha, check=False).strip()
    return int(ts) if ts.isdigit() else None


def default_ref(root: Path) -> tuple[str | None, str]:
    """The branch a local folder's project integrates into, as the folder last fetched it, and why that one: the most
    recent of origin/HEAD, origin/main, origin/master and origin/develop. origin/HEAD alone misleads: it is set when the
    folder is cloned and never follows the server (a gitflow project on Azure DevOps: main from March, all work on
    develop; a folder cloned from a feature branch). Without remote branches, the same among the local ones. Read only."""
    head = run_git(root, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD", check=False).strip()
    for group, where in (((head, "origin/main", "origin/master", "origin/develop"), "remote"), (("main", "master", "develop"), "local")):
        found = {b: t for b in dict.fromkeys(x for x in group if x) if (t := _commit_time(root, b)) is not None}
        if found:
            best = max(found, key=lambda b: found[b])
            if len(found) == 1:
                return best, "origin/HEAD" if best == head else f"the only {where} main branch"
            return best, f"the most recently updated {where} main branch of {', '.join(found)}"
    return None, "no main branch: the working copy"


def branches(root: Path, limit: int = 200) -> list[dict]:
    """The branches of a local folder, newest first, remote ones as last fetched: what the app offers to assess."""
    fmt = "--format=%(refname:short)%1f%(committerdate:iso-strict)"
    out = run_git(root, "for-each-ref", "--sort=-committerdate", fmt, "refs/remotes", "refs/heads", check=False)
    rows = [line.split("\x1f") for line in out.splitlines() if "\x1f" in line]
    return [{"name": n, "date": d} for n, d in rows if not n.endswith("/HEAD") and n != "origin"][:limit]


def fetched_at(root: Path, ref: str | None = None) -> datetime | None:
    """When the local folder last brought `ref` from its remote: the newest of FETCH_HEAD, the ref's own file and
    packed-refs (a fresh clone has no FETCH_HEAD). None when there is none of them."""
    git_dir = run_git(root, "rev-parse", "--git-dir", check=False).strip()
    if not git_dir:
        return None
    base = root / git_dir
    files = [base / "FETCH_HEAD", base / "packed-refs"] + ([base / "refs" / "remotes" / ref] if ref else [])
    times = [f.stat().st_mtime for f in files if f.is_file()]
    return datetime.fromtimestamp(max(times), UTC) if times else None


def checkout_ref(root: Path, ref: str, dest: Path) -> str:
    """A throw-away copy of a local folder at `ref`, made with `clone --shared` so nothing is written into the folder's own
    .git. Returns the commit. ValueError when the folder has no such branch, tag or commit."""
    sha = run_git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", check=False).strip()
    if not sha:
        raise ValueError(f"{root.name} has no branch, tag or commit {ref!r}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    run_git(dest.parent, "clone", "--quiet", "--shared", "--no-checkout", str(root), dest.name)
    run_git(dest, "checkout", "--quiet", "--force", "--detach", sha)
    return sha


def resolve_target(target: str, cache_dir: Path, ref: str | None = None, refresh: bool = False) -> tuple[Path, str]:
    """Return (local_path, display_source). Clones GitHub repos into cache_dir (blobless, full history)."""
    target = target.strip().strip('"')
    hosted = hosted_match(target)
    if hosted:
        host, path = hosted
        env = hosting.git_auth_env(host)
        dest = cache_dir / f"{host}__{path.replace('/', '__')}"
        cache_dir.mkdir(parents=True, exist_ok=True)
        if dest.exists() and (dest / ".git").exists():
            if refresh or ref:
                refresh_clone(dest, ref, env)
        else:
            run_git(cache_dir, "clone", "--quiet", "--filter=blob:none", f"https://{host}/{path}.git", dest.name, env=env)
            if ref:
                run_git(dest, "checkout", "--quiet", ref)
        return dest, f"{host}/{path}"
    if check_target(target)["kind"] == "local":
        top = Path(run_git(Path(target).expanduser(), "rev-parse", "--show-toplevel").strip()).resolve()
        return top, str(top)
    m = GITHUB_RE.match(target)
    if not m:
        raise ValueError(f"Not a local git folder or GitHub repository: {target}")
    owner, name = m.group(1), m.group(2)
    url = f"https://github.com/{owner}/{name}.git"
    dest = cache_dir / f"{owner}__{name}"
    cache_dir.mkdir(parents=True, exist_ok=True)
    if dest.exists() and (dest / ".git").exists():
        if refresh or ref:
            refresh_clone(dest, ref)
    else:
        run_git(cache_dir, "clone", "--quiet", "--filter=blob:none", url, dest.name)
        if ref:
            run_git(dest, "checkout", "--quiet", ref)
    return dest, f"github.com/{owner}/{name}"


class Repo:
    def __init__(self, root: Path, source: str | None = None):
        self.root = root
        self.source = source or str(root)
        self.is_git = (root / ".git").exists()
        self.params: dict[str, dict] = {}  # thresholds in force (profiles.PARAMS), set by scanner.scan()
        self.forge: str | None = None  # github / gitlab / azure when the run says so (--forge); else read from the remotes

    def param(self, check_id: str, key: str) -> float:
        from .profiles import PARAMS  # late import: profiles -> checklist only, keeps repo.py free of cycles

        if key in self.params.get(check_id, {}):
            return float(self.params[check_id][key])
        return float(next(p.default for p in PARAMS[check_id] if p.key == key))

    # ---------- file index ----------
    @cached_property
    def tracked(self) -> list[str]:
        if self.is_git:
            out = run_git(self.root, "ls-files", "-z", check=False)
            files = [f for f in out.split("\0") if f]
            if files:
                return sorted(files)
        return self.on_disk

    @cached_property
    def on_disk(self) -> list[str]:
        """All files on disk (incl. untracked / git-ignored ones), minus heavy vendor dirs."""
        files = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            rel = Path(dirpath).relative_to(self.root)
            for fn in filenames:
                files.append(PurePosixPath(*rel.parts, fn).as_posix())
            if len(files) > 200_000:
                break
        return sorted(files)

    @property
    def files(self) -> list[str]:
        return self.tracked

    @cached_property
    def _lower(self) -> list[tuple[str, str]]:
        return [(f, f.lower()) for f in self.files]

    @cached_property
    def dirs(self) -> set[str]:
        out = set()
        for f in self.files:
            parts = f.split("/")[:-1]
            for i in range(1, len(parts) + 1):
                out.add("/".join(parts[:i]).lower())
        return out

    def find(self, *patterns: str, files: list[str] | None = None) -> list[str]:
        """Case-insensitive fnmatch on full posix path. '*' crosses '/'. A pattern without '/'
        matches the basename anywhere in the tree."""
        pool = [(f, f.lower()) for f in files] if files is not None else self._lower
        pats = [p.lower() for p in patterns]
        hits = []
        for orig, low in pool:
            base = low.rsplit("/", 1)[-1]
            for p in pats:
                if ("/" in p and fnmatch.fnmatchcase(low, p)) or ("/" not in p and fnmatch.fnmatchcase(base, p)):
                    hits.append(orig)
                    break
        return hits

    def find_dirs(self, *patterns: str) -> list[str]:
        pats = [p.lower() for p in patterns]
        return sorted(d for d in self.dirs if any(fnmatch.fnmatchcase(d, p) or fnmatch.fnmatchcase(d.rsplit("/", 1)[-1], p) for p in pats))

    def exists(self, rel: str) -> bool:
        return (self.root / rel).exists()

    @cached_property
    def symlinks(self) -> set[str]:
        """Tracked symlinks (mode 120000). On Windows without core.symlinks they are checked out as one-line text files."""
        if not self.is_git:
            return set()
        out = run_git(self.root, "ls-files", "-s", check=False)
        return {line.split("\t", 1)[1] for line in out.splitlines() if line.startswith("120000 ") and "\t" in line}

    def resolve_link(self, rel: str) -> str:
        """Repo-relative path a tracked symlink points to (or `rel` itself)."""
        if rel not in self.symlinks:
            return rel
        p = self.root / rel
        try:
            target = p.resolve() if p.is_symlink() else (p.parent / p.read_text(encoding="utf-8").strip()).resolve()
            if target.is_file() and self.root.resolve() in target.parents:
                return target.relative_to(self.root.resolve()).as_posix()
        except (OSError, ValueError):
            pass
        return rel

    def read(self, rel: str, limit: int = 400_000) -> str:
        rel = self.resolve_link(rel)
        try:
            with open(self.root / rel, "rb") as fh:
                data = fh.read(limit)
            if b"\0" in data[:4096]:
                return ""
            return data.decode("utf-8", errors="replace")
        except OSError:
            return ""

    def text_files(self, max_size: int = 1_000_000) -> list[str]:
        out = []
        for f in self.files:
            if PurePosixPath(f).suffix.lower() in BINARY_EXT:
                continue
            try:
                if (self.root / f).stat().st_size <= max_size:
                    out.append(f)
            except OSError:
                pass
        return out

    def grep(
        self, pattern: str | re.Pattern, files: list[str] | None = None, max_hits: int = 50, flags: int = re.IGNORECASE
    ) -> list[tuple[str, int, str]]:
        rx = re.compile(pattern, flags) if isinstance(pattern, str) else pattern
        hits = []
        for f in files if files is not None else self.text_files():
            text = self.read(f)
            if not text or not rx.search(text):
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    hits.append((f, i, line.strip()[:200]))
                    if len(hits) >= max_hits:
                        return hits
        return hits

    def any_match(self, pattern: str, files: list[str], flags: int = re.IGNORECASE) -> list[str]:
        rx = re.compile(pattern, flags)
        return [f for f in files if rx.search(self.read(f))]

    # ---------- code classification ----------
    @cached_property
    def source_files(self) -> list[str]:
        return [
            f
            for f in self.files
            if PurePosixPath(f).suffix.lower() in SOURCE_EXT
            and not self.is_test(f)
            and not f.lower().startswith(("vendor/", "third_party/", "docs/", "examples/", ".github/"))
        ]

    @cached_property
    def test_files(self) -> list[str]:
        return [f for f in self.files if self.is_test(f) and PurePosixPath(f).suffix.lower() in SOURCE_EXT]

    @staticmethod
    def is_test(f: str) -> bool:
        low = f.lower()
        name = low.rsplit("/", 1)[-1]
        return bool(
            re.search(r"(^|/)(tests?|__tests__|spec|specs|e2e|integration_tests?)/", low)
            or re.match(r"(test_.*|.*_test\.\w+|.*\.(test|spec)\.\w+|.*tests?\.(cs|java|kt))$", name)
        )

    @cached_property
    def languages(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in self.source_files:
            ext = PurePosixPath(f).suffix.lower()
            counts[ext] = counts.get(ext, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: -kv[1]))

    @cached_property
    def workflows(self) -> list[str]:
        return self.find(".github/workflows/*.yml", ".github/workflows/*.yaml")

    @cached_property
    def workflow_text(self) -> str:
        return "\n".join(self.read(f) for f in self.workflows)

    @cached_property
    def other_ci(self) -> list[str]:
        """CI configuration besides GitHub Actions. An Azure pipeline may have any name (azure-pipelines-smoke.yml)."""
        return self.find(
            ".gitlab-ci.yml",
            "Jenkinsfile",
            "azure-pipelines*.yml",
            "azure-pipelines*.yaml",
            ".azure-pipelines/*.yml",
            ".circleci/config.yml",
            "bitbucket-pipelines.yml",
            ".travis.yml",
        )

    @cached_property
    def ci_text(self) -> str:
        """Workflow YAML plus the task runners / scripts it delegates to (scripts/test, make test, nox, tox, npm run …),
        so `run: scripts/test` counts as running pytest."""
        azure = [f for f in self.other_ci if "azure-pipelines" in f.lower()]  # read like GitHub's and GitLab's
        wf = "\n".join(x for x in (self.workflow_text, self.read(".gitlab-ci.yml"), *(self.read(f) for f in azure)) if x)
        if not wf:
            return ""
        extra = []
        for m in re.finditer(r"(?:\./)?((?:scripts|bin|tools|ci|\.github/scripts)/[\w./-]+)", wf):
            if m.group(1) in self.files:
                extra.append(m.group(1))
        runners = {
            r"\bmake\b": ["Makefile"],
            r"\bjust\b": ["justfile", "Justfile"],
            r"\bnox\b": ["noxfile.py"],
            r"\btox\b": ["tox.ini"],
            r"\b(npm|pnpm|yarn|bun) (run )?\w": ["package.json"],
            r"\b(hatch|uv run|poetry run|pdm run|task)\b": ["pyproject.toml", "Taskfile.yml"],
        }
        for pat, names in runners.items():
            if re.search(pat, wf):
                extra += [n for n in names if n in self.files]
        return wf + "\n" + "\n".join(self.read(f, 200_000) for f in dict.fromkeys(extra))

    # ---------- git metadata ----------
    @cached_property
    def head(self) -> dict:
        if not self.is_git:
            return {}
        out = run_git(self.root, "log", "-1", "--format=%H%x1f%ct%x1f%s", check=False).strip()
        if not out:
            return {}
        sha, ts, subj = out.split("\x1f", 2)
        branch = run_git(self.root, "rev-parse", "--abbrev-ref", "HEAD", check=False).strip()
        return {"sha": sha, "date": datetime.fromtimestamp(int(ts), UTC).isoformat(), "subject": subj, "branch": branch}

    @cached_property
    def commit_count(self) -> int:
        if not self.is_git:
            return 0
        out = run_git(self.root, "rev-list", "--count", "HEAD", check=False).strip()
        return int(out) if out.isdigit() else 0

    def last_modified(self, paths: list[str]) -> datetime | None:
        """Latest commit time touching any of `paths` (falls back to file mtime outside git)."""
        if not paths:
            return None
        if self.is_git:
            # chunk to keep command line short on Windows
            best = None
            for i in range(0, len(paths), 200):
                out = run_git(self.root, "log", "-1", "--format=%ct", "--", *paths[i : i + 200], check=False).strip()
                if out.isdigit():
                    t = datetime.fromtimestamp(int(out), UTC)
                    best = t if best is None or t > best else best
            if best:
                return best
        mt = [os.path.getmtime(self.root / p) for p in paths if (self.root / p).exists()]
        return datetime.fromtimestamp(max(mt), UTC) if mt else None
