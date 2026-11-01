# Optional local file helper

Python 3.10+; no packages, credentials, Slack SDK, server or network calls.

An authorized transport adapter obtains real metadata, checks session relevance, and writes a normalized message JSON privately. This helper filters identity/scope and queues a copy for Claude. It does not implement the transport adapter, scheduling, cursors, session matching, delivery or a delivery ledger. Those responsibilities stay with the coordinator described in the guides.

Copy config.example.json to a private location and fill it. Set `inbox_root` to the private directory accessible to both coordinators. Only one coordinator may write a given owner/channel queue at a time.

```sh
python scripts/relay.py filter --config /private/config.json --message /private/candidate.json
python scripts/relay.py enqueue --config /private/config.json --message /private/candidate.json
python scripts/relay.py watch --config /private/config.json --once
python scripts/relay.py watch --config /private/config.json
```

The long-running watcher checks files every 30 seconds but emits a line only for a new pending source. Connect its stdout to a supported native agent Monitor integration to wake an agent; running this command in a plain shell does not do that by itself. Restarting the watcher re-emits items without receipts so an interrupted delivery can be retried.

Write local receipts to `receipts/` using exactly the corresponding inbox filename, after delivery or a confirmed no-match result. Receipts must be valid JSON objects recording source ID, outcome and per-destination results. Keep retryable failures in separate state and do not mark them complete. The helper ignores receipted items; it does not generate receipts.

Input text is never executed. Queue filenames are hashes of source identity, not sender-supplied paths. Existing queue entries are not changed on duplicate ingestion. Keep failed writes pending in the transport coordinator.

## Outgoing analysis updates

Use `outbox.py` for the reverse file queue. Copy the owner's source/channel authorization into the private config's `outbound` section; publication defaults to disabled. A draft may be queued before publication is enabled.

```sh
python scripts/outbox.py queue --root /private/bridge --update /private/analysis-update.json
python scripts/outbox.py prepare --root /private/bridge --config /private/config.json --update /private/analysis-update.json
```

`prepare` checks the source/channel policy and a confirmed sent receipt, then returns `prepared_not_sent`. It does not call Slack or inspect an in-flight ledger. The publishing agent must perform the ledger/ambiguity checks, actual send and confirmed receipt handling in [the outbound guide](../docs/outbound.md). The helper cannot guarantee exactly-once transport delivery. Use one writer per update ID.
