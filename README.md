# JobLane

JobLane is a small operating system for Job-serving agent lanes.

The product model is:

```text
Jobs-to-be-Done define demand.
Lane packs fulfill demand.
The ledger records truth.
Gates authorize consequential effects.
Surfaces project state.
Providers supply replaceable labor.
```

JobLane is not a chat app and not a model wrapper. It is the durable proof layer
around agent work: runs, artifacts, receipts, decisions, memory, and projections.
OpenClaw, Claude, Codex, deterministic scripts, or future agents can all be
workers behind the same lane contract.

## Current Tracer Bullets

The first repo slice proves six Jobs at fixture level:

| Job | Lane |
|---|---|
| A. Public presence | `public_presence` |
| B. Keep me strong | `fitness` |
| C. Trading intelligence | `trading_intel` |
| D. Chief of staff | `chief_of_staff` |
| E. Memory/reflection | `reflection` |
| F. Small experiment | `experiment` |

Each lane is intentionally small. The goal is not completeness yet; the goal is
to prove that every Job can move through the same durable substrate.

## Quickstart

```bash
make check
python3 -m joblane.cli run public_presence
python3 -m joblane.cli decide <run_id> <gate_id> approve
python3 -m joblane.cli run-all
python3 -m joblane.cli doctor
python3 -m joblane.cli scorecard
python3 -m joblane.cli export-openclaw-skills
python3 -m joblane.cli status
```

By default, all state is local under `state/` and all surfaces are sandboxed.
No live send, publish, broker, or auth mutation exists in this first slice.

## The Kernel Conflict Rule

For any workflow, exactly one system owns orchestration state.

```text
one workflow -> one orchestrator of record
```

Default: JobLane owns durable orchestration, ledger, gates, memory policy, and
surface projections. OpenClaw owns conversational front door, agent sessions,
skills, and worker turns.

If a future lane delegates orchestration to OpenClaw Task Flow or Lobster, then
JobLane must become a library/toolset for that workflow and must not also run a
competing scheduler or gate loop.
