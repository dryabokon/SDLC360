"""Runs & reproducibility: can local results / experiments be reproduced and traced?"""

from __future__ import annotations

import re

from ..model import Checks, Dimension, short
from ..repo import Repo

RUN_DIRS = ("runs", "experiments", "outputs", "artifacts", "results", "mlruns", "wandb", "logs/runs", "reports/runs")
MANIFEST = re.compile(r"(manifest|config|params|meta(data)?|run|args|hparams|summary|metrics)\.(json|ya?ml|toml)$", re.I)


def assess(repo: Repo):
    c = Checks()
    disk_dirs = {d.split("/")[0].lower() for d in repo.on_disk if "/" in d} if repo.is_git else set()
    tracked_dirs = {d.split("/")[0].lower() for d in repo.files if "/" in d}
    gi = "\n".join(repo.read(f) for f in repo.find(".gitignore"))
    found_tracked = [d for d in RUN_DIRS if d.split("/")[0] in tracked_dirs]
    found_disk = [d for d in RUN_DIRS if d.split("/")[0] in disk_dirs and d not in found_tracked]
    ignored = [d for d in RUN_DIRS if re.search(rf"(^|/){re.escape(d)}/?\s*$", gi, re.M | re.I)]
    present = found_tracked or found_disk
    c.add(
        "run.folder",
        "Runs folder for experiment / execution outputs",
        3,
        1.0 if present else (0.5 if ignored else 0.0),
        [f"tracked: {short(found_tracked)}", f"local-only: {short(found_disk)}", f"git-ignored: {short(ignored)}"],
        "Adopt a `runs/<timestamp>_<name>/` convention: every execution writes its config, logs, metrics and outputs there.",
    )

    run_files = [f for f in (repo.on_disk if repo.is_git else repo.files) if f.split("/")[0].lower() in {d.split("/")[0] for d in RUN_DIRS}]
    manifests = [f for f in run_files if MANIFEST.search(f)]
    c.add(
        "run.manifest",
        "Each run records its config / manifest (traceable)",
        2.5,
        min(1.0, len(manifests) / 2) if run_files else 0.0,
        f"{len(manifests)} manifest/config files inside run folders" + (f": {short(manifests, 3)}" if manifests else ""),
        "Write a manifest.json per run: git SHA, dirty flag, command line, config, seed, package versions, timestamps.",
    )

    docs = "\n".join(repo.read(f) for f in repo.find("README*", "CLAUDE.md", "AGENTS.md", "docs/*.md")[:30])
    documented = bool(re.search(r"\b(runs?/|experiments?/|reproduc)", docs, re.I))
    c.add(
        "run.documented",
        "Run / reproduction procedure documented",
        1.5,
        documented,
        "README/docs mention runs/ or reproduction" if documented else "no reproduction instructions found",
        "Document how to reproduce a run: exact command, where outputs land, how to compare runs.",
    )

    tracking = repo.grep(
        r"\b(mlflow|wandb|dvc|sacred|hydra|aim\b|neptune|clearml|tensorboard|comet_ml|optuna)",
        files=repo.source_files[:3000] + repo.find("requirements*.txt", "pyproject.toml", "package.json", "dvc.yaml"),
        max_hits=5,
    )
    dvc = repo.find("dvc.yaml", ".dvc/config", "MLproject")
    c.add(
        "run.tracking",
        "Experiment tracking / pipeline tooling",
        1,
        1.0 if (tracking or dvc) else (0.5 if manifests else None),
        short(sorted({h[2][:40] for h in tracking}) + dvc, 3) if (tracking or dvc) else "none (fine for non-ML projects)",
        "For experiments, log params/metrics with MLflow/W&B or a lightweight runs/ manifest.",
    )

    locks = repo.find(
        "uv.lock",
        "poetry.lock",
        "Pipfile.lock",
        "pdm.lock",
        "requirements*.lock",
        "requirements.txt",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "bun.lockb",
        "Cargo.lock",
        "go.sum",
        "Gemfile.lock",
        "composer.lock",
        "packages.lock.json",
        "conda-lock.yml",
        "environment.yml",
        "gradle.lockfile",
    )
    pinned_req = any(re.search(r"==", repo.read(f)) for f in locks if f.endswith(".txt"))
    lock_score = 1.0 if [f for f in locks if not f.endswith(".txt")] or pinned_req else (0.4 if locks else 0.0)
    c.add(
        "run.lockfile",
        "Dependencies locked",
        2,
        lock_score if repo.source_files else None,
        short(locks),
        "Commit a lockfile (uv.lock / package-lock.json / Cargo.lock …).",
    )

    env = repo.find(
        "Dockerfile",
        "*.dockerfile",
        "docker-compose*.yml",
        "compose.y*ml",
        ".devcontainer/*",
        "flake.nix",
        "shell.nix",
        ".python-version",
        ".nvmrc",
        ".node-version",
        ".tool-versions",
        "rust-toolchain*",
        "global.json",
        ".sdkmanrc",
        "mise.toml",
    )
    c.add(
        "run.environment",
        "Pinned runtime environment (container / devcontainer / version files)",
        1.5,
        min(1.0, len(env) / 2),
        short(env),
        "Pin toolchain versions (.python-version / .nvmrc) and provide a Dockerfile or devcontainer.",
    )

    runner = repo.find(
        "Makefile", "justfile", "Justfile", "Taskfile.y*ml", "noxfile.py", "tox.ini", "scripts/*", "start*.sh", "run*.sh", "start*.bat"
    )
    if re.search(r'"scripts"\s*:', repo.read("package.json")) or "[project.scripts]" in repo.read("pyproject.toml"):
        runner.append("declared scripts")
    c.add(
        "run.entrypoints",
        "One-command entry points (Makefile / just / scripts)",
        1,
        bool(runner),
        short(runner),
        "Provide `make test`, `make run`, `make repro RUN=…` style entry points.",
    )

    seeds = repo.grep(r"\b(seed\(|random_state|manual_seed|set_seed|--seed|SEED\s*=)", files=repo.source_files[:3000], max_hits=3)
    ml = repo.grep(r"\b(import (torch|tensorflow|sklearn|numpy|jax)|from (torch|sklearn|transformers))", files=repo.source_files[:2000], max_hits=1)
    c.add(
        "run.seeds",
        "Randomness controlled (seeds) where relevant",
        0.5,
        (1.0 if seeds else 0.0) if ml else None,
        short([f"{h[0]}:{h[1]}" for h in seeds], 3) if ml else "no ML/numeric stack detected",
        "Seed every RNG (python, numpy, torch) and record the seed in the run manifest.",
    )
    return c.items


DIMENSION = Dimension(
    "runs", "Runs & Reproducibility", "runs/ folders with manifests, documented reproduction, locked deps, pinned environments.", assess
)
