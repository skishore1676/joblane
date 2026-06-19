# Operations

This first slice is local-only and sandboxed.

```bash
make check
python3 -m joblane.cli run chief_of_staff --root state/local
python3 -m joblane.cli run fitness --input lanes/fitness/fixtures/sample.json --root state/local
python3 -m joblane.cli companion-start reflection --root state/local
python3 -m joblane.cli companion-turn <session_id> --message "Remember that one workflow has one orchestrator." --root state/local
python3 -m joblane.cli ingest-surface --file surface-packet.json --root state/local
python3 -m joblane.cli render --root state/local
python3 -m joblane.cli board --root state/local
python3 -m joblane.cli due --root state/local
python3 -m joblane.cli tick --fixtures-dir lanes --root state/local
python3 -m joblane.cli providers --policy deployments/local.example/provider-policy.json --root state/local
python3 -m joblane.cli control-actions --root state/local
python3 -m joblane.cli control-intent experiment park --root state/local
python3 -m joblane.cli drawers --ensure --root state/local
python3 -m joblane.cli decide <run_id> <gate_id> approve --root state/local
python3 -m joblane.cli companion-close <session_id> --root state/local
python3 -m joblane.cli status --root state/local
```

State lives under the selected root. Rendered surfaces are projections and may
be deleted/re-rendered from the ledger.

Companion sessions currently support the memory-heavy Jobs: fitness,
chief-of-staff, and reflection. Their turns are local ledger state. Durable
memory candidates still appear as ordinary waiting gates.

A minimal surface packet looks like:

```json
{
  "surface": "obsidian",
  "external_id": "note-123",
  "intent": "companion_turn",
  "payload": {
    "session_id": "session:...",
    "message": "Remember that adapter inputs need provenance."
  }
}
```

The same contract can be used by Telegram, Apple Notes, Apple Messages, OpenClaw,
or any future surface adapter.

Schedules are lane-owned declarations. Use `joblane due` for readback:

```bash
python3 -m joblane.cli due --now 2026-06-19T17:00:00 --root state/local
```

This command does not install or mutate a scheduler.

Use `joblane tick` to execute due lanes once:

```bash
python3 -m joblane.cli tick --now 2026-06-19T17:00:00 --fixtures-dir lanes --root state/local
```

Tick renders local Markdown surfaces and writes a `runner_tick` receipt. It is
safe to call from cron or launchd later because the scheduling loop remains
outside the lane code and the runner still uses normal gates.

Use `joblane providers` to inspect which worker each lane actor resolves to:

```bash
python3 -m joblane.cli providers --policy deployments/local.example/provider-policy.json
```

The command is read-only. It lets a deployment flip workers without editing lane
packs.

Use Control Tower commands to inspect and record operator intents:

```bash
python3 -m joblane.cli control-actions
python3 -m joblane.cli control-intent experiment park --note "pause this packet"
```

Control intents are ledger rows. They do not execute the action directly.

Use `joblane drawers --ensure` to create the deployment-owned lane drawer tree:

```bash
python3 -m joblane.cli drawers --ensure --root state/local
```

This creates `state/local/lanes/<lane_id>/{inbox,work,products,archive}` and
does not write runtime files into lane source folders.
