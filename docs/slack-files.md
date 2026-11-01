# Can Claude read Slack through local files?

Claude with filesystem access can read ordinary message exports or a deliberately created inbox that the user is authorized to share. A Slack connector is not needed to parse such files. File access, however, does not automatically provide live Slack access or permission to send content to a different service.

## Desktop cache

It may be technically possible to recover some already-fetched message fragments from an accessible desktop cache. This project has not audited Slack's current cache format or anyone's installation. Do not promise a complete archive, current messages, every thread, stable sender metadata or attachments.

Slack documents clearing/rebuilding its cache as a troubleshooting step and provides a separate supported export mechanism. We therefore treat a cache reader as an unreliable input for ongoing coordination, not as a supported message-history interface. That is an engineering judgment, not a claim that no message bytes ever exist locally.

Reading a cache does not provide message sending, an event subscription, or an agent wakeup. Do not extract browser/desktop session cookies or tokens and repurpose them as an unapproved integration. Use the organization's allowed data-sharing route rather than assuming filesystem readability settles approval requirements.

## Supported exports

An authorized Slack export can be useful for a historical analysis. Export availability, private-channel coverage and approval requirements depend on role and plan. An export is a snapshot, not a live receiver. See [Slack export documentation](https://slack.com/help/articles/201658943-export-your-workspace-data).

## The intended file bridge

Use an approved Slack connection to read only the selected channel, filter out the owner's own messages, then write accepted updates to the owner's private inbox. Claude reads that explicitly selected content through normal file access. The agent provider, workspace policies and allowed audience still govern what can be shared.

This keeps transport identity, cursor handling and scope explicit. It does not require approving a separate Claude Slack app, but it also does not override an organization's restrictions on processing Slack content with Claude.

Source for cache behavior: [Slack connection troubleshooting](https://slack.com/help/articles/205138367-Troubleshoot-connection-issues). No cache extraction is included here.
