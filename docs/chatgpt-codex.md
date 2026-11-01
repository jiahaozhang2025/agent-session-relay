# Set up the ChatGPT/Codex receiver

## Discover and connect

Use the participant's own account. Verify a Slack connection to the intended workspace, and read one message in the selected channel. Workspace-wide approval of ChatGPT does not automatically connect every person's private chats or local Codex session. An invitation is needed for a private channel.

Read the authenticated Slack profile. Save its actual user ID as `owner_slack_user_id` in a private copy of config.example.json. Do not reuse a coworker's connection. Resolve the channel by ID; names can change.

For account and deployment requirements, see the [official connection guide](https://learn.chatgpt.com/docs/enterprise/chatgpt-slack-and-teams).

## Choose the runtime

**Codex desktop:** preferred when the participant wants to inform local Codex chats or write a shared inbox. Verify list/read/message tools. Create or reuse one incoming-coordinator chat. Store private state in a durable directory outside this checkout.

**ChatGPT web:** scheduled tasks can use available connected tools, subject to plan and workspace settings. Do not assume the web task can read/write local disk, list local Codex chats or notify Claude. If these tools are absent, receive in the web chat and prepare the handoff to an authorized local coordinator or accessible private storage.

The `@ChatGPT` assistant inside Slack, Slack connected tools in a personal chat, and local Codex are separate surfaces. Test the one you intend to use.

## Configure the receiver

Use [the receiver prompt](../prompts/receiver.md), substituting verified values. The owner must authorize informational notifications to their involved sessions. Default to no Slack replies and no automatic publication.

For the first run, use a human-selected start time. Do not ingest all channel history by default. Track newer roots and replies in relevant threads; Slack channel history alone is not a complete reply feed. Save a high-water mark plus pending retries, processed source IDs and thread watermarks. Read all pages before advancing past unseen records. Failed destinations remain pending even if the fetch cursor advances.

Use concrete identifiers to find candidate sessions, then read their relevant recent context. Do not route from title keywords alone. Do not notify a setup/coordinator chat about its own traffic. If there is no match, record that and retain the update for manual review or the Claude coordinator.

## Schedule and test

Test the prompt manually, then use the app's scheduling tools to run in the same receiving chat every six hours. Update a matching existing task. Keep its current settings unless the user changes them. Report the saved task ID and cadence.

Desktop tasks that require local files need the computer awake and the app running. Web tasks have different capabilities. Event-triggered tasks exist for eligible ChatGPT web/mobile accounts; they are optional, not required by this six-hour setup. See the [official scheduling guide](https://learn.chatgpt.com/docs/automations).

Verify an actual scheduled wakeup independently from a manual run. A shorter temporary test cadence requires the participant's agreement; restore six hours after the test. Alternatively wait for the next six-hour run.

## Claude bridge

Use a private directory accessible to the receiver and Claude, with `inbox/`, `receipts/`, and `state/` subdirectories. Pass its path privately. A filesystem can carry an update but cannot itself start an agent turn. Follow the [Claude guide](claude.md) to verify the wakeup mechanism and native session tools.
