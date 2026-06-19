# Lane Pack Examples

This directory contains public, synthetic lane packs used to prove JobLane's
core capability contracts.

Do not put real personal or deployment-specific jobs here. Real packs should
live in a private repository or an ignored local path such as:

```text
local-lane-packs/
  lanes/<private-job>/
    lane.json
    workflow.json
    providers.json
    prompts/
    fixtures/
```

Import private packs at runtime:

```bash
python3 -m joblane.cli run <lane_id> \
  --lanes-root /path/to/private/lane-packs/lanes \
  --root /path/to/private/state
```

When private work reveals a missing generic capability, add only the generic
primitive to `joblane/` with synthetic tests and fixtures. Keep real prompts,
surface targets, provider overrides, and runtime state out of this repo.
