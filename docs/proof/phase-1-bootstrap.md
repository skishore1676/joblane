# Phase 1 Bootstrap Proof

Status: first green local slice.

What exists:

- public-generic repo skeleton
- ledger, gate, memory, surface, provider, control modules
- six Job tracer-bullet lanes
- lane-pack metadata under `lanes/*/lane.json`
- sandbox-only local deployment example
- doctor/readback command
- approved-gate effect bridge for local draft staging and gated memory promotion
- one-shot deployment runner for due lane packs and local surface rendering
- lane-local provider defaults plus deployment provider-policy overrides
- generic Control Tower action allowlists and validated control intents
- deployment-owned runtime drawers outside lane source folders

Current proof commands:

```bash
make check
python3 -m joblane.cli run-all --root state/dev
python3 -m joblane.cli run-all --fixtures-dir lanes --root state/dev-fixtures
python3 -m joblane.cli render --root state/dev
python3 -m joblane.cli doctor --root state/dev
python3 -m joblane.cli scorecard --root state/dev
python3 -m joblane.cli due --root state/dev
python3 -m joblane.cli tick --fixtures-dir lanes --root state/dev
python3 -m joblane.cli providers --policy deployments/local.example/provider-policy.json
python3 -m joblane.cli control-actions --root state/dev
python3 -m joblane.cli drawers --ensure --root state/dev
python3 -m joblane.cli proof --root state/proof --output out/proof/joblane-proof.json
python3 -m joblane.cli export-openclaw-skills
```

Current scorecard semantics:

- 80+ = useful tracer bullet, not finished product
- 60 = partial
- 40 = skeleton
- below 40 = concept

The score includes artifact acceptance checks, not only substrate existence. The
first target is to move every Job to at least useful-tracer. The later target is
to make those useful tracers real enough for daily use.

Protected-gate statement:

- no live sends
- no live public publish
- no broker/trading mutation
- no auth/secret mutation
- no oldmac cutover
