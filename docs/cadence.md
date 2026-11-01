# Six hours by default, configurable per agent

Both Codex and Claude default to a scheduled check every **six hours**. This applies to incoming routing, Claude coordinator checks/collection of authorized analysis updates, and the Codex outbox publisher. Queue writes may happen when work completes, but ordinary agent checks use the configured cadence. Instant event-driven monitoring is an optional user-selected mode, not the default.

The private configuration has a shared default:

```json
{
  "cadence_hours": 6,
  "cadence_overrides_hours": {},
  "claude_wakeup_mode": "scheduled"
}
```

To change both agents, set `cadence_hours` to the desired number of hours. To change only one, add its override:

```json
{
  "cadence_hours": 6,
  "cadence_overrides_hours": {"claude": 2},
  "claude_wakeup_mode": "scheduled"
}
```

This example keeps Codex at six hours and checks Claude every two hours. `codex` can also have an independent override. Remove an override to inherit the shared setting again. An existing user-selected interval takes precedence over the default; never reset it during upgrades.

An agent can check its effective interval with the optional helper:

```sh
python scripts/cadence.py --config /private/config.json --runtime codex
python scripts/cadence.py --config /private/config.json --runtime claude
```

The helper only resolves a value. Editing JSON does **not** reschedule an already-created job. On a human-requested change, update the existing Codex task and/or Claude job through that runtime's scheduling tools, verify the saved effective interval, and report it. Do not create a duplicate job. If the requested interval is unsupported, explain the limitation instead of silently substituting a different interval.

Claude's default can use `/loop 6h` where supported; a custom interval must replace that example. Check the job lifetime and expiry in the actual runtime. Native Monitor/channels mode is opt-in; when enabled, it replaces the corresponding scheduled inbox check. The file watcher's 30-second filesystem scan is only for that optional mode and is not the default model-check cadence.

With sequential six-hour Codex and Claude checks, an incoming update can take roughly twelve hours plus execution time to reach a Claude working session. Users can shorten one interval or explicitly choose event-driven monitoring if they prefer.

`claude_wakeup_mode` records the owner's choice and does not change a job: `scheduled`, or `event_driven_with_daily_safety_check` for the [Claude Code watcher](claude.md#event-driven-wakeup-in-claude-code). See [event-driven setup](event-driven.md) before switching. Slack reception, Claude inbox wakeup and approved-answer publication need separate verified event paths. Keep the working schedule while an event replacement is incomplete; do not relabel polling as event-driven.
