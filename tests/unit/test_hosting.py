"""Hosted mode (SDLC360_CLOUD=1) and repositories on hosts besides GitHub (SDLC360_GIT_HOSTS)."""

import base64
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from src import hosting
from src.render import render_app
from src.repo import check_target, hosted_match
from src.serve import IAP_USER, hosted_request, make_handler

HOST = "https://git.example.org/team/tools/sdlc360"


@pytest.fixture(autouse=True)
def hosts(monkeypatch):
    monkeypatch.setenv("SDLC360_GIT_HOSTS", "git.example.org")


@pytest.fixture
def cloud(monkeypatch):
    monkeypatch.setenv("SDLC360_CLOUD", "1")


@pytest.mark.parametrize("t", [HOST, HOST + ".git", HOST + "/", "git.example.org/team/tools/sdlc360"])
def test_hosted_forms(t):
    assert hosted_match(t) == ("git.example.org", "team/tools/sdlc360")
    assert check_target(t) == {"kind": "hosted", "display": "team/tools/sdlc360"}


@pytest.mark.parametrize("t", ["https://gitlab.example.com/a/b", "https://git.example.org/onlyone", "https://git.example.org/a/../b"])
def test_hosted_rejects_unknown_host_and_odd_paths(t):
    assert hosted_match(t) is None


def test_hosts_come_from_the_environment(monkeypatch):
    monkeypatch.setenv("SDLC360_GIT_HOSTS", "gitlab.example.com")
    assert hosted_match("https://gitlab.example.com/a/b") == ("gitlab.example.com", "a/b")
    assert hosted_match(HOST) is None


def test_remote_sources_and_short_names():
    assert hosting.is_remote("github.com/encode/httpx") and hosting.is_remote("git.example.org/g/sub/r")
    assert not hosting.is_remote("D:\\work\\repo") and not hosting.is_remote("/home/me/repo")
    assert hosting.short_name("github.com/encode/httpx") == "encode/httpx"
    assert hosting.short_name("git.example.org/g/sub/r") == "g/sub/r"


def test_git_token_only_for_its_hosts(monkeypatch):
    monkeypatch.delenv("SDLC360_GIT_TOKEN", raising=False)
    assert hosting.git_auth_env("git.example.org") == {}
    monkeypatch.setenv("SDLC360_GIT_TOKEN", "t" * 8)
    assert hosting.git_auth_env("github.com") == {}  # never sent anywhere else
    env = hosting.git_auth_env("git.example.org")
    assert env["GIT_CONFIG_KEY_0"] == "http.https://git.example.org/.extraheader"
    assert env["GIT_CONFIG_VALUE_0"] == "Authorization: Basic " + base64.b64encode(b"oauth2:" + b"t" * 8).decode()


def test_cloud_refuses_the_servers_own_disk(cloud, make_repo):
    root = make_repo({"a.txt": "x"}, name="proj")
    with pytest.raises(ValueError, match="repository URL"):
        check_target(str(root))
    assert check_target("encode/httpx")["kind"] == "github"
    assert check_target(HOST)["kind"] == "hosted"


def test_hosted_request_needs_iap_user_and_same_origin():
    assert not hosted_request("x.run.app", None, None)
    assert hosted_request("x.run.app", None, "accounts.google.com:me@example.com")
    assert hosted_request("x.run.app", "https://x.run.app", "accounts.google.com:me@example.com")
    assert not hosted_request("x.run.app", "https://evil.example", "accounts.google.com:me@example.com")


def test_page_knows_it_is_hosted(monkeypatch):
    assert "const HOSTED = /*__HOSTED__*/false;" in render_app()
    monkeypatch.setenv("SDLC360_CLOUD", "1")
    assert "const HOSTED = true;" in render_app()


def test_cloud_server_endpoints(cloud, tmp_path):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(tmp_path / "runs", tmp_path / "cache"))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    def status(path: str, user: str | None = "accounts.google.com:me@example.com", method: str = "GET") -> int:
        req = urllib.request.Request(base + path, method=method, data=b"{}" if method == "POST" else None)
        if user:
            req.add_header(IAP_USER, user)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code

    try:
        assert status("/api/projects") == 200
        assert status("/api/projects", user=None) == 403  # not through IAP
        assert status("/api/fs") == 404  # the server's folders
        assert status("/api/agent?run=x") == 404  # Claude Code logs of the server
        assert status("/api/shutdown", method="POST") == 404
        assert status("/v1/logs", method="POST") == 404
    finally:
        httpd.shutdown()
        httpd.server_close()
