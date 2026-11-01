# Private file-bridge state contract

Keep all these files outside GitHub. Names below describe the default installation layout; configure actual accessible Windows/Linux paths privately. All publication files are complete JSON written with temporary-file plus atomic replacement. Ignore `.tmp` files. One writer owns each queue/state file; coordinate takeover before changing targets.

## Installation and source progress

`receiver-config.json` contains the verified owner/workspace/channel IDs, bridge and state roots, inbox/receipt directory names, cadence overrides, excluded setup/coordinator chat IDs and answer/analysis policies. `folder-worker.config.json` follows the public example, with mailbox_enabled false, safe file/receipt directories, actual target thread ID and an installed supported queue-command argument array. Publisher and receiver copies of answer policy must agree; never choose the looser policy.

The exporter may use `codex-state/receiver-state.json`:

```json
{
  "schema_version": 1,
  "workspace_id": "TEXAMPLE",
  "channel_id": "CEXAMPLE",
  "channel_high_water": "1700000000.000001",
  "thread_watermarks": {"1699999999.000001": "1700000000.000001"},
  "processed_sources": {},
  "pending_codex_deliveries": []
}
```

Use separate state for each configured channel. Identity is workspace_id:channel_id:message_ts, with strings preserved. Record per-source outcomes and per-destination success independently. Advance fetch progress only after every item in the fetched range is durably exported/rejected or separately retained for retry. Never reset a watermark during adoption. Store a private exporter status with check time, actual page/thread coverage, counts and errors. Session IDs/titles and source text remain untrusted data.

The exporter status may include `run_result`: NO_UPDATE for a completed empty/non-actionable check, UPDATED for meaningful handled work, or NEEDS_ACTION for a failure/decision requiring attention. Retain the underlying counters/errors and retries. NO_UPDATE is a local status token, not a recurring chat message; missing data or a failed check cannot be reported as a successful empty check.

## Queues and receipts

| Path under bridge root | Contract |
| --- | --- |
| `slack-inbox/SOURCE_HASH.json` | `relay.py export` output: original normalized Slack metadata/text/link, source_id, thread_ts, origin slack_export, intended_consumer codex-router, visited slack-exporter. Source hash is SHA256 of source_id. Immutable on duplicate ingestion. |
| `slack-receipts/SOURCE_HASH.json` | Matching source_id and status processed, plus actual routing/queue outcomes or rejection reason. Never suppress pending failures without independent retry state. |
| `claude-inbox/SOURCE_HASH.json` | `relay.py enqueue` output using configured inbox directory; source provenance, Codex deliveries and codex-router visited hop. A write means queued only. |
| `claude-receipts/SOURCE_HASH.json` | Actual delivered/no_match/rejected result with source_id, native destinations and rationale. The watcher treats all three as finished. A question or new-work item is delivered once its brief message succeeds. Retryable failures remain pending. |
| `brief/items/SOURCE_HASH.json`, `brief/YYYY-MM-DD.md` | The analyst's classified item (fields in [the coordinator prompt](../prompts/claude-coordinator.md)) and the brief session's daily record. Slack text and session excerpts inside them stay untrusted. |
| `answers/drafts/ID.json`, `answers/decided/ID.json` | Managed by answers.py; approved decisions include actual owner words/event reference, configured brief ID and approved-text hash. See the answer contract. |
| `answer-outbox/HASH.json`, `answer-state/HASH.json`, `answer-sent/HASH.json` | Approved text, pre-send claim and confirmed receipt respectively. Managed by the existing publisher; native wakeup does not authorize a send. |

The generic helper defaults to inbox/receipts rather than claude-inbox/claude-receipts. Use the private directory-name settings consistently; do not rename a running Claude queue.

## Worker transport state

Under the configured worker state_root, `worker-state.json` stores stable events and batches. Each event has a kind, file/probe/source metadata, discovered_at and assigned batch_id. The worker saves `batches/BATCH_UUID.json` with batch_id, target thread_id, created_at and events before its one native queue submission. State marks queued_unconfirmed or submission_uncertain; neither is delivery. Never automatically resubmit an uncertain batch.

The receiver copies that batch to `codex-state/folder-pending/BATCH_UUID.json`, then uses `folder_worker.py ack` to save `receipts/BATCH_UUID.json`:

```json
{"batch_id":"BATCH_UUID","thread_id":"ORIGINAL_TARGET_CHAT_ID","status":"received","received_at":"UTC_ISO_TIMESTAMP"}
```

The worker validates a receipt against its original batch/chat even after target migration. Do not rewrite old receipts as if a new chat received them. Reconcile old pending batches before takeover. The pending copy records processing_status, per-event results and separate retries; transport receipt alone never finishes project routing or publication.

`worker-status.json` reports checked_at, pid, errors, newly observed hints and unconfirmed batch count. Verify the actual process and exact worker command too. `worker.lock` is the exclusive process lock; after an unclean exit, verify the old process is gone before removing only that lock.

## Harmless probe

If probe_directory is configured, create one UUID-named JSON there, atomically:

```json
{"kind":"worker_probe","probe_id":"PROBE_UUID","created_at":"UTC_ISO_TIMESTAMP"}
```

This is a distinct source kind, never a fabricated Slack question or approval. Its native receiving turn records `state_root/probe-receipts/PROBE_UUID.json` with probe_id, thread_id, received_at, delivery_mode, file_notification_verified, independently_idle_wakeup_verified and explanatory evidence. Use false for manual recovery or untested stages. Queueing during an active turn and receiving a subsequent turn verifies continuation; queueing while independently idle requires a separate actual test.

For a fresh top-level chat, keep a private target registration with its actual thread ID, prior coordinator ID, interval and verified repository commit. Keep readiness/takeover/probe status private. These are installation data; use the public exporter/receiver prompts as the reusable procedure.
