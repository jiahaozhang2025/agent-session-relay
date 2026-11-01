"""Watch the private file queues and notify an existing Codex chat.

Uses the common durable queue machinery with mailbox_enabled=false. No GitHub
account, Slack token, public endpoint or cloud filesystem adapter is needed.
The exporter still needs its own working Slack connection and local file access.
"""
from mailbox_worker import main

if __name__ == "__main__":
    main()
