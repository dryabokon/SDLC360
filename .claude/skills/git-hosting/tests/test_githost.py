"""Offline checks of githost.py. Run from the skill folder: python -m unittest discover -s tests -v"""
import argparse
import os
import sys
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import githost  # noqa: E402


def ns(**kw):
    base = dict(repo=None, host=None, remote="origin", timeout=5)
    return argparse.Namespace(**{**base, **kw})


class Remotes(unittest.TestCase):
    def test_forms(self):
        cases = {
            "git@github.com:owner/repo.git": ("github.com", "owner/repo"),
            "https://github.com/owner/repo": ("github.com", "owner/repo"),
            "https://user@gitlab.com/group/sub/project.git": ("gitlab.com", "group/sub/project"),
            "ssh://git@git.example.com/team/app.git": ("git.example.com", "team/app"),
            "https://gitlab.com/group/proj/-/merge_requests/12": ("gitlab.com", "group/proj"),
            "https://github.com/o/r/pull/7/files": ("github.com", "o/r"),
        }
        for url, want in cases.items():
            self.assertEqual(githost.parse_remote(url), want, url)

    def test_targets(self):
        t = githost.url_target
        self.assertEqual((t("https://github.com/o/r/pull/7")["kind"], t("https://github.com/o/r/pull/7")["id"]), ("pr", 7))
        self.assertEqual(t("https://gitlab.com/g/p/-/merge_requests/9")["kind"], "pr")
        self.assertEqual(t("https://github.com/o/r/actions/runs/123")["id"], 123)
        self.assertEqual(t("https://gitlab.com/g/p/-/pipelines/55")["kind"], "run")
        self.assertEqual(t("https://gitlab.com/g/p/-/issues/3")["kind"], "issue")
        self.assertEqual(t("https://github.com/o/r/issues/4")["id"], 4)


class HostChoice(unittest.TestCase):
    def setUp(self):
        self.saved = os.environ.pop("GITLAB_HOST", None)

    def tearDown(self):
        os.environ.pop("GITLAB_HOST", None)
        if self.saved is not None:
            os.environ["GITLAB_HOST"] = self.saved

    def test_explicit_gitlab_ignores_a_github_remote(self):
        h = githost.client(ns(repo="gitlab-org/cli", host="gitlab"))
        self.assertIsInstance(h, githost.GitLab)
        self.assertEqual(h.host, "gitlab.com")

    def test_self_managed_gitlab_from_env(self):
        os.environ["GITLAB_HOST"] = "https://git.example.com"
        h = githost.client(ns(repo="team/app", host="gitlab"))
        self.assertEqual((h.host, h.api), ("git.example.com", "https://git.example.com/api/v4"))

    def test_url_decides(self):
        h = githost.client(ns(), githost.url_target("https://gitlab.com/g/p/-/merge_requests/1"))
        self.assertIsInstance(h, githost.GitLab)
        h = githost.client(ns(), githost.url_target("https://github.com/o/r/pull/1"))
        self.assertIsInstance(h, githost.GitHub)


class Logs(unittest.TestCase):
    LOG = "\n".join(["step 1", "error: real cause here", "more", "##[error]Process completed with exit code 1.",
                     "Post job cleanup", "Cleaning up orphan processes"])

    def test_tail_ends_at_last_error_marker(self):
        tail, _ = githost.tail_and_errors(self.LOG, 2)
        self.assertEqual(tail, ["more", "##[error]Process completed with exit code 1."])

    def test_error_lines_skip_tail_and_known_annotations(self):
        _, errs = githost.tail_and_errors(self.LOG, 1)
        self.assertIn("error: real cause here", errs)
        _, errs = githost.tail_and_errors(self.LOG, 1, known=[".github:1 real cause here"])
        self.assertNotIn("error: real cause here", errs)


class Safety(unittest.TestCase):
    def _redirect(self, frm, to):
        req = urllib.request.Request(frm, headers={"Authorization": "Bearer secret", "Private-token": "x"})
        return githost._SameHostAuthRedirect().redirect_request(req, None, 302, "Found", {}, to)

    def test_token_not_forwarded_to_another_host(self):
        new = self._redirect("https://api.github.com/x", "https://blob.core.windows.net/log?sig=1")
        self.assertNotIn("Authorization", {**new.headers, **new.unredirected_hdrs})

    def test_token_kept_on_same_host(self):
        new = self._redirect("https://api.github.com/x", "https://api.github.com/y")
        self.assertIn("Authorization", {**new.headers, **new.unredirected_hdrs})

    def test_force_push_refused_before_git_runs(self):
        for flag in ("--force", "-f", "--force-with-lease"):
            with self.assertRaises(SystemExit) as e:
                githost.cmd_git(ns(repo="o/r", host="github", git_args=["push", flag, "origin", "main"]))
            self.assertIn("force-push is refused", str(e.exception))


if __name__ == "__main__":
    unittest.main()
