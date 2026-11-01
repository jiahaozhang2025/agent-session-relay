# Verify from a fresh top-level chat

Use a new user-owned chat, not a subagent or a fork of the setup conversation. Give it the GitHub URL, the private installation root, the selected interval and authorization scope. Do not pass the old transcript or treat a past report as a successful test.

## Independent bootstrap

1. Fetch or clone the current remote default branch into the fresh chat's own directory. Read README.md, AGENTS.md, folder-bridge.md, protocol.md, answers.md and the applicable runtime guide from that checkout. Record the fetched commit. Run the helper tests there.
2. Use private configs, cursors, ledgers and registrations as installation data. Verify actual Slack/profile access, root/reply coverage, folder access, native queue command, worker process and saved automation. Apply the human's interval override; never reset it to the public six-hour default.
3. Do not install a second exporter, watcher or schedule. Preserve source IDs, inboxes, decisions, sent claims/receipts, Claude coordinator and brief registration. Publication still requires the original authorized approval policy. Real workspace and session IDs stay private.

## Take over an existing installation

Only when the owner authorizes takeover, resolve the new chat's actual ID through native tools or an owner-created local target record. Verify readiness before modifying the active target.

1. Identify the one current automation and worker. Reconcile any old unconfirmed notifications and preserve pending source work. Do not fabricate delivery or reset uncertain sends. A worker's old receipts remain bound to each original batch/chat.
2. Pause the existing exporter briefly for the handoff. Stop only the verified relay worker process; check executable/command line and its exact lock owner. Preserve all state. If a terminated process leaves its lock, confirm exit before removing only that lock file. Do not change system execution policy.
3. Update the worker's target chat ID and private receiver instructions. Keep ownership, workspace/channel allowlists, cadence overrides and answer policy unchanged. Deploy helper versions from the verified checkout. Restart one worker, check its actual process/status and update the existing automation's target and prompt to the new chat. Reactivate that same job; do not create a duplicate. Exclude both the old setup chat and the new coordinator from working-session relevance matching.
4. On Windows, configure an installed native Codex executable or the official installed CLI entry point through Node, using a subprocess argument array. A PowerShell shim can fail under a background host's execution policy even if it works interactively. Test the exact worker command without weakening security settings; a help command alone does not prove chat delivery.
5. Verify a harmless probe file produces a queued notice and a native receiving turn in the NEW chat. Record queue acceptance, receiving turn, independently idle wakeup and real Slack/Claude roundtrip separately. A probe cannot become a coworker message, owner approval or Slack reply. Keep retries durable and avoid automatic hot-loop resubmission.

The fresh chat should report the fetched commit, independent checks, actual schedule/worker targets and remaining gaps. If private installation files contain procedural details absent from this repository, identify that gap rather than claiming a clean GitHub-only setup. Keep the public procedure generic and private installation data private.

## Take over the Claude coordinator

Claude's coordinator is separate from the Codex receiver, so moving one does not move the other. Only when the owner authorizes it, use a new top-level Claude session that has not seen the setup transcript. If the runtime can only start it from another session, detach it to top level, and detach the owner brief too, so archiving the old session cannot take them along.

1. Clone the current default branch into the session's own directory. Read README.md, AGENTS.md, protocol.md, answers.md, folder-state.md, claude.md and the coordinator prompt. Run the helper tests and record the commit. Compare the private helpers with it, ignoring line endings.
2. Verify readiness before changing anything: the actual session ID, native session list/search/read/message tools, subagents on the required models and what they can read, background shell, scheduler and the bridge root. Run a fixture through `answers.py` in a temporary root. Private status files are installation data, not proof. Never write a test item into the real queues.
3. Retire the old coordinator. Its jobs and watcher belong to its session, so it must cancel them itself, on the owner's words. Check the process table before starting a new watcher, because two watchers would process one item twice. Queue files are durable, so a short gap loses nothing. Archiving the old session is the owner's separate decision.
4. Start one watcher and one safety check with its renewal, as in [the Claude guide](claude.md#event-driven-wakeup-in-claude-code). Preserve the owner's wakeup mode and interval. Exclude the old and new coordinators and the brief from relevance matching. Process any pending envelope under the normal rules. Record in private status only what you verified.
5. Keep the owner brief unless the owner says otherwise. `answers.approval_session_id` must name it in every private config copy, and changing it is a policy change. Tell the brief to reread its role file.
6. Test the wakeup with a separate temporary root and watcher, never a fabricated envelope in the real inbox. Report the fetched commit, actual job and watcher IDs, wakeup, delivery and remaining gaps separately. Report any procedure the repository did not supply as a documentation gap.
