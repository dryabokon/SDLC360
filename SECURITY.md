# Security policy

Please report vulnerabilities privately through GitHub's **Report a vulnerability** (Security tab).
Do not open public issues for them. Expect a first answer within a week.

Scope notes:

- The web app binds to 127.0.0.1 only. It rejects requests whose `Host` or `Origin` is not local (DNS rebinding
  and cross-site requests).
- Scans read the target repository and never write to it. GitHub targets are cloned into `.cache/repos/`.
- Secrets found by the scanner are masked in reports (first 4 characters and the length).
