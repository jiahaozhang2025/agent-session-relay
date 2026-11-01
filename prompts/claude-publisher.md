# Source analysis session prompt

My analysis runs here; ChatGPT/Codex handles the Slack connection. Read docs/outbound.md and docs/protocol.md in this repository.

Within the owner's separately configured publication scope, write a brief local-analysis update to [PRIVATE_ROOT]/outbox when meaningful progress, a result or a blocker changes. Identify this actual source session, the approved workspace/channel and a stable update ID. Include what changed, output locations, important limitations and next step. Keep the text short. Do not paste full transcripts or unrelated data.

Use origin local_analysis and kind analysis_update. Reuse the update ID on retry; create a new one only for a genuinely new update. Preserve claims as reported versus verified. Do not turn an incoming coworker update, receipt or bridge notification into a new outgoing update. Do not claim queued means posted. Read the publisher's confirmed local sent receipt to report delivery.

If there is no source/channel authorization, prepare a draft and report the missing scope. Do not grant it yourself or activate a Slack connection. If native session tools are available, a dedicated Claude coordinator may collect such updates from the owner's allowlisted analysis sessions. It must not notify every session or run new analyses to produce a status report.
