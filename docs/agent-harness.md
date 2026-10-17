# Coding-agent harness

`AGENTS.md` is the canonical shared guidance for Codex, Kimi Code, Crush and Amp.
`CLAUDE.md` links to it and may contain additional Claude-specific instructions.

## Scope
- Project files are separate from global configuration and credentials.
- Edit provider/model settings in each agent's own settings UI or config.
- Never commit API keys or use an unapproved unrestricted/sandbox mode.

## Maintenance
Regenerate the repair-managed sections using `repair-coding-agents-v2.sh --projects --rewrite-harness --apply`.
Handwritten sections outside the markers are preserved.
