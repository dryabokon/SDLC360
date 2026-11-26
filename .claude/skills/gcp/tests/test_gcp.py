"""Offline checks of gcp.py: error compaction and deploy / rollback plans against recorded gcloud answers.
Run from the skill folder: python -m unittest discover -s tests -v"""
import argparse
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import gcp  # noqa: E402

# What gcloud answered for a real service (trimmed) - the same setup 8Allo deploys.
SERVICE = {"spec": {"template": {"spec": {"containers": [
    {"image": "europe-west1-docker.pkg.dev/demo/hdx-signals/app:20261022-140556"}]}}},
    "status": {"traffic": [{"percent": 100, "revisionName": "app-00005"}]}}
REVISIONS = [{"metadata": {"name": n}, "status": {"conditions": [{"type": "Ready", "status": s}]}}
             for n, s in (("app-00005", "True"), ("app-00004", "False"), ("app-00003", "True"))]
ENABLED = [{"config": {"name": n}} for n in ("run.googleapis.com", "cloudbuild.googleapis.com", "iap.googleapis.com",
                                              "artifactregistry.googleapis.com", "secretmanager.googleapis.com")]


class FakeG(gcp.G):
    """gcloud stand-in: answers from the recordings above, never runs anything."""
    existing = {"service": True, "secret": True, "repo": True, "sa": True}

    def __init__(self, a):
        self.exe, self.wsl_windows, self.account = "gcloud", False, None
        self.project, self.region = "demo", "europe-west1"

    def config(self, key):
        return None

    def path(self, p):
        return p

    def json(self, *args, ok_missing=False):
        key = " ".join(args[:3])
        if key.startswith("services list"):
            return ENABLED
        if key.startswith("run services describe"):
            return SERVICE if self.existing["service"] else None
        if key.startswith("run revisions list"):
            return REVISIONS
        if key.startswith("artifacts repositories describe"):
            return {"name": args[3]} if self.existing["repo"] else None
        if key.startswith("secrets describe"):
            return {"name": args[2]} if self.existing["secret"] else None
        if key.startswith("iam service-accounts describe"):
            return {} if self.existing["sa"] else None
        raise AssertionError(f"unexpected gcloud call: {args}")

    def run(self, argv, stdin_bytes=None):
        raise AssertionError("a plan must not execute anything")


def deploy_args(**kw):
    base = dict(name="app", source=".", image=None, env=None, secret=["ANTHROPIC_API_KEY=anthropic-api-key"],
                mount=["demo-runs:/app/runs"], access="iap", service_account="site@demo.iam.gserviceaccount.com",
                min=None, max=1, cpu="1", memory="1Gi", timeout=900, cpu_always_on=True, repo=None, apply=False,
                project=None, region=None, json=False)
    return argparse.Namespace(**{**base, **kw})


class Plans(unittest.TestCase):
    def setUp(self):
        self.real = gcp.G
        gcp.G = FakeG
        FakeG.existing = {"service": True, "secret": True, "repo": True, "sa": True}

    def tearDown(self):
        gcp.G = self.real

    def commands(self, a):
        data, _ = gcp.cmd_deploy(a)
        self.assertFalse(data["applied"])
        return [s["command"] for s in data["steps"]], data["notes"]

    def test_deploy_like_8allo(self):
        cmds, notes = self.commands(deploy_args())
        deploy = cmds[-1]
        self.assertTrue(any("builds submit" in c for c in cmds))
        self.assertIn("/hdx-signals/app:", deploy)            # keeps the service's image repository
        for flag in ("--iap", "--no-allow-unauthenticated", "--update-secrets=ANTHROPIC_API_KEY=anthropic-api-key:latest",
                     "--add-volume-mount=volume=demo-runs,mount-path=/app/runs", "--execution-environment=gen2",
                     "--no-cpu-throttling", "--max-instances=1", "--service-account=site@demo.iam.gserviceaccount.com"):
            self.assertIn(flag, deploy)
        self.assertFalse(any("services enable" in c for c in cmds))  # everything needed is on
        self.assertTrue(any("secretAccessor" in c for c in cmds))    # the account may read its secret
        self.assertTrue(any("existing repository" in n for n in notes))

    def test_new_service_gets_a_repository_and_missing_apis_are_enabled(self):
        FakeG.existing.update(service=False, repo=False)
        saved = ENABLED[:]
        ENABLED[:] = [e for e in ENABLED if e["config"]["name"] != "iap.googleapis.com"]
        try:
            cmds, _ = self.commands(deploy_args(name="new-app", access="iap"))
        finally:
            ENABLED[:] = saved
        self.assertTrue(any("artifacts repositories create cloud-run" in c for c in cmds))
        self.assertTrue(any("services enable iap.googleapis.com" in c for c in cmds))

    def test_missing_secret_stops_the_plan(self):
        FakeG.existing["secret"] = False
        with self.assertRaises(SystemExit) as e:
            gcp.cmd_deploy(deploy_args())
        self.assertIn("secret-set anthropic-api-key", str(e.exception))

    def test_public_access_is_called_out(self):
        _, notes = self.commands(deploy_args(access="public", secret=None, mount=None, service_account=None))
        self.assertTrue(any("anyone on the internet" in n for n in notes))

    def test_rollback_skips_the_serving_and_the_broken_revision(self):
        data, _ = gcp.cmd_rollback(argparse.Namespace(name="app", to=None, apply=False, project=None, region=None))
        self.assertIn("--to-revisions=app-00003=100", data["steps"][0]["command"])


class Errors(unittest.TestCase):
    def test_disabled_api(self):
        err = ("ERROR: (gcloud.sql.instances.list) ... Cloud SQL Admin API has not been used in project x before or "
               "it is disabled.\n  reason: SERVICE_DISABLED\n  service: sqladmin.googleapis.com")
        self.assertIn("sqladmin.googleapis.com is not enabled", gcp.short_error(err))

    def test_rate_limit_and_generic(self):
        self.assertIn("rate-limited", gcp.short_error("... 'status': 429 ... RESOURCE_EXHAUSTED"))
        self.assertEqual(gcp.short_error("ERROR: (gcloud.run.deploy) Image not found."), "Image not found.")

    def test_sizes(self):
        self.assertEqual(gcp.human_size("27955"), "27.3 KB")
        self.assertEqual(gcp.human_size(None), "-")


if __name__ == "__main__":
    unittest.main()
