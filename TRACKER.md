# JASON implementation tracker

Plan: docs/superpowers/plans/2026-11-01-jason.md

Branch: feat/jason-runtime. User authorized implementation, branch management and pushes; no worktrees. GitHub is the only requested remote access.

## Decisions
- Use normal feature branch; preserve main documentation baseline.
- Use installed development virtual environment to verify; standalone Python/PowerShell are prerequisites for user setup.
- Provider: supported async generateContent SDK API, manual function dispatch; no hosted tools.
- No live API test without user-supplied key and verified free project.
- Runtime grants are local approvals for exact commands and selected public/demo root.
- Remote-control/network server omitted: user explicitly requested GitHub remote only.

## Progress
- [x] Configuration, SQLite, data policy and grants
- [x] Quota scheduler and streaming Gemini adapter (live account validation pending)
- [x] Persistent Windows shells and owned process cleanup
- [x] Workspace edits and browser
- [x] Concurrent CLI/task orchestration
- [x] Windows/browser tests, independent review and documentation
- [ ] Live Gemini acceptance: needs user key, verified Free project and actual quotas
- [ ] Verify pushed GitHub CI result

## Rulings and implementation limits

1. Normal main/feature branches replace worktrees, per user instruction. GitHub remote only; no remote-control server.
2. Supported async generateContent SDK used; automatic callable execution/hidden retries disabled. Model candidates are allowlisted and require real project eligibility verification.
3. Arbitrary PowerShell commands use one-use approvals because transitive script dependencies cannot be fully fingerprinted. Reusable named recipes remain follow-up work; this adds prompts.
4. Exact chat inputs, read file versions and shell/browser/search excerpts require human public/demo classification. Filters are supplemental, not certification.
5. Edge is the tested Chromium engine with an isolated temporary context. Downloaded Chromium failed with WinError 14001; no system runtime/UAC change was made.
6. Startup cancellation collects and cleans the eventual owned shell; grants and page/command identities are rechecked immediately before dispatch. Job supervision does not provide OS isolation or universal escaped-child cleanup.
7. Conversation is bounded/in-memory. Crash recovery marks old work INTERRUPTED rather than replaying it. Durable preferences, automated retention/export, persistent browser profiles and reusable command recipes remain follow-up work, documented in README.
8. Development uses the available development Python in a local virtual environment. Product setup requires standalone Python/PowerShell; no Codex internal path is hardcoded.
9. No merge into main, force push, paid fallback, public deployment or worktree was introduced.

## Verification evidence

- Core policy/quota tests passed after implementation; revoked-grant and spawn-cancellation regressions were reproduced before fixing them.
- Real three-shell tests verify state, key exclusion, selective stop and background-child ownership.
- Real Edge tests verify localhost navigation/clicks and blocked redirects.
- Full frontend + diagnostics + backend + browser/selective-stop demonstration passed, including the apostrophe in this checkout path.
- Fake Gemini tests verify tool continuation, conversation context and quota waiting without duplicate writes.
- Windows symlink creation is unavailable; that test reports a skip, not a pass.
- No real Gemini call was made. Final suite counts and branch push evidence are recorded in execution output/commit history. The full release gate remains open until live Gemini is validated.
- Final local verification: **26 passed, 1 skipped** (Windows symlink privilege); pip dependency check and Git whitespace check passed. Piped CLI startup/exit regression also passed.

