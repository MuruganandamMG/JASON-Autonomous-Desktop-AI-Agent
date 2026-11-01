# JASON

**Updated access behavior:** normal chat no longer requires a public/demo workspace or a per-message classification approval. Local file tools may work in any folder by default (workspace.any_folder=true); set it false to restore root confinement. Relative paths use the configured root; absolute paths can select other folders. Edit grants are scoped to each destination folder. Secret-path/content checks and explicit classification of cloud-bound file/browser/terminal excerpts remain active. Free-project verification, key and quota setup are still required for AI replies. Older public_demo instructions below are retained for compatibility; that flag no longer gates chat or AI readiness.

JASON is a Windows terminal agent: streaming Gemini conversation, concurrent tasks, three persistent PowerShell sessions, project editing/VS Code launch, and browser automation. The initial version uses Gemini Free-tier projects only. It does not run a remote-control server; GitHub is the configured remote.

## Install

Use standalone **Python 3.12+**, **PowerShell 7** (pwsh on PATH), Git, VS Code, and Microsoft Edge. A compatible Chromium build can also be configured in the Browser adapter. The supplied tests use Edge because downloaded Chromium failed on this machine with Windows side-by-side error 14001.

In a PowerShell terminal in this repository:

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item config.example.toml config.toml
~~~

The development environment created in this checkout is already installed. It uses Codex's development Python; create a fresh environment from your own standalone Python for use outside Codex. No dependency on Codex is built into JASON.

## Configure the free project

1. In Google AI Studio, verify your project is eligible for the **Free tier**, with **no linked billing account**. JASON does not enable billing or use credits/paid fallback. The API key cannot itself prove billing status; you must verify it. Reconfirm when changing project/account.
2. Edit ignored config.toml: project_id, free_project_verified=true, verified_on as today's YYYY-MM-DD, actual Lite/Flash RPM/input-TPM/RPD, root of your public demo project, public_demo=true, and allowed public/demo browser origins (including localhost ports).
3. Candidate models are gemini-3.5-flash-lite and gemini-3.8-flash. Check current availability, pricing and actual project quotas in AI Studio. Unsupported models are blocked. The model allowlist lives in models.py and must be reviewed with pricing evidence before expansion.
4. Set your key **locally**, not in chat or Git:

~~~powershell
$env:GEMINI_API_KEY = Read-Host "Gemini API key" -MaskInput
.\.venv\Scripts\python.exe -m jason --config config.toml
~~~

An ignored .env with GEMINI_API_KEY is also supported. It is plaintext, not an encrypted vault; restrict its Windows file permissions. Never commit it. Shells, browser processes and VS Code launches receive a reduced environment excluding the model key.

No key is needed for offline controls or the automated test suite. Free-project verification expires after one day; update verified_on only after confirming the project remains eligible and unbilled. A free-capable model can be billed if someone externally changes the project to Paid; JASON cannot prevent external account changes.

## Conversation and approvals

Type an instruction while other jobs run. Examples:

- “Explain the demo architecture.”
- “Open this project in VS Code, start the frontend in PS-1 and inspect its localhost page.”
- “Run diagnostics in PS-2 and the backend in PS-3; keep the frontend alive.”

Each task has an ID. Describe your request normally: create/make/write requests select action routing, and any tool call on the light route continues automatically through the same local permission checks. No resubmission is needed. Bare /flash or /lite changes the mode; /auto restores automatic selection. Empty requests never start tasks.

Only non-sensitive public/demo information may go to the free cloud service. **Content classification is human-assisted:** each exact chat input and newly read file version requires local public-content classification; shell/browser/search excerpts require classification before upload. The local approval shows the content to review. Known credential patterns are blocked, but automatic detection is not proof that arbitrary data is public. This adds approval steps intentionally; it does not silently send uncertain data for fully unattended operation.

Use /approve ID or /deny ID. Reversible project edit/open-VS-Code grants can be reused until revoked. **Arbitrary PowerShell commands use one-use approvals**, because their transitive code/dependency effects cannot be safely fingerprinted. They execute with your Windows account privileges, not inside a security sandbox. Approve only trusted demo scripts. The first version does not yet offer reusable named command recipes.

Read a file before writing: the tool requires its current SHA-256; new files use an empty expected hash. Existing content is backed up locally. Concurrent changes are refused. This protects recorded edits, not arbitrary shell side effects or unsaved editor buffers.

## Local controls

