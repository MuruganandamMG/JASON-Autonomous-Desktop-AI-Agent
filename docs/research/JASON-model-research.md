# JASON: Gemini model/API research

Research only; no installation, API account changes, scaffolding, or implementation. Retrieved 2026-11-01 from primary Google documentation. Model names below were verified in current pages, not inferred from older model knowledge. Actual availability, quota, latency, and quality in the user's project remain untested.

## User free-tier decision: update after initial questions

This section supersedes the earlier open provider/budget questions below. User selected Gemini AI Studio Developer API only, initial cost $0, their own key later, Flash-Lite for everyday work and Flash for complex work, no paid fallback, quota pause/resume, and modular future upgrades. V1 scope is live terminal conversation, three PowerShell sessions, workspace/VS Code and browser; broader desktop later. This remains research, not implementation authorization.

### Verified current facts

- Standard `gemini-3.5-flash-lite` and `gemini-3.8-flash` currently list free input/output. Pricing is model/feature-specific, not a blanket free entitlement: their built-in Search/Maps grounding is unavailable on the API free tier (AI Studio testing is different), and computer-use model tooling is unavailable free. Use ordinary local/browser tools for approved v1 capabilities; do not confuse them with Google-hosted paid features. [Current pricing](https://ai.google.dev/gemini-api/docs/pricing)
- Current docs support free-tier model inference through the Developer API; `interactions`, `generateContent`, and `streamGenerateContent` are explicitly named inference paths. Availability depends on the project. Not every project/account qualifies; `models.list` success does not prove inference eligibility or billing status. If eligibility fails, this user's chosen policy requires stopping rather than upgrading. [Project eligibility and metadata limitation](https://ai.google.dev/gemini-api/docs/troubleshooting#project-restricted-or-unavailable)
- India is on the supported-region list. Timezone alone does not establish location, age, or account eligibility. API terms require age 18+, professional/business developer use, and access from an available region. Clients made available to EEA/UK/Swiss users must use paid services, while their unpaid data treatment has a separate regional exception. A free-only distribution plan therefore needs actual audience/location confirmation. [Regions](https://ai.google.dev/gemini-api/docs/available-regions), [Terms](https://ai.google.dev/gemini-api/terms)
- Free input outside the regional exception can be used for product improvement/human review; sensitive, confidential, and personal input must not be submitted. This includes relevant workspace text, terminal output, URLs, page contents and screenshots. Local detection/redaction cannot guarantee universal scrubbing. A local access grant is not blanket permission to transmit its contents. [Unpaid-service terms](https://ai.google.dev/gemini-api/terms#unpaid-services)
- RPM, input TPM, RPD and any model-specific limits share project scope across keys/jobs. RPD resets at midnight Pacific, not midnight India/UTC. Compute reset with `America/Los_Angeles` and daylight-saving rules. No exact RPM/TPM window-boundary guarantee was found; do not invent one. AI Studio exposes the actual project limits; capacity remains variable. [Quota rules](https://ai.google.dev/gemini-api/docs/rate-limits)
- AI Studio's Projects/Billing Tier view and Dashboard > Usage are the documented checks for tier and aggregate usage. The API key identifies the project's billing/quota context; it is not a free-only credential. Existing billing-enabled projects may incur paid model rates even for models with a free-tier offering. [Billing and usage views](https://ai.google.dev/gemini-api/docs/billing#verify-billing-status), [Key/project association](https://ai.google.dev/gemini-api/docs/api-key)

### Practical $0 boundary and usage monitor

Use a dedicated eligible project with no linked open billing account; do not link billing, prepay, auto-reload, or switch providers. Keep an explicit approved model/endpoint/feature allowlist and fail closed on unavailable/paid-only capabilities. These are proposed application rules, not proof that arbitrary credentials are free. The returned `service_tier=standard` describes inference service class, not a Free billing-tier attestation; the schema has standard/flex/priority values, no free-only billing guard. [Service-tier schema](https://ai.google.dev/api/interactions-api)

For authoritative billing-state automation, Cloud Billing `projects.getBillingInfo` returns `billingEnabled`; false means paid services cannot be used. It requires an authenticated principal with project-view permission and OAuth scopes, not just an ordinary inference key. An API-key-only v1 can require the user to verify the dedicated project's Free tier in AI Studio, but cannot honestly promise continuous independent detection if someone later enables billing. Optional read-only Cloud authentication is a separate scope decision. [Billing-state method](https://docs.cloud.google.com/billing/docs/reference/rest/v1/projects/getBillingInfo), [Billing-state meaning](https://docs.cloud.google.com/billing/docs/reference/rest/v1/ProjectBillingInfo)

Make configured limits editable per actual project/model; don't hard-code a blog's free quota. A shared persistent ledger should track attempts, per-model request timestamps and Pacific-day counts, token estimates/reservations, returned actual usage, unknown usage after interrupted streams, and pause reason/reset estimate. All three shell jobs and chat must pass through one admission controller. Show local estimates as estimates: other apps/keys can consume the same project's quota, and server enforcement wins.

No documented key-only endpoint providing exact remaining Developer API RPM/TPM/RPD and live billing status was established in this research. Cloud Service Usage has quota-metric/limit APIs requiring `serviceusage.quotas.get` and OAuth; this generic endpoint is not proof that all Gemini AI Studio counters or remaining consumption are exposed. Don't promise automatic authoritative quota synchronization. [Service Usage quota API](https://docs.cloud.google.com/service-usage/docs/reference/rest/v1beta1/services.consumerQuotaMetrics/list)

Use final `interaction.usage` input/output/thought/cache/tool/total counters; `count_tokens` measures input before generation, not future thinking/output. If using the older generation API, equivalent fields live in `usageMetadata`. Final totals may be missing on interrupted requests; retain an unknown/reserved state instead of claiming zero. Token metadata is not a remaining-quota counter. [Token guide](https://ai.google.dev/gemini-api/docs/tokens), [Generation usage schema](https://ai.google.dev/api/generate-content#UsageMetadata)

### Pause, retry and resumable work

Interactions distinguishes short-window `rate_limit_exceeded`/`too_many_requests` from daily `quota_exceeded`, all potentially HTTP 429. Short-window/transient failures warrant bounded exponential backoff with jitter; daily exhaustion should park model-dependent work until the next Pacific reset and recheck with a bounded attempt. A permission/eligibility failure requires attention, not waiting for midnight. Legacy errors may use `RESOURCE_EXHAUSTED`; inspect endpoint-specific structured details rather than classifying every 429 as daily exhaustion. [Error codes](https://ai.google.dev/gemini-api/docs/api-errors), [Retry guidance](https://ai.google.dev/gemini-api/docs/troubleshooting#retry-strategy)

Respect valid server retry hints if supplied, but no guarantee was found that every Gemini 429 includes `Retry-After` or `RetryInfo`. HTTP permits date or seconds forms. Configure one owner for retries so SDK automatic retries and scheduler retries do not multiply attempts; current SDK source exposes retry options and exponential jitter. [HTTP Retry-After](https://www.rfc-editor.org/rfc/rfc9110.html#field.retry-after), [Google SDK retry code](https://github.com/googleapis/python-genai/blob/main/google/genai/_api_client.py), [Retry option schema](https://github.com/googleapis/python-genai/blob/main/google/genai/types.py)

Resume the job from persisted checkpoints, not by replaying the entire user command. Record local tool-call identity, arguments, result and completion/uncertainty before requesting further inference. Verify external state before retrying any uncertain write; do not repeat terminal/browser side effects merely because the model request timed out. Provider interaction/event IDs and continuation tokens support provider reconnection where available, but they do not supply exactly-once local execution. No general Gemini create-request idempotency-key guarantee was found in the API reference. [Interaction/continuation schema](https://ai.google.dev/api/interactions-api)

### Remaining uncertainties and user answers

- Actual country/audience, age/account eligibility and the later supplied project's Free tier/available limits are unverified. $0 availability and continuous service cannot be promised before those checks.
- Confirm which non-sensitive workspace/browser material may be sent to unpaid inference. Automatic broad desktop capture is not compatible with treating everything it sees as safe to upload.
- Decide whether an API-key-only setup with user-confirmed billing state is sufficient, or whether a strict automatic check must require optional read-only Cloud authentication. Never claim the model allowlist alone prevents charges on a billing-enabled project.
- Decide whether daily exhaustion parks the whole reasoning job or permits an explicitly approved alternate free model. There must be no hidden quality downgrade or paid fallback.
- User must choose automatic post-reset continuation versus asking to resume when the machine/browser/workspace may have changed during the wait. Any auto-resume needs freshness checks and a live application process; a powered-off PC cannot resume itself.

No account/key was used, and no live inference or billing-state call was made. The source discrepancies noted elsewhere remain integration-test items for the approved implementation phase.

## Decisions the research changes

- Gemini is a viable candidate, not a settled requirement. Select it only after the user answers privacy, spending, and customization questions and a later approved evaluation demonstrates reliable desktop tool selection.
- Keep cloud inference separate from local execution, authorization, scheduling, and memory. Model function calls are requests for the application to execute; parallel function calls do not provide a Windows job scheduler or permission boundary. [Function calling](https://ai.google.dev/gemini-api/docs/function-calling)
- Fine-tuning can remain a conditional future phase, but it cannot currently be promised through the Gemini Developer API. Separate personalization/memory from changing model weights. [Developer API tuning](https://ai.google.dev/gemini-api/docs/model-tuning)

## Python/API and streaming

Google recommends the GA Google GenAI SDK (`google-genai`, `from google import genai`), replacing older libraries. Its official Python reference includes async clients and explicit resource closing. It also warns that SDK defaults use beta endpoints; API version, SDK version, and model release status are separate choices. [Libraries](https://ai.google.dev/gemini-api/docs/libraries), [Python SDK](https://googleapis.github.io/python-genai/)

Current Interactions documentation says this API became GA in June 2026 and recommends it for new projects; `generateContent` remains supported as a legacy API. This is a material change from older blueprints. Stateful history is optional; tools, system instructions, and generation settings must be supplied again for each interaction. [Interactions overview](https://ai.google.dev/gemini-api/docs/interactions-overview)

Streaming includes text and client function calls. Accumulate partial argument JSON by step/call, wait for a complete step, then validate and authorize before execution. Return each result against its `call_id`. The API supports multiple independent calls and sequential composition; the local application decides which can actually run concurrently. Preserve provider-required history/signatures. [Streaming](https://ai.google.dev/gemini-api/docs/streaming), [Function calling](https://ai.google.dev/gemini-api/docs/function-calling)

Documentation discrepancy worth a later integration test: the function-calling streaming example checks delta type `arguments`, while the dedicated streaming guide documents `arguments_delta`. Pin the SDK and test the selected endpoint's real event contract before building the UI around either spelling. The streaming guide also documents `interaction.completed` with `requires_action`; stream termination alone is not proof the user's task finished. [Function-calling example](https://ai.google.dev/gemini-api/docs/function-calling#stream-tool-calls), [Streaming events](https://ai.google.dev/gemini-api/docs/streaming)

If retaining `generateContent`, disable SDK automatic function calling for desktop actions: direct Python callables may otherwise execute automatically. The SDK exposes a configurable automatic-call limit, which is not a substitute for application policy. [Python SDK](https://googleapis.github.io/python-genai/)

## Cancellation and concurrent jobs

Interactions background mode works for standard models and returns an ID for polling, streaming, and reconnection. Explicit cancellation stops a server task, with a possible cleanup delay before `cancelled` appears; deletion removes its stored record. Background mode requires stored interactions. [Background execution](https://ai.google.dev/gemini-api/docs/background-execution), [Storage constraints](https://ai.google.dev/gemini-api/docs/interactions-overview)

Design inference: stopping local stream consumption must not be treated as proven server cancellation, local process termination, or undo. JASON needs distinct cancellation for inference, queued/running local tools, and the entire job. Already performed side effects require explicit status/reconciliation; retries must not blindly replay them. The sources establish server cancellation but do not promise rollback of external tools.

## Stable versus preview model choice

The official catalog, updated 2026-10-28, lists stable `gemini-3.8-flash`, `gemini-3.5-flash-lite`, and `gemini-4-argon`; it recommends recent Flash models for new projects and limits 2.5 access to established users. Prefer a specific stable model over a moving `latest` alias. Preview versions can have restricted quota and short deprecation notice. These are catalog facts, not a selection for JASON. [Models and version patterns](https://ai.google.dev/gemini-api/docs/models)

The individual 3.8 Flash page, updated 2026-10-30, confirms function calling, text output, multimodal input, a 1,048,576 input-token limit, and a 65,536 output-token limit. It explicitly says Live API is unsupported and `minimal` thinking is invalid. Terminal text streaming therefore does not require Live/voice API assumptions. No model quality or latency benchmark was run. [3.8 Flash specification](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash)

## Quota and spending

Rate limits are project-wide, not independent per key, and include request and token limits. Active limits are project/tier specific and visible in AI Studio; advertised capacity is not guaranteed. Preview limits can be tighter. Concurrent jobs need a shared limiter, backoff, and bounded context/output/tool loops. [Rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)

AI Studio offers project monthly spend caps, currently experimental with roughly ten-minute processing latency; long tasks can overshoot. Prepay and auto-reload controls also exist. Application budgets should reserve estimated cost before admission, reconcile reported usage, and stop admitting work at limits. [Billing controls](https://ai.google.dev/gemini-api/docs/billing)

Current standard 3.8 Flash text rates are $0.75 input and $3.75 output per million tokens through 2026-12-31, rising to $1.50/$7.50 on 2027-01-01; output pricing includes thinking. Search/caching can add charges. This is an example for budget planning, not a guaranteed project quote. The invite-only Contributor tier explicitly allows product improvement even when paid, unlike standard paid inference; confirm the actual service tier. [Pricing](https://ai.google.dev/gemini-api/docs/pricing)

## Cloud data use and retention

Unpaid service terms permit product improvement and human review and prohibit submitting sensitive/confidential/personal information. Standard paid terms say prompts/responses are not used to improve products but allow safety logging and international processing. Terms restrict use to professional/business development, require adults, and require appropriate supervision for agentic services; they forbid automatically bypassing human-confirmation requests. Confirm intended audience/use before final provider choice. [Terms, effective 2026-03-23](https://ai.google.dev/gemini-api/terms)

Paid inference is not zero-retention: the separate abuse-monitoring page specifies 55-day retention of prompts, contextual information, and outputs. [Abuse monitoring](https://ai.google.dev/gemini-api/docs/usage-policies)

Interactions additionally defaults to stored objects: paid 55 days, free one day; paid project-storage retention can be shortened. `store=false` disables this object storage and prevents background execution and chained `previous_interaction_id`. This control does not establish exemption from the separate safety-retention policy. [Interactions retention](https://ai.google.dev/gemini-api/docs/interactions-overview)

## Fine-tuning and later customization

The Developer API/AI Studio tuning page (updated 2026-04-28) says no supported fine-tunable model remains after 1.5 Flash retirement and no immediate return is planned. Its old tuning-related terms do not establish current feature availability. [Developer API tuning](https://ai.google.dev/gemini-api/docs/model-tuning)

Google's Gemini Enterprise Agent Platform separately supports supervised tuning for a limited model list (currently 3.5 Flash/Flash-Lite, 3.1 Flash-Lite, and selected 2.5 models; not 3.8 Flash in this list). Constraints include JSONL datasets up to 1 GB, model-specific serving/tuning regions, and no SLA SLO coverage for tuning. SFT guidance recommends minimal/no thinking for tuned tasks; it is not a blanket upgrade to general reasoning. [Supervised tuning](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/tuning/supervised-tuning)

Design recommendation: begin with editable instructions, user preferences, retrieval, tool descriptions, and explicit memory controls. Later fine-tuning should require an approved dataset, held-out evaluation, consent/retention rules, and evidence of a repeatable behavior gap. Do not promise exportable Gemini weights or continuous self-training.

## Questions only the user can answer

1. Is Gemini mandatory, or may a later small evaluation decide? Is this for personal use, professional work, or distribution to other users?
2. Which file contents, screenshots, browser data, and tool output may leave the PC? Is standard paid cloud processing and documented retention acceptable, or is stricter retention/local inference required?
3. What monthly and per-task spending limit should be enforced, and how should JASON behave when it reaches a limit?
4. Does customization mean personality/preferences, searchable personal knowledge, better repeatable workflows, or actual training? Is later enterprise cloud setup/training expense acceptable?
5. Should a long job continue after terminal disconnection? What must Stop cancel, and may it leave an already performed change in place?

No credentials were requested or inspected, and no live paid request was made. Recheck model access, pricing, terms, retention, SDK events, and project quota immediately before implementation approval.
