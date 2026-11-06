---
id: 13-google-ml-test-score
title: The ML Test Score: A Rubric for ML Production Readiness and Technical Debt Reduction
publisher: Google; IEEE Big Data 2017
authors: Eric Breck, Shanqing Cai, Eric Nielsen, Michael Salib, D. Sculley
published: 2017
kind: peer-reviewed paper, 10 pages
url: https://research.google/pubs/the-ml-test-score-a-rubric-for-ml-production-readiness-and-technical-debt-reduction/
retrieved: 2026-11-06
license: (c) 2017 IEEE: personal use permitted, redistribution not. Kept local only.
files:
  - local ml-test-score.pdf 8db5862dc7c7aaa2c55bb43bd42fc55531a0503782b7026b5811c00c98befd31 https://research.google.com/pubs/archive/aad9f93b86b7addfea4c419b9100c6cdd26cacea.pdf
---

# The ML Test Score: A Rubric for ML Production Readiness and Technical Debt Reduction

Its final score is the minimum over sections: the same idea as our critical gate.

## Key points

- The rubric has 28 tests in four sections: Data, Model, Infrastructure and Monitoring. It deliberately leaves out generic practices such as unit-test coverage and a well-defined binary release process, while saying these "remain necessary". (§I Introduction, p.1)
- Scoring: a test gets 0.5 point if it is run manually with documented and distributed results, and 1 point if it is automated and run repeatedly. Points are summed per section, and the final ML Test Score is the minimum of the four section sums. All tests weigh the same. (§VI.A Computing an ML Test Score, p.7; p.8)
- Reproducibility: training twice on the same data should produce identical models. Seeding addresses RNG non-determinism, but initialization order and threading also matter. (Infra 1, p.4)
- Model specs should be code-reviewed and checked in, so that the exact code behind a model is known, which supports audit and reproducibility. (Model 1, p.3)
- Unit-test model code cheaply, for example by training one step on random data or restoring from a checkpoint. Avoid "golden" tests. (Infra 2, p.4-5)
- A fully automated integration test should exercise the whole ML pipeline regularly. In practice this was one of the least adopted tests. (Infra 3, p.5; §VII.C, p.8-9)
- Validate model quality automatically before serving, canary models, and be able to roll back. Capture data expectations in a schema and monitor data against it. (Infra 4, 6, 7, p.5; Data 1, p.2; Monitor 2, p.6)
- Checklists help even expert teams. One team found a thousand-line feature file with no tests at all. (§VII.A, p.8)

## Used for

- `test.layers`
- `test.coverage`
- `rep.seeds`
