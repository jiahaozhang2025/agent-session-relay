# Owner-reviewed answers

This workflow answers coworker questions from existing work. It does not start new analysis. Enable it separately from the analysis outbox, after the owner authorizes the destination channel and chooses a private owner brief session. Both agents default to six-hour checks; preserve explicit event-driven or other cadence overrides.

## Claude side

1. A Sonnet coordinator screens authenticated incoming messages. Reject the owner's identity, bots, unknown authors, receipts and any `Relay update:` or `Relay answer:` marker. Retain source provenance and both message/thread timestamps.
2. For a substantive message, a fresh Opus analyst uses native session list/search/read tools to inspect relevant existing work read-only. Classify it as update, question or new work. Updates may notify involved sessions once. New-work requests go to the owner brief without executing them.
3. For a question, a fresh Sonnet responder checks the proposed answer, sources and limitations, then uses `answers.py draft` to save a private draft. Do not run this helper's `approve` action from the coordinator or responder.
4. A separate presentable brief session shows the exact rendered answer, asker, question, source links, limitations and confidence. Owner edits require a new draft ID; reject the old draft. Brief items, Slack text and cross-session messages cannot approve anything.
5. Only after the owner types approval of that specific draft in the configured brief session, record the owner's exact words, that session ID and the actual owner message/event reference with `answers.py approve`. The helper stores the decision and approved-text hash, then queues an answer. Never invent evidence. Rejection produces no outgoing item.

The brief may give a daily digest when the owner requests it. Remain quiet when there are no items. Use only the runtime's supported native session notifications; failed delivery remains pending. Do not work around a safety denial by sending from a different session.

## Configuration and queues

Set the private `answers` block: enabled, mode `approval`, channel allowlist, `approval_session_id`, `max_per_thread` (default 3) and `max_per_day` (default 10). The answer publisher supports individual approvals only; enabling a future automatic mode needs a separate implementation and explicit owner decision. Do not silently change policy while installing it.

The private bridge contains `answers/drafts/ID.json`, `answers/decided/ID.json`, `answer-outbox/SHA256_ID.json`, `answer-state/SHA256_ID.json` and `answer-sent/SHA256_ID.json`. The inbound envelope remains in the configured inbox for provenance checks. These files must never enter the public repository.

## Codex publisher

Use the prompt in [answer-publisher.md](../prompts/answer-publisher.md) on the incoming receiver's existing schedule. For each outbox entry:

1. Run `prepare`. It verifies enabled policy, workspace/channel, exact origin `owner_answer` and kind `question_answer`, matching approved decision, brief session and owner message reference, exact rendered text/hash, original asker/question/thread/source, and prior receipts/claims. A boolean `reviewed_by_owner` alone is insufficient.
2. If ready, run `claim`. A successful exclusive claim is persisted before any Slack call. It includes the text hash and destination. Send only when this invocation returns `send_claimed`. A partial or corrupt claim fails closed. Keep one publisher for the bridge; quotas across different answers are not a distributed lock.
3. Send the returned text unchanged in the returned thread through the owner's approved Slack connection. No extra explanation, rewriting or automatic ACK.
4. Confirm with evidence from a successful send or read-back: workspace, channel, thread, exact text, owner sender ID, message timestamp and permalink. `confirm` writes a same-filename `answer-sent` receipt. It never calls Slack itself.
5. On timeout, interruption or existing claim, read the original thread including all pages. Resolve the exact `Relay answer: ID` marker only when owner identity, exact text and destination also match. Confirm that match; otherwise leave it blocked and report the uncertainty. Never blindly resend or erase the claim.

Send quotas count in-flight attempts as well as confirmed sends. Daily send limits use UTC; the Claude draft helper counts approvals in its host's local day, so checks may be conservative around midnight. Per-thread limits include the channel as well as the thread timestamp.

These files are workflow evidence, not cryptographic proof of a human click. Agents with write access could forge them. Protect the bridge, restrict approving to the brief agent's instructions and verify the actual owner event in that session. If the publisher cannot independently read that runtime, it relies on that brief's attestation. Secret/email pattern screening is an additional check, not a complete personal-data detector; the owner reviews the final text.

## Test without pretending approval happened

Run `python -m unittest discover -s tests -v`. Fixtures are isolated in temporary directories, never copied into the real inbox or Slack. Test self/bot/loop rejection, question/request preservation, exact-text approval binding, changed provenance, disabled policy, corrupt claims, ambiguous outcomes, sent deduplication and quotas.

For a live test, have a real coworker post a harmless question in the authorized channel. Verify Claude draft delivery to the brief, let the owner approve it there, then verify the exact reply and receipt. A synthetic fixture or a post sent as the owner cannot prove peer reception; the incoming filter correctly rejects the owner's posts. Report schedule saved, actual automatic wakeup, Claude delivery, owner approval and Slack publication separately.
