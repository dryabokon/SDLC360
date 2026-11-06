"""Secrets management & security posture."""

from __future__ import annotations

import re

from ..model import Checks, Dimension, short
from ..repo import Repo

# High-confidence token formats. Values are never written to reports - only file:line and a masked prefix.
SECRET_PATTERNS = {
    "AWS access key": r"\b(AKIA|ASIA)[0-9A-Z]{16}\b",
    "GitHub token": r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{60,}\b",
    "Anthropic key": r"\bsk-ant-[A-Za-z0-9_-]{30,}",
    "OpenAI key": r"\bsk-(proj-)?[A-Za-z0-9]{32,}\b",
    "Slack token": r"\bxox[abposr]-[A-Za-z0-9-]{10,}",
    "Google API key": r"\bAIza[0-9A-Za-z_-]{35}\b",
    "Stripe live key": r"\b(sk|rk)_live_[0-9a-zA-Z]{20,}",
    "Private key block": r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY( BLOCK)?-----",
    "Generic assigned secret": r"\b(?i:api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|password|passwd|client[_-]?secret)\b"
    r"\s*[:=]\s*['\"]([^'\"\s$<>{}]{16,})['\"]",
}
PLACEHOLDER = re.compile(
    r"(?i)(x{4,}|\*{3,}|example|placeholder|your[_-]|changeme|dummy|sample|fake|test|redacted|<|\$\{|\{\{|process\.env|os\.environ|getenv)"
)
SENSITIVE_FILES = [
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.jks",
    "id_rsa",
    "id_ed25519",
    "*.keystore",
    "credentials.json",
    "service-account*.json",
    "*.tfstate",
    "*.tfvars",
    ".npmrc",
    ".pypirc",
    ".netrc",
    ".env",
    ".env.*",
    "*.env",
]
SAFE_ENV = re.compile(r"(?i)\.(example|sample|template|dist|defaults?)$|example|\.env\.test$")
SEC_TOOLS = r"codeql|gitleaks|trufflehog|detect-secrets|trivy|snyk|semgrep|bandit|pip-audit|npm audit|osv-scanner|dependency-review|grype|zizmor|checkov|tfsec|safety check|govulncheck|cargo audit|scorecard"


def scan_secrets(repo: Repo) -> list[dict]:
    rx = {k: re.compile(v) for k, v in SECRET_PATTERNS.items()}
    union = re.compile("|".join(f"(?:{v})" for v in SECRET_PATTERNS.values()))
    findings = []
    skip = re.compile(r"(?i)(\.lock$|lock\.json$|\.min\.js$|\.map$|\.svg$|(^|/)(fixtures?|testdata|__snapshots__)/)")
    for f in repo.text_files(max_size=500_000):
        if skip.search(f):
            continue
        text = repo.read(f)
        if not text or not union.search(text):  # fast pre-filter: one pass per file
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if len(line) > 2000:
                continue
            for kind, r in rx.items():
                m = r.search(line)
                if not m:
                    continue
                value = m.group(m.lastindex or 0) if kind == "Generic assigned secret" else m.group(0)
                if kind != "Private key block" and PLACEHOLDER.search(value):
                    continue
                if kind == "Generic assigned secret" and (
                    repo.is_test(f) or len(set(value)) < 6 or not (re.search(r"\d", value) and re.search(r"[A-Za-z]", value))
                ):
                    continue  # identifiers like "oauth_client_secret" are not secrets: real ones mix letters and digits
                findings.append({"file": f, "line": i, "kind": kind, "in_test": repo.is_test(f), "masked": value[:4] + "…" + f"({len(value)} chars)"})
                break
        if len(findings) >= 50:
            break
    return findings


