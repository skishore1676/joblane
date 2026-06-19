# Operations

This first slice is local-only and sandboxed.

```bash
make check
python3 -m joblane.cli run chief_of_staff --root state/local
python3 -m joblane.cli run fitness --input lanes/fitness/fixtures/sample.json --root state/local
python3 -m joblane.cli companion-start reflection --root state/local
python3 -m joblane.cli companion-turn <session_id> --message "Remember that one workflow has one orchestrator." --root state/local
python3 -m joblane.cli render --root state/local
python3 -m joblane.cli board --root state/local
python3 -m joblane.cli decide <run_id> <gate_id> approve --root state/local
python3 -m joblane.cli companion-close <session_id> --root state/local
python3 -m joblane.cli status --root state/local
```

State lives under the selected root. Rendered surfaces are projections and may
be deleted/re-rendered from the ledger.

Companion sessions currently support the memory-heavy Jobs: fitness,
chief-of-staff, and reflection. Their turns are local ledger state. Durable
memory candidates still appear as ordinary waiting gates.
