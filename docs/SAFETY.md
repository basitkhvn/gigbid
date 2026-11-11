# Safety and platform respect

**Never do:** send anything without human approval in GigBid (and confirmation on Upwork in live mode); spend Connects without approval; fabricate experience; include contact details/guarantees/off-platform asks; scrape or automate a website; log PII or tokens.

| Rule | Enforcement | Where |
|---|---|---|
| Human approval | LangGraph `interrupt()`; executor only runs after resume; no auto-send mode exists (autonomy only auto-*skips*) | `agent/graphs/bid_graph.py` |
| Exactly-once send | deterministic idempotency keys + server-side idempotency store | `mcp_servers/marketplace/server.py`, test |
| Grounded claims | claim verification before Critic; unsupported claims removed; reported before/after | `rag/verify.py` |
| Injection | job text / client messages delimited as data, injected lines stripped before any model sees them, injection flagged in the risk report, system prompts say untrusted, Compliance filter on output | `agent/guard.py`, prompts |
| Least privilege | per-agent tool allowlists | `agent/mcp_client.py` |
| PII | emails/phones/cards/secrets masked in traces, logs and the audit log | `agent/pii.py` |
| Tokens | Fernet-encrypted per user, never logged | `apps/api/auth/tokens.py` |
| Tenancy | `user_id` in every app query and every marketplace tool call | `apps/api/db.py` |
| Polite automation | per-user rate limiter, scout interval >= 60 min (live: 30 s min between reads, recommended 4 h+) | marketplace server, worker |

## What still gets through (honest)
* Paraphrased injections that avoid the regex trigger phrases are not stripped; defence then relies on the model following the "untrusted data" instruction and on the Compliance filter. In the measured run the model resisted all 36 planted attacks even without the defences (see RESULTS), so **the experiment cannot show the defences' marginal value**; the planted attacks were my own four templates and are weak.
* Injection inside screening questions or client messages is delimited but only the job-post path was measured.
* Compliance is rule/regex based: novel off-platform phrasing ("ping me on Signal") passes.
* The semantic grounding check can accept a claim that is related-but-not-identical to its cited evidence (relevance threshold -3.0).
