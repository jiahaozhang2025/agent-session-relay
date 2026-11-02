# Retire the Codex receiver every 24 hours

This is opt-in and requires the owner's standing authorization to create fresh
top-level chats, move the existing relay to them, and archive superseded chats.
It reduces accumulated conversation context. It does not rotate Claude, change
approval policy, or guarantee a particular usage reduction.

Save this substituted procedure privately as `RECEIVER_ROTATION.md`, including
the bridge root, GitHub URL, existing automation ID and owner authorization.
Keep IDs, native evidence, work content and state out of GitHub.

## Durable age check

Deploy `receiver_rotation.py` beside `mailbox_worker.py`, `relay.py` and
`answers.py`. Initialize once on the owner's instruction:

```sh
python receiver_rotation.py init --state BRIDGE_ROOT/codex-state/receiver-rotation.json --current ACTUAL_THREAD_ID --automation-id EXISTING_AUTOMATION_ID --max-age-hours 24
```

Set the existing worker's optional `rotation_state_file` to that absolute path.
Restart only the verified worker. It checks the clock without a model and emits
one `receiver_rotation_due` hint per generation at or after the deadline. Normal
worker polling latency applies; app/network outages can delay the receiving turn.
Queue acceptance is not a completed rotation.

At the start of EVERY scheduled and native receiving turn, check rotation state.
A chat whose actual ID differs from `current_thread_id` stands down: no routing,
publication or retargeting. The predecessor may finish its own verified pending
retirement/archive bookkeeping. Recover pending handoffs before normal processing.
The existing scheduled tick is a fallback if a hint is lost; no new schedule.

## Handoff transaction

All commands below take `--state` with the same private absolute path.

1. Run `status`, then `begin --current OLD_ID`. Use `--force` only on an owner's
   immediate rollover instruction. The reservation is persisted BEFORE native
   creation. Existing pending reservations must be recovered, never duplicated.
2. Create one fresh top-level chat using the native create tool, not a fork.
   Pass a short pointer to private runbooks and standing scope, not the old
   transcript. Bind the actual returned ID with `bind --current OLD_ID
   --rotation-id ID --successor NEW_ID`. After an ambiguous creation result,
   locate the actual chat with native tools before any retry.
3. The successor bootstraps read-only: verify native identity, helper versions,
   files, configs, Slack access and native tools; write a private readiness
   record. Do not start jobs/workers, publish, switch targets or recursively
   rotate during bootstrap. Record unavailable capabilities honestly.
4. Pause the existing automation with its native scheduler. Verify executable,
   arguments and exact lock owner before stopping only the relay worker. After
   confirmed exit, remove only its stale lock if necessary. Preserve cursors,
   queues, retries, decisions, claims, original batch/chat IDs and sent receipts.
   Update worker target and receiver runbooks; exclude both old/new coordinators
   from relevance. Preserve Claude registrations, scope, approval gates,
   disabled analysis publication and the chosen polling interval.
5. Retarget and reactivate the SAME automation through its native tool, keeping
   the compact prompt. Verify ID, target, status and interval. Save actual
   readiness and target evidence privately. `activate --current OLD_ID
   --rotation-id ID --evidence FILE` requires `ready_thread_id`, `worker_thread_id`
   and `automation_thread_id` equal NEW_ID, plus the original `automation_id` and
   `automation_status: ACTIVE`. Start exactly one worker and verify its actual
   process, target and fresh status. Evidence fields are adapter attestations,
   not owner publication approval or independent cryptographic proof.
6. Verify a harmless worker probe reaches a separate native turn in the new
   chat. Probe handling sends nothing to Slack/Claude. If a stage fails, retain
   the transaction, report the blocker, and do not archive early or launch
   duplicate chats/workers. Uncertain Slack claims remain subject to their
   original reconciliation gates across the handoff.
7. Archive the predecessor with the native archive tool only after takeover is
   verified. Run `complete --current NEW_ID --rotation-id ID --evidence FILE`
   using the actual archive result (`archived_thread_id: OLD_ID`, `archived: true`).
   Preserve history. After interruption, the successor may finish bookkeeping
   using native verification. The next deadline is 24 hours after binding.
   Standing owner authorization covers later rotations without recurring
   approval requests. A leftover mutation lock requires checking that no live
   handoff owns it before recovery. The helper never creates/archives chats or
   edits a scheduler itself.
