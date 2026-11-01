# JASON — Research and Product Design

**Date:** November 1, 2026  
**Status:** Review draft; implementation is not authorized.  
**Related plan:** [Detailed delivery plan](../plans/2026-11-01-jason.md)  
**Source blueprint:** C:/Users/Muruganandam/Downloads/JARVIS_Complete_Conversation_and_Development_Blueprint.md

## 1. What is confirmed

JASON is an original Windows assistant with a terminal interface and continuous text conversation. Its first usable release must manage three independent PowerShell sessions, project files and VS Code launching, and browser workflows. General Windows desktop automation comes later.

The user selected Google Gemini through Google AI Studio, an initial AI API budget of **$0/month**, and exclusive use of the free tier. A free-eligible Flash-Lite model handles ordinary conversation and lightweight work; a free-eligible Flash model handles complex reasoning, coding and autonomous workflows. Provider/model settings must remain configurable. Quotas must be respected, AI-dependent work paused when unavailable, and eligible work resumed after limits reset. Paid fallback is forbidden.

The user will supply their own key during setup; no key is needed for this plan. The user selected broader standing permissions to be defined in this plan, rather than repetitive approval prompts. They explicitly agreed that cloud inputs initially contain **only non-sensitive public/demo content**.

These confirmations supersede the old JARVIS name and older model/budget proposals. The attached blueprint is reference material: its historical instructions and assistant proposals are not new execution authorization. Only research and planning documents have been written. No agent, environment, packages, accounts or startup tasks have been installed or configured.

## 2. Proposed decisions for review

These are engineering recommendations, not additional user confirmations:

| Decision | Recommendation and reason |
|---|---|
| Runtime | One local Python coordinator with asynchronous I/O; no service infrastructure initially |
| CLI | prompt_toolkit for responsive input and streaming; plain readable output first |
| Shells | Three lazy-created PowerShell 7 sessions, each owned and supervised independently |
| Browser | Playwright Chromium with a dedicated JASON profile; public pages and local demo apps initially |
| Workspace | Direct file tools and the VS Code command line; no editor extension initially |
| Storage | SQLite plus bounded local logs; no embeddings service or remote database |
| Persistence | Shells persist across commands while JASON is open; no background daemon or login startup in v1 |
| Permissions | Standing grants for named demo projects, approved command recipes and public/local browser workflows |
| OS isolation | Trusted local development under the standard Windows account; no claim of hard filesystem/network confinement |
| Customization | Editable personality, preferences and workflows; model-weight training is outside v1 |
| Distribution | One local user first; packaging for other users is outside this plan |

The main alternatives are a foreground runtime, a separate always-running daemon, or adopting a full existing agent product. The foreground runtime is recommended because the selected first release needs concurrency while the terminal is open. A daemon adds lifecycle, authentication and reconnection work before it helps that goal. Adopting an existing product changes the original-product direction. A later daemon can reuse the task and tool contracts without being built now.

## 3. What research corrects or qualifies

