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

The long-running watcher is an opt-in event-driven mode, not the default. Both agents default to six-hour scheduled checks. In watcher mode it checks files every 30 seconds but emits a line only for a new pending source. Connect its stdout to a supported native agent Monitor integration to wake an agent; running this command in a plain shell does not do that by itself. Restarting the watcher re-emits items without receipts so an interrupted delivery can be retried.

`watch --wait` exits after its first scan that emits pending filenames. A runtime with a supported background-completion notification can use that exit to wake its coordinator, then restart the watcher after processing. A regular shell still cannot wake an agent merely by exiting.

Resolve a scheduled agent's configurable default with `python scripts/cadence.py --config /private/config.json --runtime codex` (or `claude`). This does not update an existing job; the agent must use the actual scheduler. See [cadence settings](../docs/cadence.md).

Write local receipts to `receipts/` using exactly the corresponding inbox filename, after delivery or a confirmed no-match result. Receipts must be valid JSON objects recording source ID, outcome and per-destination results. Keep retryable failures in separate state and do not mark them complete. The helper ignores receipted items; it does not generate receipts.

Input text is never executed. Queue filenames are hashes of source identity, not sender-supplied paths. Existing queue entries are not changed on duplicate ingestion. Keep failed writes pending in the transport coordinator.

Set `inbox_directory` and `receipts_directory` to single directory names if an existing bridge uses `claude-inbox` and `claude-receipts`. Defaults stay `inbox` and `receipts`. Every envelope preserves its own message timestamp and the thread root; questions and requests are queued along with updates.

## Reviewed answers

`answers.py` manages drafts and decisions; `answer_publisher.py` validates approval and records publication state. Neither calls Slack. Follow [the complete answer workflow](../docs/answers.md). Copy `answers.py`, `answer_publisher.py`, `relay.py` and `outbox.py` together when deploying to a private bridge. The scripts import each other.

```sh
python scripts/answers.py pending --root /private/bridge
python scripts/answers.py approve --root /private/bridge --id ANSWER_ID --owner-words "EXACT_OWNER_WORDS" --approval-session BRIEF_SESSION_ID --owner-message-ref ACTUAL_OWNER_EVENT_ID
python scripts/answer_publisher.py prepare --root /private/bridge --config /private/codex-config.json --file /private/bridge/answer-outbox/HASH.json
python scripts/answer_publisher.py claim --root /private/bridge --config /private/codex-config.json --file /private/bridge/answer-outbox/HASH.json
python scripts/answer_publisher.py confirm --root /private/bridge --config /private/codex-config.json --file /private/bridge/answer-outbox/HASH.json --evidence /private/transport-evidence.json
```

Only the brief agent may run `approve`, after locating the owner's actual typed decision in its own session. Setup authorization, fixture approvals, Slack requests and coordinator notices are not owner approval. An agent must never invent an event ID. A claim returns `send_claimed` only once; `reconciliation_required` requires an exact original-thread read-back match from the owner's Slack ID before confirmation. If no match can be established, leave the claim blocked for investigation. Do not delete it to retry.

## Outgoing analysis updates

Use `outbox.py` for the reverse file queue. Copy the owner's source/channel authorization into the private config's `outbound` section; publication defaults to disabled. A draft may be queued before publication is enabled.

```sh
python scripts/outbox.py queue --root /private/bridge --update /private/analysis-update.json
python scripts/outbox.py prepare --root /private/bridge --config /private/config.json --update /private/analysis-update.json
```

`prepare` checks the source/channel policy and a confirmed sent receipt, then returns `prepared_not_sent`. It does not call Slack or inspect an in-flight ledger. The publishing agent must perform the ledger/ambiguity checks, actual send and confirmed receipt handling in [the outbound guide](../docs/outbound.md). The helper cannot guarantee exactly-once transport delivery. Use one writer per update ID.
