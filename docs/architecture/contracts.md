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

JobLane-orchestrated packs also declare an `execution` block. The block is a
small, declarative sandbox recipe for the current local runner:

- `memory_fast`: optional fast-memory writes.
- `memory_candidate`: optional gated slow-memory proposal.
- `artifact`: artifact id/kind/content source and sensitivity.
- `gate`: optional content-bound human gate.
- `receipts`: optional non-gated proof receipts.
- `companion`: optional namespace/kind metadata for companion-mode packs.
- `status`: terminal run status after the sandbox step, usually `waiting` or `done`.

The execution block is intentionally narrow. It is not a general programming
language; provider calls and richer domain logic can be added as worker steps
later, but the host must still load behavior from the lane pack or a declared
worker, not from hardwired lane branches.

## Schedule

A lane pack owns its portable schedule declaration in `lane.json`. Supported
kinds are `manual`, `daily`, `weekly`, and `interval_hours`. The schedule
contract answers due/not-due with reasons from lane metadata plus the ledger's
last run time. It does not mutate cron, launchd, or any external scheduler.

## Drawer

A lane pack declares its drawer contract in `lane.json`; deployment state owns
the actual folders. The standard drawers are `inbox`, `work`, `products`, and
`archive` under `state/lanes/<lane_id>/`. Runtime drawer contents must not live
inside source lane folders.

## Runner

The deployment runner is a one-shot local executor. A tick may run due lanes,
render sandbox surfaces, and write a `runner_tick` receipt. It must route every
lane through the normal runtime and must not bypass gate validation or perform
live external effects.

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

## Surface Inbox

External adapters submit typed packets to the surface inbox. Each packet needs a
`surface`, an idempotency `external_id`, an `intent`, and an object payload. The
current generic intents are:

- `companion_turn`
- `frontdoor_packet`
- `lane_run`

The inbox records accepted and rejected packets. It deduplicates by
`surface + external_id` so retries do not double-run a lane or duplicate a
companion turn. Routing a packet may create runs, fast memory, candidates, or
gates, but it may not perform live external effects.

## Provider

A provider returns structured work for a role. A provider may be deterministic,
OpenClaw, Claude, Codex, a local script, or a future runtime. Provider failure
may cascade; a valid semantic verdict must not be rerolled.

Lane packs declare portable actor defaults in `providers.json`. Deployments may
override those defaults through `provider-policy.json`. Resolution order is:

- deployment lane actor override
- deployment lane default
- deployment global default
- lane-pack actor default
- lane-pack default
- built-in deterministic default

Failover chains are ordered. Infra failure cascades to the next layer; a
successful provider result with a negative outcome such as `revise` is still a
valid result and must not be rerolled.

## Control

Control reads ledger state and writes validated intents. Each lane declares
`allowed_control_actions` in `lane.json`; unknown actions fail closed. A control
intent may target a lane or a specific run owned by that lane. Control never
mutates workflow state directly and never bypasses gates.
