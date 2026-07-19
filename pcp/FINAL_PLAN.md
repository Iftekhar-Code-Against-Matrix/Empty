# PCP — Final Plan (locked 2026-07-17)
> The single roadmap. Architecture: `PCP_ARCHITECTURE_v2.md`. Benchmarks: `BENCHMARKS.md`.
> Day-1 build: `WEEKEND_BUILD.md`. Claims/eval rigor: `PCP_RESEARCH_v1.md` (v1.2).

## Locked decisions
- **Identity:** a Personal Context Protocol. Headline benchmark = **PersonaMem-v2** (beat 48% → chase 55%). Rigor benchmark = **LongMemEval-cleaned**. Checkbox = **LoCoMo**.
- **Architecture:** symmetric tree-index (Writer places / Retriever descends, same logic) → 4-retriever fusion → **reranker ranks, Gatekeeper filters+curates** → curated package over MCP. Git + Cognee-graph = pluggable, deferred. Tree cited as **MemTree/RAPTOR** family; differentiator = edge-traversal + fusion + Gatekeeper + provenance, on personal context.
- **Models:** host/Writer/Gatekeeper/reader/judge = **Gemini 3.5 Flash** (temp 0); embeddings = **Gemini + BGE-Large**; ablation tier = **Qwen3-4B/32B, Grok 4.5**.
- **Baselines:** day-1 = vanilla RAG; wk1 add **Mem0**; wk1–2 add **Zep, Letta, Cognee, ByteRover**. Same fixed reader/judge for all.
- **Discipline:** one harness, seeded subsets → overnight full runs, disk-cached calls, append-only results w/ config hash, tokens/latency/cost logged everywhere.

## Day 1 (today) — PCP-lite spine, 3 benchmark subsets
Per `WEEKEND_BUILD.md`: pre-flight (keys/cap/data/cache) → store+cards+shared descent → Writer → 3-retriever fusion + Gatekeeper → reader → LME/PersonaMem/LoCoMo adapters. **Deliverable:** {RAG, PCP-lite} scored on 3× N=100 subsets (per-type for LME), tokens/latency/cost, traces saved; full runs launched overnight. **Headline check:** PCP-lite vs 48% on PersonaMem MCQ.

## Week 1 — full v2 + credible baselines
- Complete v2: **full upward card propagation**, **BM25 as 4th retriever**, **BGE reranker** stage, Gatekeeper **git-diff staleness** reasoning, `Recall_source/full` drill-down tools.
- Baselines: **Mem0**, then **Zep, Letta, ByteRover** under the fixed harness.
- **Full runs** (not subsets) on all 3 benchmarks; first real per-split tables + **accuracy-vs-cost Pareto** plot.
- Weeknight: finish the **LongMemEval C-subset labeling** (211-row sheet in `pilot/`) for the git contribution slice.

## Week 2 — mechanism claims + ablations
- **Claim 1 (git temporal):** ±git-tools on the labeled update-chain C-subset, report accuracy **and tokens/query**; temporal-checkout replay (as-of-session-k).
- **Claim 2 (abstention):** Gatekeeper confidence → **risk–coverage / ECE / reliability** curves vs similarity-threshold baseline.
- **Ablation grid:** ±reranker · ±each retriever (tree/dense/BM25/grep) · ±Gatekeeper · ±card-propagation · orchestrator tier (Gemini vs Qwen3-4B/32B vs Grok) · embeddings (Gemini vs BGE-Large).
- **Cognee graph experiment:** plug in as 5th retriever, measure Δ on multi-hop.

## Week 3 — headline hardening + real archive
- **PersonaMem-v2 full + open-ended track** (paper's LLM-judge rubric); push the **Writer's implicit-preference** distillation — this is where the headline number is won.
- **Real personal archive:** ingestion adapters (ChatGPT/Claude/Cursor exports) + contamination-controlled **labeling protocol** (≥100 QA incl. update-chains, abstention). The ownable testbed.
- Optional Phase-2 trace distillation only if a model tier plateaus.

## Week 4 — scale, package, write-up
- **Scaling curve:** grow tree 1×/10×/100× nodes; navigation success / tokens / latency vs RAG's flat curve; `git log`/checkout latency at scale.
- **Containerize** the local MCP server (mounted vault, endpoint configs); one-line install path.
- **Write-up:** per-split tables + CIs, full ablations, **Pareto headline figure**, prior-art honesty (MemTree/RAPTOR/DiffMem/Zep), limitations (§4.3 drawbacks + cost/latency risk), released harness. Save all `runs/` for future **image/optical retrieval** + graph experiments.

## The three risks to watch (from the sanity check)
1. **Cost/latency** — 4 retrievers + frontier Gatekeeper + O(depth) card writes can blow the "fraction of infra" Pareto claim. Tokens/query is a first-class metric from day 1.
2. **Greedy descent wrong-branch** — keep top-k branches; parallel dense/grep are the safety net; measure route-miss.
3. **Novelty overclaim** — tree = MemTree/RAPTOR; win on edge-traversal + fusion + Gatekeeper + git + personal-context measurement. Say it first.