App and working-folder controls work locally without an AI request: /apps lists installed Start Menu applications, /app NAME launches a selected app, /terminal opens a visible owned PowerShell window, and /cd PATH changes the default working folder. Model tools expose the same app discovery/launch and terminal capabilities. /retry TASK-ID starts a fresh inspected reattempt of prior work. /tasks and common completion questions display actual task states immediately, without waiting for Gemini. Waiting approvals do not occupy conversation capacity. /stop all closes both visible owned terminals and managed shell sessions.

Applications are launched through installed executable paths/shortcuts, not arbitrary shell evaluation. This is app launching and terminal management, not universal mouse/keyboard control of every Windows app. Command execution, file changes and cloud-bound excerpts retain their approval boundaries.

| Control | Behavior |
|---|---|
| /tasks | Task states and IDs |
| /terminals | PS-1/2/3 owners, running state and exit code |
| /logs 1 | Recent output for one session (local only) |
| /quota | Local usage/reservation estimates; not authoritative remaining quota |
| /permissions | Pending approval IDs |
| /approve ID, /deny ID | Resolve a local approval |
| /revoke | Clear standing grants |
| /pause, /resume | Disable/enable new action dispatch; existing servers continue |
| /stop TASK-ID | Cancel that task and its owned shells |
| /stop all, “stop everything” | Cancel all tasks, stop owned shells, leave dispatch paused |
| /new | Clear in-memory conversation context |
| /exit | Stop owned work and close JASON |

Ctrl+C cancels response tasks and pending approvals; it preserves existing shells. Use /stop all for full owned-job cleanup. Shell completion/exit changes produce local alerts without model polling. Raw logs are bounded in memory.

A foreground server occupies one shell. Shell slots are not reassigned to another task while background children remain. On forced stop the shell resets. Normal child processes are supervised through Windows Job Objects; WMI/breakaway/detached launches are unsupported and universal descendant cleanup is not promised.

## Quota behavior

All model attempts pass through one request lock and a persisted local RPM/input-TPM/RPD admission ledger. Actual returned token metadata is recorded separately from reservations. Input reservation is a conservative byte-based estimate, not an authoritative tokenizer; check AI Studio and configure headroom. SDK hidden retries are disabled.

AI-dependent work waits when quota is exhausted. Local status/stop commands and already-running servers remain available. Daily reset uses Pacific time with daylight saving. Transient service exhaustion has bounded retries, followed by a conservative daily-reset wait. Invalid configuration/credentials fail locally instead of upgrading. Before continuing, tool approvals and script/page identity are checked again. A journal prevents blind replay of an operation with uncertain effects.

## Testing

~~~powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
~~~

Tests include real Windows PowerShell sessions, Job Object ownership, child environment exclusion, local Edge navigation/clicks/redirect blocking, a frontend + diagnostics + backend demonstration, data/path checks, quota clocks, mocked Gemini tool continuation, approval revocation and cancellation races. One junction/symlink test can skip when Windows does not permit creating symlinks.

**Live Gemini validation completed on November 1, 2026 for the configured local Free project:** interactive greeting, conversation follow-up, file creation and readback passed. The automated suite uses SDK data types/fake provider output for deterministic failure checks. New installations still need their own key/project setup and smoke test. Temporary provider errors now show bounded retry progress; network requests time out after 60 seconds, and local stop remains available during backoff.

## Current limits

- This is the initial runtime, not a claim of universal autonomous desktop control.
- No general GUI control, voice, auto-start, post-exit daemon, remote-control server, private-data cloud mode or model-weight training.
- Conversation context is bounded and in memory. Task, approval, operation and quota records persist. After restart, running tasks become INTERRUPTED; issue a fresh instruction after inspecting state, rather than replaying an old plan.
- Quota waiting resumes in the open process; an interrupted process cannot automatically continue later.
- Browser uses an isolated temporary profile and one owned page, with navigation restricted to configured origins. Browser actions serialize; page URL is rechecked after approval. It does not attach to your personal browser profile or retain login cookies.
- No unsaved VS Code buffer access, automatic rollback of commands, full-screen terminal autonomy, verified server health beyond requested tool evidence, or perfect secret detection.
- Local SQLite records/backups currently remain until you remove the ignored .jason folder after closing JASON. Automated retention/export and durable conversation preferences remain follow-up work; do not store private content here.
- The approved design remains the target; actual completion and deviations are recorded in TRACKER.md.

## Branches and progress

main preserves the approved planning baseline; feat/jason-runtime contains implementation and tests. No worktrees are used. See [TRACKER.md](TRACKER.md), [design](docs/superpowers/specs/2026-11-01-jason-design.md), and [implementation plan](docs/superpowers/plans/2026-11-01-jason.md). Pushes are normal fast-forward branch updates; no force push is required.
