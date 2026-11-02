# Compact scheduled tick

Save the full substituted [exporter procedure](folder-exporter.md) in a private durable runbook first. Substitute its actual absolute path below, then save only this short text as the existing scheduled task prompt:

> Check the Slack file relay using BRIDGE_ROOT/FOLDER_EXPORTER.md and saved state. If nothing actionable changed, record NO_UPDATE locally and stay quiet. Report meaningful delivery, failure, or required owner action.

The scheduler holds the chosen interval and destination chat. Keep account/scope/approval/routing/recovery details in the runbook and private configs; do not append the whole setup history or handoff report to each tick. A short prompt still starts an agent check at the configured cadence. Missing runbooks or failed checks are failures, not NO_UPDATE.

When the owner enables [daily receiver rotation](../docs/receiver-rotation.md),
the private exporter checks durable receiver age/target before normal work.
Keep that procedure in the runbook; the compact tick stays unchanged.
