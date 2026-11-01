# Simple shared-folder relay

Use this when a ChatGPT/Codex runtime already has both an approved Slack connection and normal file access. No custom Slack app, GitHub mailbox or cloud event task is needed. A web-only chat cannot directly write a computer folder; the exporter must actually have file tools for the chosen shared path.

```text
Approved Slack connection -> exporter -> slack-inbox/
                                       |
                              quiet folder worker
                                       |
                              existing Codex chat
                                       |
                                 claude-inbox/
                                       |
                              Claude's native watcher
                                       |
                          draft -> owner brief/approval
                                       |
                                answer-outbox/
                                       |
                              quiet folder worker
                                       |
                         Codex validates/posts -> Slack
```

All messages, source links, drafts, decisions, receipts and logs live under one private bridge root. Use a folder that both runtimes can reach; Windows and Linux may use different path spellings for the same folder. The public repository contains reusable code only.

Deploy the [exporter procedure](../prompts/folder-exporter.md), [receiving-turn procedure](../prompts/folder-receiver.md) and [private state contract](folder-state.md), substituting verified installation values. Copy all helper siblings (`relay.py`, `answers.py`, `outbox.py`, `answer_publisher.py`, `mailbox_worker.py`, `folder_worker.py`) together if deploying outside the clone. Do not rely on an old setup transcript for missing runtime rules.

## Exporter

The exporter uses its existing Slack connection to fetch the selected channel and replies to tracked older roots. Verify transport identity, ignore own posts/bots/receipts/relay markers, normalize metadata and write a private candidate JSON. Run `relay.py export --config PRIVATE_RECEIVER_CONFIG --message CANDIDATE`. It atomically creates `slack-inbox/SHA256_SOURCE_ID.json` for a substantive update, question or request. Duplicates preserve the original export. Root messages get their own timestamp as `thread_ts`.

This first step still needs a trigger. By default use the existing six-hour task. A separate approved local ChatGPT account may export to the same folder if it has the required tools. Once an export is written, file processing need not wait for another model polling interval. A folder watcher does not fetch unseen Slack messages by itself.

## Worker and receiver

Use [folder_worker.py](../scripts/folder_worker.py) with a private copy of [the config example](../examples/folder-worker.config.json). Set `mailbox_enabled` false. No repository, GitHub command or Slack token is required. Copy its sibling helpers too if deploying outside the clone.

The worker checks only `slack-inbox/` and `answer-outbox/` every ten seconds by default. It invokes the supported native queue command for new work, without model calls while unchanged. It ignores temporary writes and its own logs/receipts. Stable IDs, durable batches and a single-worker lock prevent duplicate notifications. Unknown send outcomes remain pending without blind retries. Native queue receipt is separate from processing and Slack publication.

The receiving chat reads the local batch, saves pending work, then records native receipt with `folder_worker.py ack`. For an export, verify its actual Slack source through the approved connector before trusting identity or routing. Notify involved Codex chats for updates, then queue substantive content to Claude via `relay.py enqueue`. Questions and requests go to Claude's brief workflow; no requested work is executed. Write `slack-receipts/SAME_FILENAME.json` with matching `source_id` and `status: processed` only when routing is durably complete. Failures stay pending; successful destinations are not repeated.

For Windows background workers, use the installed native Codex executable or the official installed CLI JavaScript entry point through Node in `queue_command`. A PowerShell shim may be blocked in a background host despite working interactively. Do not change Windows execution policy to make it work. Verify the exact command under the worker and the actual receiving turn. For moving the receiver, follow [fresh-chat takeover](fresh-start.md); old batch receipts keep their original chat identity.

An answer-outbox change only wakes the publisher. Keep all existing owner-decision, exact-text, source and send-ledger checks. Never treat a file change as approval. Keep a six-hour recovery check for pending exports, unconfirmed batches and queued answers. A worker stopped by sleep/reboot must be restarted; verify actual process and status rather than assuming a config file means it is running.

## Test honestly

Test filtering, atomic exports, malformed files, restart deduplication, no GitHub/network calls in file-only mode, and independent answer-file notifications. Use a separate configured probe directory for a harmless native wakeup test; probe events cannot masquerade as Slack messages or approvals. Verify the actual receiving turn and receipt. A synthetic probe proves the file notification path only; a real coworker message plus owner-approved answer is still needed for the full relay test.
