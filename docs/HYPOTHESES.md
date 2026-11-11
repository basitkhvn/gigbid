# Pre-registered hypotheses (written before results files were committed)

Earlier 15-job smoke checks on the ML persona (not reported as results) showed decomposition helping and plain hybrid hurting; the hypotheses below were written after that smoke check but before any full evaluation run was saved to `evals/results/`.

**B (RAG).** H-B1: requirement decomposition plus hybrid retrieval plus cross-encoder rerank (`v_best`) raises evidence Recall@5 by >= 15 points over V0 on jobs with >= 4 requirements. H-B2: *plain* hybrid (V2, whole job post as the query) does NOT beat V0, because BM25 over a long multi-requirement post is dominated by generic words. H-B3: outcome-aware boosting (V4) improves reply rate in GigSim but not Recall@5 (it optimises something other than relevance).
**A (tools).** H-A1: coarse tools (4 tools with an `action` argument) lose argument accuracy versus the fine-grained set; the rewritten-description set is best on selection accuracy and uses fewer tokens than fine-grained.
**C (architecture).** H-C1: the hand-built graph beats a single ReAct agent on unsupported claims and compliance catches, but the single agent is competitive on bid-or-skip accuracy for easy jobs and uses fewer tokens.
**E (safety).** H-E1: delimiting + sanitising + compliance reduces prompt-injection attack success rate from > 30% to < 5% on the planted-injection dev jobs.