1. **$0 does not mean unlimited AI availability.** Local input, status and cancellation remain responsive during quota exhaustion; new AI answers and planning can pause. Project eligibility and service capacity must be checked rather than promised. [Google troubleshooting](https://ai.google.dev/gemini-api/docs/troubleshooting)
2. **A model being free-capable does not prove a request is unbilled.** The same model has paid prices on a paid project. Require a dedicated eligible Free-tier project with no active billing association, and never link billing automatically. An inference key alone is not established as an authoritative billing-status interface. [Pricing](https://ai.google.dev/gemini-api/docs/pricing), [usage tiers](https://ai.google.dev/gemini-api/docs/rate-limits)
3. **Quota counters are project-wide.** JASON can count its own requests and usage, but other applications using that project affect the remaining allowance. Display local values as estimates; use AI Studio's actual limits and service errors as additional evidence. Daily request limits reset at midnight Pacific time. [Rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
4. **Free cloud processing restricts inputs.** Google's unpaid-service terms allow product improvement and human review and exclude sensitive, confidential and personal submissions. The user's public/demo-only decision is therefore an architecture constraint. Automatic secret filtering cannot certify arbitrary content as safe. [Terms](https://ai.google.dev/gemini-api/terms)
5. **Permission checks must precede the first tool action.** They cannot wait for the original roadmap's later autonomy phase. Stop controls also belong in the first runnable milestone.
6. **Project-folder checks are not Windows confinement.** Child scripts use Windows process privileges; npm scripts can execute arbitrary commands. Job Objects supervise processes but do not confine file access. Hard containment requires a separate OS-isolation design. [CreateProcess](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw), [npm scripts](https://docs.npmjs.com/cli/v11/using-npm/scripts/), [Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)
7. **Persistent terminals need a real adapter.** ConPTY uses synchronous channel I/O; bridge it through a tested native adapter/worker threads and bounded queues rather than blocking the conversation loop. PTY text alone is not a reliable command-completion protocol. [ConPTY hosting](https://learn.microsoft.com/en-us/windows/console/creating-a-pseudoconsole-session)
8. **Existing personal Chrome control is a separate capability.** Use a dedicated profile; default-profile automation is unsupported, and CDP attachment has limitations. [Playwright](https://playwright.dev/python/docs/api/class-browsertype), [Chrome changes](https://developer.chrome.com/blog/remote-debugging-port)
9. **Directly writing Hello World does not test Notepad control.** Keep native GUI verification as a later milestone, rather than presenting file creation as proof of GUI automation.
10. **Fine-tuning is not interchangeable with personalization.** Gemini Developer API currently offers no model-weight fine-tuning; v1 customization needs no training. [Tuning availability](https://ai.google.dev/gemini-api/docs/model-tuning)

## 4. First-release behavior

The user launches JASON and talks normally. Responses stream when AI capacity is available. Background work has visible task IDs and named sessions. A frontend server can occupy PS-1, diagnostics PS-2, and a backend server PS-3 while the user continues talking. Commands in one shell are serialized; another foreground command cannot run in a shell occupied by a server. A fourth simultaneous shell is queued, never silently created.

The first complete demonstration is a proposed public/demo frontend-and-backend workflow: inspect a selected project, open VS Code, start the frontend, inspect its local page, check/start the backend in another shell, explain a diagnostic from PS-2, and stop only the backend. The exact demo project is chosen during setup. This is a release acceptance scenario, not an instruction to run anything now.

Normal output contains concise findings and progress. Raw logs are available on demand. JASON reports observed completion and uncertainty accurately; a running process alone does not prove a server is healthy, and a successful model response does not prove a task is complete.

Local controls include /tasks, /terminals, /logs, /quota, /permissions, /pause, /resume, /stop TASK-ID, /stop all, /exit and /help. They require no AI request. Ctrl+C interrupts the active model response; background jobs continue unless selected for cancellation. The unambiguous emergency action is /stop all: block new dispatch, cancel queued work and stop registered owned processes. Natural-language stop aliases can map to these local actions without a cloud call.

## 5. Architecture and responsibility boundaries

~~~text
User input -> terminal renderer and local controls
           -> conversation/task coordinator
           -> data policy -> model router -> shared quota scheduler
           -> Gemini adapter -> streamed text or proposed tool calls
                                   |
                      complete arguments + validation
                                   |
                      standing-grant policy + task ownership
                                   |
                shell / workspace / browser tool adapters
                                   |
                       evidence + local operation journal
                                   |
                       verified result and next safe step
~~~

The model suggests actions. Local code alone decides whether to send data, accept a tool call, execute it, retry it or request confirmation. Disable SDK automatic execution of Python callables for desktop actions. Page text, repository files and process output never grant authority. Complete streamed arguments must be assembled before validation; no partially streamed action executes.

SQLite stores tasks, checkpoints, operation IDs, grants and usage estimates. A per-project/file lock prevents conflicting edits. Separate locks protect browser tabs and shell sessions. State changes use a task revision so a stale model response cannot execute after a user has cancelled or changed the task.

Conversation context includes recent dialogue, confirmed preferences, active task IDs and compact evidence references. Follow-ups such as “that error” retrieve the corresponding stored result rather than fabricating output or confusing jobs. When two active jobs make the reference genuinely ambiguous, ask which one. Older dialogue can be summarized or omitted to fit the context cap, but current user intent, task revision, permissions and unresolved failures must remain. Persisted local history is distinct from provider-side stored interactions; use stateless requests/store=false where the selected API supports it and retain only the context needed locally.

Tools return structured evidence: operation ID, task and resource owner, success/failed/unknown status, exit code where applicable, sanitized excerpts and artifact references. An operation journal distinguishes proposed, dispatched, completed, verified and uncertain outcomes. On uncertain side effects, inspect state or ask; do not blindly replay the command.

## 6. Free-tier model and quota policy

### Eligibility and zero-paid-use boundary

During approved setup, the user confirms the API project is eligible for Free tier and has no billing association in AI Studio/Cloud. Record project identifier, confirmed tier, verification date and selected free features locally; do not record the key in that record. A key-only integration cannot independently guarantee that billing will never be enabled externally. If tier evidence is missing or contradictory, block AI calls and explain the setup issue. Optional read-only Cloud billing verification is a separate later enhancement, not an assumed permission.

JASON never activates billing, consumes trial credits as a paid substitute, buys capacity, rotates accounts/keys to bypass limits, switches to a paid provider, or chooses paid-only models/features. Local Playwright automation is distinct from a hosted computer-use API. Search/Maps grounding, paid caching, batch services and hosted computer use stay disabled unless independently proven free and separately approved for a future revision.

Current candidate IDs are gemini-3.5-flash-lite for light work and gemini-3.8-flash for complex work: their Standard input/output pricing is presently free. These are candidates, not proven available in this user's project. Verify model access, streaming and tool calling during approved setup; pin actual SDK/API/model versions. Do not use a moving latest alias. [Current pricing](https://ai.google.dev/gemini-api/docs/pricing), [model catalog](https://ai.google.dev/gemini-api/docs/models)

### Routing and consumption

Route locally by task class: ordinary chat/simple read-only explanations to Lite; coding changes, recovery planning and multi-step tool workflows to Flash. Do not spend an extra AI call merely to choose a model. If Flash capacity is unavailable, wait; do not silently substitute a less suitable model for a complex action. Allow manual selection among verified free routes.

Proposed defaults are one in-flight model request overall, three live shells maximum, one browser context with up to four tabs, and at most two active action workflows. Conversation has scheduling priority; waiting jobs age to avoid starvation. Start with 8,000 input-token and 1,024 output-token budgets for light work, 32,000 and 4,096 for complex work, reduced when actual model limits require it. These are adjustable application caps, not claims about provider quotas. Tool schema and retained policy/history count toward input context.

Select relevant excerpts, deduplicate repeated logs and keep compact task summaries locally. Do not send full repositories, full browser histories or unbounded terminal transcripts. Run deterministic monitoring without AI polling; a process exit creates one actionable event, not repeated model requests. Use model-specific supported thinking controls only after verifying their contract.

### Quota manager

- Configure actual per-project/model RPM, input TPM, RPD and any extra limits shown in AI Studio; zero or unknown eligibility is not unlimited allowance. No guessed quota table is built into product promises.
- Reserve estimated request/input capacity before dispatch; reconcile observed usage afterward. Distinguish request counts, input tokens, output tokens, thinking tokens and cached usage where the response provides them. Do not double-count provider totals.
- Persist local daily request estimates, outstanding reservations and known reset times. Track interrupted/failed requests conservatively. Show that other clients and server-side accounting can make remaining-quota estimates inaccurate.
- One scheduler owns all requests, including retries, diagnostics and summarization. Disable or integrate hidden SDK retries so they cannot bypass accounting. Never sleep on the CLI thread.
- Honor structured retry delays when available. Otherwise use exponential backoff with jitter, initially 1/2/4/8 seconds with a 60-second cap and at most four retries for transient failures; every retry requires fresh admission. Daily quota exhaustion waits for reset rather than consuming four immediate retries. Authentication/eligibility/configuration failures require correction, not daily blind retries.
- Compute daily reset with the America/Los_Angeles timezone, including daylight saving; show the next expected reset in Asia/Calcutta. Use monotonic time for short windows and UTC for persisted timestamps.

When capacity is unavailable, use WAITING_FOR_QUOTA with a reason and an estimated next attempt if known. Existing dev servers may continue; no unplanned next action is launched. After reset/retry eligibility, resume only still-authorized work after checking cancellation, changed files, server state, grants and current quota. A reset is permission to reassess, not proof capacity returned or permission to duplicate side effects. Unknown exhaustion causes are reported honestly. [Rate-limit definitions](https://ai.google.dev/gemini-api/docs/rate-limits), [retry guidance](https://ai.google.dev/gemini-api/docs/troubleshooting)

## 7. Standing-permission proposal

Grants record project root, allowed action categories, approved command recipes, browser origins, network expectations, duration and revocation. Persist them until revoked unless the user chooses task/session expiry. A task can reuse a matching grant; it cannot expand it. Approval requests state the exact new effect and why the existing grant does not cover it.

A command recipe binds its executable, argument schema, canonical cwd, relevant script/manifest identity and disclosed effects. The model selects a recipe and validated arguments, not an arbitrary command string that passes merely because its first word is npm or pwsh. An unfamiliar one-off command must be shown and explicitly covered by a grant before preparing it for the shell. Recipe/script/lockfile changes invalidate the affected grant for review. These checks reduce unintended actions; they do not constrain arbitrary trusted script code at the OS level.

| Action | Proposed v1 behavior |
|---|---|
| Read/search non-sensitive files in an opted-in demo project | Automatic under the grant; sensitive/unknown content withheld from Gemini |
| Create/edit ordinary project source, inspect diffs, open VS Code | Automatic with stale-file checks and recoverable local changes |
| Run reviewed test/build/format/start recipes | Automatic under a command grant, including disclosed execution/network effects |
| Start/use PS-1 through PS-3, inspect owned process status | Automatic; independent ownership and cancellation |
| Inspect public pages and local demo app, click demo controls | Automatic within granted origins and workflow effects |
| Retry transient failures or resume after quota reset | Automatic only within original scope, budget, checkpoint and freshness rules |
| Add a project/origin, run unfamiliar scripts or broaden network scope | Confirm the expanded grant once; reuse it afterward |
| Install/update project dependencies or change a recipe/lifecycle hook | Confirm changed execution effects; grant can cover that named task |
| Delete files, overwrite unrelated/untracked work, reset Git state | Show exact impact and obtain specific confirmation; preserve recovery where feasible |
| Upload/download demo files or submit a non-sensitive external form | Confirm unless an existing explicit workflow grant covers the exact effect |
| Local Git commits of JASON-owned edits | Automatic only when the project/task grant includes local commits; exclude unrelated staged/unstaged work and review execution hooks |
| Push, publish or send external messages | Outside standing developer grants; require explicit authorization for that external effect |
| VS Code extension installation, user settings, workspace trust | Confirm; project access alone does not authorize global settings |
| Personal accounts, credential extraction, payments, security changes, UAC/admin actions | Disabled in v1; broader product scope must be reviewed first |
| Send private/confidential/personal/uncertain data to free Gemini | Block under current agreement; a one-off tool approval cannot override this data rule |

Approving this plan adopts the matrix only if the user explicitly approves it; it does not preapprove unspecified system-wide actions. During setup, the user selects actual project roots and command grants. A multi-root VS Code window does not authorize all roots.

## 8. Data and credential handling

Prefer a session-scoped local GEMINI_API_KEY environment variable. A local .env file is an optional convenience with user-only Windows permissions, ignored by Git and excluded from file tools, log capture and model context. It is plaintext protected by filesystem access, not an encrypted vault. Do not overwrite an existing secret file or ask the user to paste the key into chat.

Construct child-process environments explicitly; exclude Gemini keys, unrelated tokens and unnecessary credential variables. Never put secrets in command-line arguments. This reduces exposure but does not isolate same-user processes from personal files or credential stores.

Only opted-in public/demo sources are candidates for model input. Enforce exclusion of .env files, private keys, browser storage, credentials and secret-bearing settings. Inspect excerpts for likely secrets and withhold uncertain content. A project label or filename alone is not proof of safety. Diagnostic text can contain credentials, absolute personal paths or personal information; minimize and sanitize it before submission. A blocked excerpt stays local with a clear explanation; do not ask Gemini to decide whether it is safe by uploading it.

The same admission gate covers every outbound component: newly typed chat, retained dialogue, user preferences, task summaries, file/path labels, custom instructions, tool arguments/results and browser evidence. Directly typing a secret or personal detail is not consent to upload it under the current free-tier agreement. Hold detected sensitive/uncertain text locally and invite a non-sensitive rephrasing; prevent retained history from reintroducing previously blocked text. Human classification and careful source selection remain necessary because automatic detection is imperfect.

Authenticated personal browser workflows and full-screen capture remain off. Screenshots, if necessary for a public/demo page, are explicit scoped artifacts; prefer DOM/text. No continuous recording, keyboard collection or automatic whole-project upload.

Proposed local retention: redacted conversation and diagnostic logs 7 days, task/audit/usage metadata 30 days, confirmed user preferences until removed; screenshots are not retained by default. The user can inspect, export, correct or clear local records. Local deletion cannot revoke data already processed by Google. No consented training dataset is collected in v1.

## 9. Shell, workspace and browser details

### PowerShell

Prefer standalone PowerShell 7 with a supported Python version and verified ConPTY wrapper wheels. Use a native adapter with dedicated channel I/O workers feeding bounded asyncio queues. One shell owns cwd, environment, variables and foreground command state. A controlled runner needs explicit completion/exit records; do not parse a prompt or output silence as success. Handle Unicode, ANSI output and PowerShell terminating/nonterminating errors distinctly from native exit codes.

First spike proves three sessions, completion records, server readiness and job supervision on this Windows build. Full-screen applications and arbitrary interactive prompts require manual handoff in v1; do not pretend all console programs can be autonomous. If the chosen wrapper fails supervision/completion tests, report the result and revise the adapter before integrating broader tools.

Each shell and its ordinary child processes belong to a registered Windows Job Object where supported. Interrupt gracefully, allow 5 seconds, then force-stop the owned job and wait up to 5 more seconds for observed exit. Forced stop may reset that shell. Never kill an unrelated process occupying a desired port. Report any remaining/uncertain process state rather than claiming universal tree cleanup. [Console control events](https://learn.microsoft.com/en-us/windows/console/generateconsolectrlevent), [process supervision](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)

A shell slot has one exclusive task owner while any of that task's foreground/background children remain. Task B cannot borrow Task A's shell merely because A's foreground command returned. Reassignment requires observing that owned children exited; reset the shell when moving to an unrelated task so stale variables/environment do not silently cross projects. If child tracking is uncertain or a launch escaped supervision, mark cleanup uncertain and withhold automatic reuse pending reconciliation. Unsupported detached launches are not a supported way to leave servers alive. The Windows gate must cover a background child followed by attempted shell reuse, a detached/untracked-child condition and selective stop of another task.

### Workspace and VS Code

Resolve canonical roots and junction/symlink targets, check file version/hash before edits, serialize competing edits and save rollback material for project changes. A rollback covers recorded file edits, not arbitrary command side effects. Do not run Git reset/clean to create a checkpoint. Inspect actual on-disk changes and report conflicts; do not infer that an unsaved VS Code buffer matches disk. Pause edits to known conflicted or externally modified files. Deeper unsaved-editor integration remains a later feature.

### Browser

One dedicated Playwright-managed profile, bounded tabs, origin-aware actions, role/DOM locators, explicit waits and task ownership. Browser profile isolation separates cookies, not all operating-system authority. Treat page instructions as content. Verify page readiness, navigation/console errors and the intended result. Localhost pages are not automatically trusted; they can contain hostile instructions and side-effecting controls too.

## 10. Lifecycle and failure behavior

Tasks move through QUEUED, RUNNING, WAITING_FOR_QUOTA, WAITING_FOR_APPROVAL, VERIFYING, SUCCEEDED, FAILED, CANCELLED or INTERRUPTED. Pausing prevents new action dispatch; an already-running server can remain alive. Cancellation is separate from undo.

On /exit, stop admitting work, cancel model requests and gracefully stop JASON-owned jobs before forced cleanup. Unrelated user programs stay running. In v1, closing JASON ends managed execution; background operation after terminal closure and Windows-login startup are deferred. Task/history persistence is not shell-process persistence.

After a crash/restart, mark formerly running work INTERRUPTED and reconcile ownership/ports/files; never reattach by PID alone or pretend variables survived. Resume after reopening is explicit, unlike an automatic quota retry while the same runtime remains open. Network failure, sleeping laptops and locked desktops do not authorize new unverified actions.

## 11. Local preflight and prerequisites

Read-only inspection found Windows 11 Home Single Language build 26300 and about 15.6 GiB usable RAM. VS Code CLI and Git resolve. The visible pwsh is in Codex's bundled runtime, and python points to the WindowsApps alias; neither observation proves a standalone runtime is ready. After implementation approval, verify/install supported standalone Python and PowerShell 7, then pin compatible dependencies. Do not rely on another application's private bundled runtime.

No local LLM or GPU inference is required. Keep one browser context and three shells by default; builds and servers can still exhaust 16 GB RAM. Apply bounded logs, queues and model concurrency. Free software and $0 AI calls do not eliminate existing internet, hardware or electricity costs.

## 12. Deferred scope and review assumptions

Deferred: general Windows GUI control, Notepad UI proof, voice/wake word, auto-start/daemon, private/personal cloud workflows, hard OS confinement, full-screen terminal autonomy, VS Code unsaved-buffer extension, model-weight training, public distribution, hosted paid tools and autonomous external publishing/messaging.

Review these assumptions with the plan: foreground lifetime only; dedicated public/demo browser; trusted scripts under the standard user account; personality/workflow customization rather than weight training; proposed log retention and context caps. Before live API setup, confirm actual service region/eligibility and permitted account/use terms, Free-tier status, selected model quotas and project identity. No values from an inference key are assumed to prove billing status. If private data or hard containment becomes required, revise the design before broad execution.

## 13. Acceptance gate

The release passes only when it demonstrates the frontend/backend scenario, local controls during artificial quota/network failure, independent three-shell state and selective stop, scoped edits with conflict detection, public browser verification, no secret in model requests/child environments, no unapproved tool dispatch, no paid fallback and no blind mutation replay. Tests use fake model responses and a disposable demo project first. One approved small live free-tier smoke test validates integration; it is not a capacity or reliability benchmark.

Full implementation steps and named verification cases are in the linked delivery plan. The design and plan require user review before any product implementation.
