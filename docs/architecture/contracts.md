# Contracts

## Ledger

The ledger records execution truth: runs, artifacts, gates, decisions, receipts,
memory, provider calls, and surface references. Deleting rendered surfaces must
not delete state.

## Workflow

A lane pack owns a `workflow.json` file. The default schema is
`joblane.workflow.v1`: stable id, version, orchestrator, stages, gates, and
live-effect declaration. A gated workflow must declare content-bound gates with
allowed decisions. Default lane packs may not enable live effects.

## Gate

A valid gate decision must:

- address the expected `gate_id`
- choose exactly one allowed decision
- match the expected action fingerprint
- bind to the approved artifact hash when content matters

Approved gates may trigger durable effects only through the runtime effect
bridge. Current sandbox effects are:

- draft packet staging to a local outbox
- durable memory promotion from a pending candidate
- local commitment receipt
- local experiment staging receipt

Reject, revise, park, or skip decisions do not perform the approved effect.

## Memory

Fast memory is append-only and gate-free. Slow memory is durable and promoted
only by `propose -> decide`. Private or unknown sensitivity fails closed for
publishing.

## Companion Session

A companion session is bounded interaction state for lanes that need more than a
single input packet. The ledger records the session, the attached run, every
turn, and any proposed durable memory. A companion session may write fast memory
without a gate. It may not write slow memory directly, perform a live effect, or
close a human gate on behalf of the human.

Approving a companion memory gate promotes only the bound candidate. It does not
close the companion session; the session remains active until explicitly closed
or until its turn budget is exhausted.

## Surface

A surface may publish a view and ingest human input. It must not authorize an
effect without gate validation and must not become state.

## Provider

A provider returns structured work for a role. A provider may be deterministic,
OpenClaw, Claude, Codex, a local script, or a future runtime. Provider failure
may cascade; a valid semantic verdict must not be rerolled.

## Control

Control reads ledger state and writes validated intents. It never mutates
workflow state directly and never bypasses gates.
