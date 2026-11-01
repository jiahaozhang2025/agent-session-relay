# Verify an installation

Run these checks using a private test channel and a harmless project marker. Do not send test messages without the user's authorization.

1. **Identity:** each participant resolves their own actual Slack user ID. The same provider app approval can exist for both; their connections and identities must still be correct.
2. **Self-message:** an owner's ordinary post and AI-generated post under their identity are both skipped before session lookup. Neither creates a Claude inbox file or Slack reply.
3. **Coworker message:** a real peer posts a harmless update. Verify sender metadata, source link, scope, relevance decision and a single local inbox file.
4. **Duplicates and loops:** rerun the check. No repeated destination notice, duplicate inbox item or Slack acknowledgment appears. Receipt-only posts are skipped even when a peer sent them.
5. **Codex relevance:** a concrete project marker reaches one authorized matching working chat, not unrelated chats or the coordinator. If no delivery tools exist, record this stage unavailable.
6. **Scheduled wakeup:** let the saved schedule run while the receiver is idle. Check the actual run, not merely the task's existence. Keep the normal cadence at six hours unless the user authorizes a temporary change.
7. **Claude delivery:** separately verify queue creation, wakeup, session matching and native delivery. A plain shell watcher without a native agent event bridge only watches files. Mark this stage pending until the recipient session contains the notice.
8. **Restart and failure:** restart the receiver and confirm the durable cursor/history. Failed deliveries remain retryable; successful ones are not repeated. Never start a second coordinator while the first is still processing.

Report each stage as verified, pending, unavailable or failed. Include task IDs and private output locations only in the participant's own chat. Do not store installation evidence in the public repository.

The helper checks can run offline:

```sh
python -m unittest discover -s tests -v
```
