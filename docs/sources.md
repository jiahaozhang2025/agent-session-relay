# Official product references

Reviewed for the initial guide on 2026-10-31. Recheck current documentation and actual account tools during onboarding.

- [OpenAI scheduled tasks](https://learn.chatgpt.com/docs/automations): schedules, in-chat context, connected tools, desktop availability requirements, and eligible web/mobile event triggers.
- [OpenAI Slack deployment and personal access](https://learn.chatgpt.com/docs/enterprise/chatgpt-slack-and-teams): shared deployments and personal connections are distinct.
- [Claude Code session schedules](https://code.claude.com/docs/en/scheduled-tasks): `/loop`, session lifetime, native monitoring where available, scheduling limits and expiry.
- [Claude Code Desktop scheduled tasks](https://code.claude.com/docs/en/desktop-scheduled-tasks): local scheduled work and new sessions.
- [Claude Code channels](https://code.claude.com/docs/en/channels): configured MCP event delivery into running sessions; availability requirements apply.
- [Slack data exports](https://slack.com/help/articles/201658943-export-your-workspace-data): export scope, roles, plans and approval requirements.
- [Slack cache troubleshooting](https://slack.com/help/articles/205138367-Troubleshoot-connection-issues): cache clearing/rebuilding; this is not a cache-history API specification.

The session-routing procedure is this project's design. Native cross-session tools differ across products and installations; the links do not guarantee every runtime supports session-to-session notification.
