"""Where SDLC360 runs: on this machine (default) or hosted (SDLC360_CLOUD=1: Cloud Run behind Identity-Aware Proxy).

Hosted, the app serves many people from one server, so everything that reads this machine is off: local folders,
the folder browser, Claude Code session logs, telemetry and /api/shutdown. Repositories come by URL only, from GitHub
or from the hosts in SDLC360_GIT_HOSTS (none by default), cloned with SDLC360_GIT_TOKEN when it is set.
Settings are read at call time, so tests can change them. See docs/deploy-gcp.md.
"""

from __future__ import annotations

import base64
import os


def cloud() -> bool:
    return os.environ.get("SDLC360_CLOUD", "") == "1"


def git_hosts() -> tuple[str, ...]:
    """Git hosts besides github.com whose repositories are cloned by URL: https://<host>/<group>/.../<repo>."""
    return tuple(h.strip().lower() for h in os.environ.get("SDLC360_GIT_HOSTS", "").split(",") if h.strip())


def is_remote(source: str) -> bool:
    """A run's source is a cloned repository (github.com/o/r, <host>/g/.../r), not a local folder."""
    return source.startswith("github.com/") or any(source.startswith(h + "/") for h in git_hosts())


def short_name(source: str) -> str:
    """owner/repo for GitHub, group/.../repo for the other hosts; a local source is returned as it is."""
    for host in ("github.com", *git_hosts()):
        if source.startswith(host + "/"):
            return source[len(host) + 1 :]
    return source


def target_of(source: str) -> str:
    """What to clone a remote run's source from: github.com/o/r -> o/r, <host>/<path> -> https://<host>/<path>."""
    return source[len("github.com/") :] if source.startswith("github.com/") else "https://" + source


def git_auth_env(host: str) -> dict[str, str]:
    """Environment that makes git send the token to <host> only. Passed as GIT_CONFIG_* variables, so the token is
    never in the command line (error messages quote it), the remote URL or .git/config."""
    token = os.environ.get("SDLC360_GIT_TOKEN", "").strip()
    if not token or host not in git_hosts():
        return {}
    basic = base64.b64encode(f"oauth2:{token}".encode()).decode()
    return {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": f"http.https://{host}/.extraheader",
        "GIT_CONFIG_VALUE_0": f"Authorization: Basic {basic}",
        "GIT_TERMINAL_PROMPT": "0",
    }
