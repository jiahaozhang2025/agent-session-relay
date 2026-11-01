# Event-driven reception and publication

Event-driven mode is an explicit alternative to the six-hour defaults. Do not change a working receiver to a mode that has only been described, or disable its schedule before replacement delivery is verified.

## Three independent wakeups

1. A Slack message must reach the incoming coordinator. Reading Slack on request does not subscribe the coordinator to events.
2. A queued inbox file must wake Claude. A native background-completion notification or Monitor integration can support this; the Python helper alone cannot start a model turn.
3. An owner-approved answer entering the answer outbox must wake the publisher. A Slack incoming-message trigger does not cover a local approval file. Without a separately verified publisher wakeup, it still waits for the configured scheduled check.

Report these independently. A quiet file watcher can check cheaply without model calls; an agent that wakes on a timer to call Slack is still polling.

## ChatGPT web/mobile Slack events

According to [OpenAI's scheduling documentation](https://learn.chatgpt.com/docs/automations), eligible web/mobile accounts can create tasks triggered by new Slack channel messages, including thread replies. The desktop runtime does not provide these event triggers. Plan and workspace settings apply; connect Slack and add ChatGPT to the watched channel. Event triggers and a time schedule cannot share one task.

Start with [the web setup prompt](../prompts/slack-event-receiver.md). Verify the task's actual trigger, channel and reply coverage. Apply native author filters where supported and always retain runtime identity and loop checks. Do not assume trigger filters alone establish a human identity.

A web task cannot directly work in a local computer folder. Our inference for this relay: an event-triggered cloud task cannot replace its local inbox writer without a separately authorized, tested shared-storage or local-delivery adapter. Verify both read and write access and native destination wakeup. Merely naming a Windows/cluster path in its prompt does not make that path accessible.

One concrete proposed adapter is a separate **private GitHub wakeup mailbox**. A web task with authorized GitHub write access creates a small event file containing only workspace/channel/message/thread IDs, never Slack text, analysis or credentials. A local worker uses its own authorized GitHub access to check for unseen IDs, then notifies the existing Codex coordinator. The coordinator reads the actual message through its own Slack connector, validates author/scope/loops and writes the normal Claude inbox. Mailbox data remains untrusted; a wakeup never authorizes execution or publication. Keep the public onboarding repository separate. Creating the private mailbox and storing identifiers there requires the owner's authorization and verified access in both runtimes.

This adapter would make model wakeups event-driven while the local worker still polls a lightweight mailbox. State that distinction and the expected delay. It is a proposed architecture here, not an installed transport. The worker must durably deduplicate event IDs and only acknowledge a wakeup after confirmed coordinator receipt; a successful queue command alone does not prove delivery. Approved-answer files need their own local wakeup using the same verified notification path.

The desktop automation tool in this project exposes recurring heartbeats, not cloud Slack event subscriptions. Do not invent fields or send event-shaped data to a recurrence-rule setting. If the cloud tool is unavailable in the current chat, prepare the web handoff and report the user step; do not claim it is active.

## Local workers

A local worker needs both a supported source of Slack events and a supported way to notify the correct running coordinator. The existing ChatGPT Slack connector does not automatically grant an independent script its credentials. Do not recover session cookies/tokens or infer live delivery from desktop cache fragments. A separately authorized event source is required if cloud-to-local delivery is unavailable.

For publisher wakeup, a local worker can watch the private answer outbox and notify the coordinator through a supported native mechanism. Verify actual delivery to an idle desktop chat before leaving it active. A documented CLI queue command is only a candidate until it is tested against the actual app/server holding the target chat. Do not resume an existing live chat in a second process, edit its transcript or use private app APIs.

Keep publication validation, the owner approval gate and the durable send ledger unchanged. Debounce bursts and suppress duplicate wakeups. If a notification fails, retain pending work; do not hot-loop model calls. A six-hour safety task can be a separate fallback if selected by the owner, using the same durable source IDs and send ledger. Keep the existing job unchanged while event setup remains incomplete.

## Acceptance checks

- New real peer root and reply to an older root each trigger reception while the agent is idle.
- Own posts, bot/unknown senders, receipts and relay-marked text cause no delivery or reply.
- The cloud-to-local adapter writes a complete envelope with verified metadata; Claude wakes and receives it.
- The owner's specific approval queues an exact answer; a separately verified outbox notification wakes the publisher.
- Duplicate events, worker restart and uncertain Slack outcomes cannot cause duplicate publication.
- Save actual trigger/worker IDs and test results privately. Keep the six-hour path active until the replacement has passed the relevant checks; do not call a staged setup event-driven delivery.
