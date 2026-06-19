# Architecture

JobLane has six stable nouns:

- **Job**: the human outcome being served.
- **Lane**: portable fulfillment for a Job.
- **Ledger**: execution truth.
- **Gate**: fail-closed human authorization.
- **Memory**: fast episodic records plus slow gated durable knowledge.
- **Surface**: projection/input channel, never state.

Providers are workers. Control is a steering layer. OpenClaw is a front door or
worker unless a specific workflow elects it as orchestrator of record.

## Ownership

| Concern | Owner |
|---|---|
| Workflow run truth | Ledger |
| Human authorization | Gate contract |
| Durable memory promotion | Memory contract plus gate |
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

