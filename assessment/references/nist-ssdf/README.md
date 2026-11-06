---
id: nist-ssdf
title: NIST SP 800-218A: Secure Software Development Practices for Generative AI and Dual-Use Foundation Models (SSDF Community Profile)
publisher: NIST
authors: Booth, Souppaya, Vassilev, Ogata, Stanley, Scarfone
published: 2024-07
kind: standard (special publication)
url: https://doi.org/10.6028/NIST.SP.800-218A
retrieved: 2026-11-06
license: Public domain (U.S. Government work)
files:
  - commit NIST.SP.800-218A.pdf e088c8bc75716824dae7c36a987f408364638561d381ed001b5c12254a7b10d8 https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-218A.pdf
  - commit NIST.SP.800-218.pdf 617746e553a9e2da49bfbd4eef0dfc3094758a39b869314e4173ac36605cde22 https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-218.pdf
---

# NIST SP 800-218A: Secure Software Development Practices for Generative AI and Dual-Use Foundation Models (SSDF Community Profile)

SP 800-218 (SSDF v1.1, 2022) is included because 800-218A extends its practice ids (PO, PS, PW, RV).

## Key points

- SSDF 1.1 asks for automated toolchains configured as code ("pipelines-as-code"), kept updated and integrity-checked, and for reproducible builds. (SP 800-218 PO.3.2 Ex.3, Ex.4, Ex.5, Ex.7, p.16)
- Store code and configuration-as-code with least-privilege access and track every change in version control. Signed commits are recommended, and the code owner should review and approve changes made by others. (SP 800-218 PS.1.1 Ex.1-4, p.18)
- Third-party components should be vetted, kept up to date and checked continuously for known vulnerabilities, with detection built into the toolchain. (SP 800-218 PW.4.1 Ex.7, PW.4.4 Ex.1-2, p.21-22)
- Use code review and/or static analysis, ideally run automatically as code is checked in. Linters and formatters are named explicitly as ways to standardise code. (SP 800-218 PW.5.1 Ex.7, p.22; PW.7.2 Ex.1, Ex.4, Ex.6, p.23)
- Testing should be scoped, documented and automated. Tests for previously reported vulnerabilities go into the suite, and fuzzing is recommended. The GenAI profile lists unit, integration, adversarial and red-team testing, and suggests automating tests in the pipeline for regression testing. (SP 800-218 PW.8.2 Ex.2-5, p.24; SP 800-218A PW.8.1.R1/C1, p.25)
- Have a vulnerability disclosure policy and program, and record design decisions and risk responses. (SP 800-218 RV.1.3 Ex.1, p.26; PW.1.2 Ex.2, p.20)
- Provenance for every release, for example an SBOM, should be collected, protected and updated whenever a component changes. The GenAI profile extends this to model training libraries and pipelines, and suggests capturing toolchain versions as provenance. (SP 800-218 PS.3.2, p.19; SP 800-218A PS.3.2.R1, p.21; PW.6.2.C1, p.24)
- GenAI-specific items: monitor environments for plaintext secrets, limit resource and usage rates during model development, and use safe model serialization. (SP 800-218A PO.5.1.R1/R6, p.18-19; PW.6.1.C1, p.24)

## Used for

- `arch.structure`
- `arch.adr`
- `hyg.precommit`
- `hyg.lint`
- `hyg.format`
- `test.ci`
- `test.present`
- `test.layers`
- `sec.precommit_secrets`
- `sec.workflow_permissions`
- `sec.policy`
- `sec.dep_updates`
- `sec.ci_scanning`
- `sec.env_template`
- `sec.no_secrets`
- `sec.codeowners`
- `sec.no_sensitive_files`
- `rep.provenance`
- `rep.documented`
- `rep.lockfile`
- `ci.hygiene`
- `ci.pinning`
- `ci.present`
