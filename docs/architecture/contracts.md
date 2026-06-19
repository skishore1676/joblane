# Contracts

## Ledger

The ledger records execution truth: runs, artifacts, gates, decisions, receipts,
memory, provider calls, and surface references. Deleting rendered surfaces must
not delete state.

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
