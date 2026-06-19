# OpenClaw Boundary

OpenClaw can be a conversational front door and worker runtime. JobLane remains
the orchestrator of record for the default lane packs in this repository.

The safe handoff is a front-door packet:

```json
{
  "lane_id": "reflection",
  "requested_by": "openclaw",
  "namespace": "weekly",
  "observations": [
    {"key": "obs-1", "value": {"text": "episodic fact"}, "sensitivity": "private"}
  ],
  "proposed_memories": [
    {"kind": "takeaway", "memory": {"text": "durable candidate"}, "sensitivity": "internal"}
  ]
}
```

JobLane records observations as fast memory. Proposed durable memories become
candidates behind a human gate. The front door cannot directly approve, publish,
or mutate slow memory.

Generate or install OpenClaw skills with:

```bash
python3 -m joblane.cli export-openclaw-skills
python3 -m joblane.cli install-openclaw-skills --target-dir /path/to/openclaw/workspace-main/skills
```

Installation writes skill source files only. It does not restart OpenClaw or
change live runtime routing.

If a future workflow is OpenClaw-orchestrated through Task Flow or Lobster, that
workflow must declare OpenClaw as orchestrator of record and JobLane must not run
a competing scheduler/gate loop for it.
