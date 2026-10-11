# Security

SpendSentry is designed so an AI agent cannot change an ad account without the user's typed approval of the exact action. If you find a way around that, please report it privately rather than in a public issue: use GitHub's "Report a vulnerability" (Security tab) on this repository.

In scope: bypassing the guard hook, forging or replaying approvals, executing actions that differ from the approved input, and gate checks that can be skipped.
Out of scope: write access you granted outside Claude Code (credentials in your shell, other tools).

Known limits are documented in `skills/ads/references/safety-model.md`.