def assess(repo: Repo):
    c = Checks()
    findings = scan_secrets(repo)
    high = [x for x in findings if x["kind"] != "Generic assigned secret" and not x["in_test"]]
    score = 0.0 if high else 0.5 if any(x["kind"] == "Generic assigned secret" for x in findings) else 0.75 if findings else 1.0
    c.add(
        "sec.no_secrets",
        "No hard-coded secrets in tracked files (HEAD)",
        5,
        score,
        [
            f"{x['kind']} at {x['file']}:{x['line']} [{x['masked']}]" + (" - in tests, likely a fake fixture" if x["in_test"] else "")
            for x in findings[:10]
        ]
        or ["no token patterns found"],
        "Rotate the exposed credentials immediately, purge them from history (git filter-repo / BFG), "
        "and load secrets from env vars or a secret manager.",
    )

    sens = [
        f
        for f in repo.find(*SENSITIVE_FILES)
        if not SAFE_ENV.search(f)
        and not f.lower().endswith(".pub")
        and not re.search(r"(^|/)(tests?|fixtures?|testdata|examples?|samples?|docs?)/", f.lower())
    ]
    c.add(
        "sec.no_sensitive_files",
        "No credential files committed (.env, *.pem, tfstate, …)",
        4,
        1.0 if not sens else 0.0,
        [f"committed: {short(sens)}"] if sens else ["none committed"],
        "Remove the files from the repo, rotate anything inside them, and add the patterns to .gitignore.",
    )

    gi = "\n".join(repo.read(f) for f in repo.find(".gitignore"))
    wanted = {".env": (r"(^|/)\*?\.env", 0.7), "keys/certs": (r"\*\.(pem|key|p12)|\.pem|\.key\b", 0.3)}
    got = [k for k, (p, _) in wanted.items() if re.search(p, gi, re.I | re.M)]
    c.add(
        "sec.gitignore",
        ".gitignore protects env files and keys",
        2,
        sum(wanted[k][1] for k in got) if gi else 0.0,
        [f"covers: {', '.join(got) or 'nothing relevant'}"] if gi else ["no .gitignore"],
        "Add `.env`, `.env.*` (with `!.env.example`), `*.pem`, `*.key`, `*.local.*` to .gitignore.",
    )

    uses_env = bool(
        repo.grep(
            r"os\.environ|getenv\(|process\.env\.|dotenv|env::var|System\.getenv|Environment\.GetEnvironmentVariable",
            files=repo.source_files[:3000],
            max_hits=1,
        )
    )
    example = repo.find(".env.example", ".env.sample", ".env.template", "*.env.example", ".env.dist")
    c.add(
        "sec.env_template",
        "Env template documents required secrets (.env.example)",
        1.5,
        (1.0 if example else 0.2) if uses_env else None,
        [f"template: {short(example)}"] if example else ["code reads env vars but no template found"] if uses_env else ["no env usage detected"],
        "Commit a `.env.example` listing every variable with placeholder values.",
    )

    secpol = repo.find("SECURITY.md", ".github/SECURITY.md", "docs/SECURITY.md")
    c.add(
        "sec.policy",
        "Security policy (SECURITY.md)",
        1,
        bool(secpol),
        short(secpol),
        "Add SECURITY.md describing supported versions and how to report vulnerabilities.",
    )

    dep = repo.find(".github/dependabot.yml", ".github/dependabot.yaml", "renovate.json", ".renovaterc*", ".github/renovate.json*")
    c.add(
        "sec.dep_updates",
        "Automated dependency updates (Dependabot / Renovate)",
        2,
        bool(dep),
        short(dep),
        "Enable Dependabot (`.github/dependabot.yml`) for every package ecosystem plus github-actions.",
    )

    tools = sorted(set(m.lower() for m in re.findall(SEC_TOOLS, repo.ci_text, re.I)))
    c.add(
        "sec.ci_scanning",
        "Security scanning in CI (SAST / deps / secrets)",
        3,
        min(1.0, len(tools) / 2),
        [f"tools in workflows: {', '.join(tools) or 'none'}"],
        "Add CodeQL (SAST), a dependency audit (dependency-review / pip-audit / npm audit) and gitleaks to CI.",
    )

    pc = "\n".join(repo.read(f) for f in repo.find(".pre-commit-config.yaml", ".husky/*", "lefthook.yml", ".lefthook.yml"))
    secret_hooks = re.findall(r"gitleaks|detect-secrets|trufflehog|detect-private-key|ggshield", pc, re.I)
    c.add(
        "sec.precommit_secrets",
        "Pre-commit secret detection",
        1.5,
        bool(secret_hooks),
        f"hooks: {', '.join(sorted(set(h.lower() for h in secret_hooks)))}" if secret_hooks else "no secret-scanning hook",
        "Add gitleaks or detect-secrets to .pre-commit-config.yaml so secrets never reach a commit.",
    )

    if repo.workflows:
        has_perm = sum(1 for f in repo.workflows if re.search(r"^\s*permissions\s*:", repo.read(f), re.M))
        prt = re.findall(r"pull_request_target", repo.workflow_text)
        s = has_perm / len(repo.workflows) - (0.3 if prt else 0)
        c.add(
            "sec.workflow_permissions",
            "Least-privilege workflow tokens (`permissions:` set)",
            1.5,
            s,
            [f"{has_perm}/{len(repo.workflows)} workflows declare permissions"] + (["uses pull_request_target (review carefully)"] if prt else []),
            "Declare `permissions: contents: read` at workflow top-level and widen per job only when needed.",
        )
    else:
        c.add("sec.workflow_permissions", "Least-privilege workflow tokens (`permissions:` set)", 1.5, None, "no workflows")

    owners = repo.find("CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS")
    c.add(
        "sec.codeowners",
        "CODEOWNERS for review ownership",
        0.5,
        bool(owners),
        short(owners),
        "Add .github/CODEOWNERS so security-sensitive paths require an owner's review.",
    )
    return c.items


DIMENSION = Dimension(
    "security", "Security & Secrets", "Hard-coded secrets, credential files, ignore rules, dependency & code scanning, policies.", assess
)
