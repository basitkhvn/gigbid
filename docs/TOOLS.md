# Tools (one row per MCP tool)

Annotations: RO = readOnlyHint, D = destructiveHint, I = idempotentHint. Auth: in-memory/stdio transports are in-process; HTTP transport requires `Authorization: Bearer $MARKETPLACE_MCP_TOKEN` (marketplace) . Signatures are snapshot-tested in `tests/contract/snapshots/tools.json`.

| Tool | Server | R/W | Annotations | Auth | Allowed agents |
|---|---|---|---|---|---|
| search_jobs | marketplace | read | RO I | bearer | scout, ui |
| get_job | marketplace | read | RO I | bearer | scout, risk, ui |
| get_client_history | marketplace | read | RO I | bearer | risk, ui |
| get_connects_balance | marketplace | read | RO I | bearer | pricing, executor, ui |
| get_price_stats | marketplace | read | RO I | bearer | pricing, ui |
| get_platform_policy | marketplace | read | RO I | bearer | pricing, ui |
| list_messages | marketplace | read | RO I | bearer | liaison, ui |
| list_proposals | marketplace | read | RO I | bearer | ui |
| create_proposal_draft | marketplace | write (draft; `dry_run` default true) | I | bearer + idempotency key | executor |
| submit_proposal | marketplace | write (spends Connects) | D I | bearer + idempotency key | executor (after human approval only) |
| send_message | marketplace | write | D I | bearer + idempotency key | executor (after human approval only) |
| search_evidence | portfolio | read | RO I | - | fit, writer, critic, liaison, ui |
| get_case_study | portfolio | read | RO I | - | fit, writer, critic, ui |
| list_skills | portfolio | read | RO I | - | fit, ui |
| free_slots | workspace | read | RO I | - | liaison |
| create_interview_hold | workspace | write (tentative) | I | idempotency key | liaison (after approval) |
| create_email_draft | workspace | write (draft only) | I | idempotency key | liaison |

Resources: `portfolio://case/{id}`, `portfolio://proposal/{id}`. Prompts: `answer_screening_question`, `draft_cover_letter`, `what_have_i_won_with`.

Write-tool guarantees: Pydantic input constraints; required idempotency key stored in sqlite (a retry returns the first result with `replayed: true`); `dry_run` preview with cost; per-user rate limiter below GigSim's own; append-only audit log (SQL triggers forbid UPDATE/DELETE) with PII masked and the trace id.

## Third-party servers and trust rationale
| Server | Used for | Trust rationale |
|---|---|---|
| Upwork official MCP (`https://mcp.upwork.com/mcp`) | live mode (A4) | First-party platform server; OAuth 2.1 scoped tokens; every write is a draft the user confirms on Upwork. Only via `UpworkLiveAdapter`; reads throttled (>= 30 s). *Not exercised live in this submission.* |
| GitHub MCP server | repo ingestion (B1) | Maintained by GitHub; read-only token with `public_repo` read scope only; allowlist `ingest` agent can call `github_get_file_contents` only. *Wired but not run here.* |

## Tool-design study
See docs/RESULTS.md (R&D question A) and the report. Rewritten descriptions + 12 tools was best on both selection and argument accuracy.
