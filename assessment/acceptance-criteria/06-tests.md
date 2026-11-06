# Tests: how each capability is judged

Capabilities and their priorities are in [capabilities.md](../capabilities.md).
How to edit this file: [assessment/README.md](../README.md#acceptance-criteria).

## test.present: The project has an automated test suite.

**How we check.** Tracked source-extension files under a `test/`, `tests/`, `__tests__/`, `spec/`, `specs/`, `e2e/` or `integration_test(s)/` folder, or named `test_*`, `*_test.*`, `*.test.*`, `*.spec.*` or `*test(s).cs/java/kt`. It counts files.

- **Met:** {target*0.85} or more test files (target: {target}).
- **Partially met:** {target*0.35} or more test files.
- **Not met:** Fewer.

**What the check cannot see.** It counts files, not tests: `conftest.py`, helpers, fixtures and empty files count. Vendored tests count. Names such as `latest.java` or `contest.cs` count as tests. Whether the tests run or pass is not checked.

**Why we expect it.**

> Write the tests and evals before generating the code. Together they are the contract with the AI.
>
> — [google-new-sdlc](../references/google-new-sdlc/), p. 43 · direct

> Give Claude something it can run that comes back pass or fail.
>
> — [anthropic-claude-code-best-practices](../references/anthropic-claude-code-best-practices/), Give Claude a check to run · direct

> Scope the testing, design the tests, perform the testing, and document the results
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218 PW.8.2, p.24 · direct

## test.ci: Tests run in CI on every push and pull request.

**How we check.** It searches `ci_text` (GitHub workflow YAML plus the scripts/Makefile/nox/tox/package.json/pyproject they delegate to) for a test command such as `pytest`, `tox`, `nox`, `npm test`, `jest`, `go test`, `cargo test`, `mvn test`, `dotnet test` or `make test`.

- **Met:** Any test command is found in that text.
- **Partially met:** None is found, but `.gitlab-ci.yml`, `Jenkinsfile`, `azure-pipelines.yml` or `.circleci/config.yml` exists (scores 0.5, file not read).
- **Not met:** Neither.

**What the check cannot see.** This is a plain substring match. `pip install pytest` in a lint job counts. A delegated `Makefile` or `pyproject.toml` is read whole, so `pytest` listed as a dependency or in an unused make target counts. Bitbucket and Travis configs are ignored here.

**Known flaw.** The checklist says "on every push and pull request". Triggers are not checked, so a test step in a nightly-only or manual workflow is Met.

**Why we expect it.**

> whether code is created by hand or by AI, the same automated testing and deployment processes are applied
>
> — [dora-2025-state-of-ai-assisted-development](../references/dora-2025-state-of-ai-assisted-development/), p. 72 · direct

> the convergent process of code review and automated testing is necessary to ensure that changes conform to organizational standards
>
> — [dora-2025-ai-capabilities-model](../references/dora-2025-ai-capabilities-model/), p. 39 · direct

> Consider automating tests within a development pipeline as part of regression testing where possible.
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218A PW.8.1.C1, p.25 · direct

## test.ratio: Tests grow with the code (healthy test-to-source ratio).

**How we check.** The number of test files (as in test.present) divided by the number of source files.

- **Met:** A ratio of {target_ratio*0.85} or more (85% of the target ratio {target_ratio}).
- **Partially met:** A ratio of {target_ratio*0.35} or more.
- **Not met:** A ratio below {target_ratio*0.35}.
- **Not applicable:** No source files.

**What the check cannot see.** It counts files, not lines or tests. Vendored tests inflate the ratio. Shell scripts count as source. One large test file per many modules looks weak even if coverage is high.

**Why we expect it.**

> Add or update tests for the code you change, even if nobody asked.
>
> — [agents-md](../references/agents-md/), README: Sample AGENTS.md file / Testing instructions · supporting

## test.coverage: Coverage is measured and a minimum is enforced.

**How we check.** Coverage files anywhere (`.coveragerc`, `codecov.yml`, `.codecov.yml`, `coverage.config.*`, `.nycrc*`, `jacoco*`, `tarpaulin.toml`). Coverage keywords (`--cov`, `coverage run`, `--coverage`, `codecov`, `coveralls`, `fail_under` and others) in the root `pyproject.toml`, `package.json`, `ci_text` or any `Makefile`/`justfile`. Threshold keywords (`fail_under`, `fail-under`, `coverageThreshold`, `--cov-fail-under`, `minimum_coverage`) are searched in the same places and in the coverage files. Score: 0.6 if measured, plus 0.4 if a threshold is found.

- **Met:** Coverage is measured and a threshold keyword is found.
- **Partially met:** Measured without a threshold (0.6), or a threshold keyword alone (0.4).
- **Not met:** No coverage file or keyword.

**What the check cannot see.** The threshold value is not checked, so `fail_under = 0` passes. A local-only config with no CI step can pass. Thresholds kept in `jest.config.*`/`vitest.config.*` or as a Codecov `target:` are not seen.

**Why we expect it.**

> Require eval coverage with explicit rubrics as a precondition for any agent shipping into a shared workflow, the same way test coverage gates a service deployment.
>
> — [google-new-sdlc](../references/google-new-sdlc/), p. 44 · supporting

> does not include generic software engineering best practices such as ensuring good unit test coverage … Such strategies remain necessary as well.
>
> — [google-ml-test-score](../references/google-ml-test-score/), §I Introduction, p.1 · supporting

## test.framework: The test runner is configured explicitly.

**How we check.** Anywhere in the tree: `pytest.ini`, `conftest.py`, `tox.ini`, `noxfile.py`, `jest/vitest/playwright/cypress` configs, `karma.conf.*`, `.mocharc*`, `phpunit.xml*` or `*.runsettings`. Also `[tool.pytest` in the root `pyproject.toml`, a `"test":` key in the root `package.json`, a `*_test.go` test file, or a root `Cargo.toml` alongside test files.

- **Met:** Test files exist and at least one of these is found.
- **Partially met:** Never.
- **Not met:** No test files, or none of the above.

**What the check cannot see.** Whether the config works is not checked. The npm-init placeholder `"test": "echo \"Error: no test specified\" && exit 1"` passes. A lone `conftest.py` passes.

**Known flaw.** There is no detection for Maven/Gradle (JUnit in `pom.xml`/`build.gradle`), RSpec (`.rspec`, `spec_helper.rb`), .NET test projects without `.runsettings`, or plain `unittest`. Those repos are Not met even when the runner is configured.

**Our convention.** An explicitly configured test runner gives humans and agents one unambiguous command and test discovery rule.

## test.layers: Beyond unit tests there are integration / e2e / property tests.

**How we check.** It searches the test file paths plus the root `pyproject.toml` and `package.json` for three layers: integration (`integration`), e2e (`e2e`, `end.to.end`, `playwright`, `cypress`, `selenium`) and property/fuzz (`hypothesis`, `fast-check`, `proptest`, `quickcheck`, `fuzz`).

- **Met:** 2 or 3 layers are detected.
- **Partially met:** Exactly 1 layer.
- **Not met:** None, or no test files.

**What the check cannot see.** It matches names and dependency lists, not real tests. A `hypothesis` dependency or an "integration" folder name counts even if empty. Layers named differently (`acceptance`, `system`, `smoke`) are missed.

**Known flaw.** The checklist asks for integration/e2e/property tests "beyond unit tests", which one layer satisfies. The code needs two layers for Met.

**Why we expect it.**

> there must be a fully automated test that runs regularly and exercises the entire pipeline
>
> — [google-ml-test-score](../references/google-ml-test-score/), Infra 3, p.5 · direct

> Agents can produce test cases, including edge cases and property-based tests, that humans might not think of.
>
> — [google-new-sdlc](../references/google-new-sdlc/), p. 23 · supporting

> Several forms of code testing can be used for AI models, including unit testing, integration testing, penetration testing, red teaming, use case testing, and adversarial testing.
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218A PW.8.1.R1, p.25 · supporting
