# JobLane Agent Instructions

This repository is greenfield and public-generic. Keep product concepts generic:
Jobs-to-be-Done, lanes, ledger, gates, memory, surfaces, providers, control.

Do not add operator-specific names, secrets, live paths, or runtime state to
source. Fixtures may be illustrative, but they must stay generic.

Protected gates:

- no live trading, broker, money movement, or account mutation
- no auth/secret changes or token printing
- no public posts, emails, or real sends without an explicit human gate
- no destructive migration or live production cutover without explicit approval

Default build stance:

- one workflow has one orchestrator of record
- JobLane owns durable proof: ledger, gates, memory policy, projections
- OpenClaw/Jarvis/Claude/Codex are workers or front doors unless a workflow is
  explicitly delegated to OpenClaw as orchestrator of record

