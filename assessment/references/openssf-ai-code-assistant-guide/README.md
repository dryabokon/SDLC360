---
id: openssf-ai-code-assistant-guide
title: Security-Focused Guide for AI Code Assistant Instructions
publisher: OpenSSF Best Practices and AI/ML Working Groups
authors: OpenSSF
published: 2025-08-01
kind: guide
url: https://best.openssf.org/Security-Focused-Guide-for-AI-Code-Assistant-Instructions
retrieved: 2026-11-06
license: Apache-2.0 (github.com/ossf/wg-best-practices-os-developers)
files:
  - commit Security-Focused-Guide-for-AI-Code-Assistant-Instructions.md a663b8579e8def52cb90d2bfc2b89ab712eb17ff910dcc2fae1c16badc0ef6e7 https://raw.githubusercontent.com/ossf/wg-best-practices-os-developers/main/docs/Security-Focused-Guide-for-AI-Code-Assistant-Instructions.md
---

# Security-Focused Guide for AI Code Assistant Instructions

## Key points

- Repositories should carry an AI instruction file (CLAUDE.md, Copilot instructions, Cursor rules and so on) that encodes security expectations. It should be concise, specific and actionable, and the AI can be asked to build it from the guide. (Introduction; TL;DR > Guide the AI)
- AI-generated code still has to go through code review, testing, static analysis, documentation and version-control discipline. (TL;DR > Apply Engineering Best Practices Always)
- Secrets must never be hard-coded in code or in CI workflow files. Use environment variables, GitHub Secrets or vaults instead. (Secure Coding Principles > Authentication, Authorization & Secrets Management; Platform and Runtime > Operational Security)
- Supply chain: use the official package manager, specify version ranges or exact versions, update regularly, guard against hallucinated or slopsquatted packages, generate SBOMs (SPDX/CycloneDX) and use in-toto style attestations. (Addressing Software Supply Chain Security)
- CI/CD should run SAST/DAST and dependency checks. GitHub Actions should be locked to specific SHAs. (Platform and Runtime > Operational Security)
- Containers should use minimal, official base images pinned by digest and should not run as root. (Platform and Runtime > Container and Deployment Considerations)
- Use linters and type hints (PEP 8 and type hints for Python), and write negative unit tests for security-critical functions. (Programming Language-Specific > Python; Secure Coding Principles > Testing for Security)

## Used for

- `hyg.lint`
- `hyg.types`
- `rep.environment`
- `ci.pinning`
- `sec.no_secrets`
- `sec.no_sensitive_files`
- `sec.ci_scanning`
- `sec.dep_updates`
- `sec.workflow_permissions`
- `sec.env_template`
