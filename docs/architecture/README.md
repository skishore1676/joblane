# Architecture

JobLane has six stable nouns:

- **Job**: the human outcome being served.
- **Lane**: portable fulfillment for a Job.
- **Ledger**: execution truth.
- **Gate**: fail-closed human authorization.
- **Memory**: fast episodic records plus slow gated durable knowledge.
- **Companion Session**: bounded human/front-door conversation attached to a lane run.
- **Surface**: projection/input channel, never state.

Providers are workers. Control is a steering layer. OpenClaw is a front door or
worker unless a specific workflow elects it as orchestrator of record.

## Ownership

| Concern | Owner |
|---|---|
| Workflow run truth | Ledger |
| Human authorization | Gate contract |
| Durable memory promotion | Memory contract plus gate |
| Multi-turn interaction | Companion session backed by ledger |
| Chat/session labor | Provider/front door |
| Operator views | Surfaces |
| Safe steering | Control |

## One-Orchestrator Rule

The system avoids double kernels by making orchestration ownership explicit per
workflow.

```text
JobLane-orchestrated: JobLane runs stages, gates, ledger, memory.
OpenClaw-orchestrated: OpenClaw runs the workflow; JobLane exposes tools only.
```

The default is JobLane-orchestrated because this repository is proving ledger,
gate, memory, and projection semantics first.

## Companion Sessions

Some Jobs are not one-shot workflows. Fitness coaching, chief-of-staff planning,
and reflection need several turns of human context before a lane can produce a
useful artifact. JobLane models that as a companion session, not as a second
workflow kernel.

```text
front door -> companion session -> fast memory
                         |
                         v
                 proposed slow memory -> gate -> slow memory
```

The session transcript and turn count live in the ledger. The front door may be
OpenClaw, a terminal, Telegram, Obsidian, Apple Notes, Apple Messages, or another
surface. The rule does not change: surfaces and workers may suggest durable
state, but only gate validation can promote it.
