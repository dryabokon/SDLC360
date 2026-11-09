---
id: dora-2025-state-of-ai-assisted-development
title: State of AI-assisted Software Development 2025
publisher: DORA, Google Cloud
authors: DORA research team
published: 2025-10 (v2025.2)
kind: research report, 142 pages
url: https://dora.dev/research/2025/dora-report/
retrieved: 2026-11-06
license: CC BY-NC-SA 4.0 (stated in the PDF). Local only because of size (15 MB).
files:
  - local 2025_state_of_ai_assisted_software_development.pdf b403c537496ba97e6cf3fff14d5b172f69fd483b173450bd4b7186c7d56f53f8 https://services.google.com/fh/files/misc/2025_state_of_ai_assisted_software_development.pdf
---

# State of AI-assisted Software Development 2025

## Key points

DORA, *State of AI-assisted Software Development 2025*

- AI is an amplifier: it strengthens what high-performing organisations already do well and makes the problems of struggling ones worse. The biggest returns come from the surrounding system (platform, workflows, team alignment), not from the tools (p. 3, p. 5).
- Adoption is close to universal: 90% use AI at work and more than 80% believe it raised their productivity (p. 4, p. 30). 71% of people who write code use AI to do it, and 65% of AI users rely on it a moderate amount or more (p. 27). Agentic use is still rare: 61% never use agent mode (p. 29).
- Trust is low even though use is high. 30% report little or no trust in AI-generated code (23% "a little", 7% "not at all"), and only 24% trust it "a lot" or "a great deal". DORA reads this "trust but verify" stance as mature adoption, and advises training people to guide, evaluate and validate AI output (p. 4, p. 5, p. 31).
- The throughput/instability split: AI adoption now improves software delivery throughput (in 2024 the effect was negative), but it is still associated with more delivery instability. Instability still harms product performance and burnout, and those losses can cancel out the throughput gains (p. 4, p. 41, p. 42).
- Perceived code quality: 59% see an improvement from AI and 10% see harm (p. 30). AI shows no relationship with friction or burnout. DORA attributes this to the surrounding system rather than the tool (p. 39, p. 43).
- The seven-capability model was chosen from 15 candidate capabilities, using 78 interviews. Each of the seven measurably amplifies AI's effect on outcomes (p. 50). Small batches amplify product performance and reduce friction (p. 58). Frequent commits and rollbacks amplify individual effectiveness and team performance (p. 56). Without a user-centric focus, AI adoption lowers team performance (p. 60).
- Platform engineering: 90% of organisations have an internal platform and 76% have dedicated platform teams (p. 66, p. 67). AI's effect on organisational performance is negligible when platform quality is low and strong when it is high (p. 71). Code written by hand and code written by AI should pass through the same automated testing and deployment (p. 72).
- To carry AI's speed downstream, organisations need to adapt reviews, CI/CD pipelines, security protocols and context: AI first-pass reviews, AI quality checks without manual gates, and exposing docs and decision records to AI (p. 81, p. 82, p. 83, p. 85).
- Case studies: Booking.com saw up to 30% more merge requests once developers learned to give assistants more explicit instructions and context. At Adidas, teams with loosely coupled architectures and fast feedback loops gained 20–30% (p. 10).

## Used for

- `doc.freshness`
- `ai.guardrails`
- `ai.ci_agents`
- `rev.ai_policy`
- `test.ci`
- `arch.boundaries`
- `ci.cd`
- `ci.speed`
- `cost.llm_tracking`
