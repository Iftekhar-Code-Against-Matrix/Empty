# PCP — Weekend Build (v2, aligned to `PCP_ARCHITECTURE_v2.md`)
> v2.0 · 2026-07-17 · supersedes weekend-build v1 (which described the drifted "one 4B greps git" design)
> **What survived from v1:** all the *plumbing* (§A). **What changed:** the *retrieval brain* (§B).

---

## A. Reusable scaffolding (was right in v1, keep it)
1. **Benchmarks-as-config:** a benchmark = `(ingest adapter, question loader, scorer)`; store/Writer/Retriever/reader shared. Each new benchmark ≈ 1h adapter.
2. **One fixed reader + judge model for EVERY system** (anti-cheating rule).
3. **Seeded stratified subsets first (dev sets, N stated) → overnight full runs.** A finished N=100 number is real; an unfinished full run is nothing.
4. **Append-only `results/` with config hash**; per-stage tokens/latency/cost logged; go/no-go gate; hard spend cap set Saturday AM.
5. **PCP is an MCP server**; the harness calls `Save`/`Recall` — dev == test == future product.

## B. What the weekend actually builds: **PCP-lite** (architecturally faithful subset of v2)
The full v2 (4 parallel retrievers + reranker + Gatekeeper + upward card propagation + 5 industry baselines) does **not** fit one weekend. PCP-lite keeps the *spine* and defers the rest — nothing here contradicts v2, it's a subset.

| v2 component | Weekend (PCP-lite) | Deferred to week 1–2 |
|---|---|---|
| Store = self-describing node-card tree | ✅ cards + **greedy top-k descent** | upward propagation to root (weekend: update leaf + immediate parent only) |
| Writer (place + KV notes + provenance) | ✅ | implicit-preference tuning pass (needed for PersonaMem headline) |
| Retrievers | ✅ **tree-descent + dense + grep** (3, in parallel) | BM25 as 4th, Cognee graph as 5th |
| Reranker (BGE cross-encoder) | ⚠️ optional if time | full ablation |
| Gatekeeper (frontier, filter/curate/JSON) | ✅ **filter + curate** | git-diff staleness reasoning, calibration |
| Models | Gemini 3.5 Flash (host/Writer/Gatekeeper); Gemini Embeddings + BGE-Large; reader/judge pinned | Qwen3-4B/32B, Grok 4.5 ablation tier |
| Provenance drill-down | ✅ IDs stored | `Recall_source/full` as MCP tools |
| Baselines | **Vanilla RAG only** (day 1) | **Mem0** (wk1), then Zep, Letta, Cognee, ByteRover (wk1–2) |

**Weekend goal:** PCP-lite + 2 baselines produce scored numbers on **LongMemEval, PersonaMem-v2 (MCQ), LoCoMo** — under one harness. Headline target: **PCP-lite > 48% on PersonaMem-v2 MCQ.**

---

## B.1 PRE-FLIGHT (first 30 min — do before writing pipeline code)
- [ ] **Keys + spend cap:** Gemini 3.5 Flash + Gemini embeddings working; **hard budget cap set in the provider dashboard** before any ingestion run.
- [ ] **Datasets pull (all verified public/ungated 2026-07-17):**
  - LongMemEval: HF `xiaowu0162/longmemeval-cleaned` (oracle/S). Schema: `question, question_type, answer, question_id (_abs=abstention), haystack_sessions, answer_session_ids`.
  - PersonaMem-v2: HF `bowen-upenn/PersonaMem-v2`, file **`benchmark/text/benchmark.csv`** + `data/chat_history_32k/*.json`. MCQ cols: `user_query, correct_answer, incorrect_answers`; per-persona history via `chat_history_32k_link`; bonus update signal in `updated`/`prev_pref`.
  - LoCoMo: **GitHub** `snap-research/locomo` → `data/locomo10.json` (10 convs, ~199 QA each). Schema: `qa:[{question, answer, evidence, category}]`, `conversation`. (HF mirror is README-only — use GitHub raw.)
- [ ] **Caching + repro on from line 1** (§B.2). 

## B.2 Caching + reproducibility (build these into the wrappers, not bolted on later)
- **Disk cache:** wrap every embedding + LLM call; key = `sha256(model + params + prompt)` → JSON on disk (`cache/`). Debug re-runs re-pay nothing after the first pass (turns LME's ~4,000 Writer calls into a one-time cost).
- **temperature = 0** for reader, judge, Gatekeeper, Writer (determinism).
- **Seeds pinned** (subset sampling, any shuffles) = 42.
- **Abstention path wired end-to-end:** empty Gatekeeper `pass` → package = "NO_MEMORY_FOUND" → reader outputs "the information is not available" → LME `_abs` judge scores it correct. Test one `_abs` question before the full run.

## C. Repo (aligned to v2)
```
pcp/
  configs/harness.yaml         # reader/judge, embeds (gemini+bge-large), models, seed, budgets
  src/pcp/
    store.py                   # node-card tree, per-msg raw commits, per-write memory commits
    cards.py                   # _card.md read/write; leaf+parent update (full propagation = wk1)
    writer.py                  # Save(): distill episodic + KV notes + place via descent + provenance
    descent.py                 # SHARED grader descent (ANN+grep+ls over cards) — used by Save & Recall
    retrievers.py              # tree_descent(), dense_leaf(), grep_leaf()  → run in parallel
    fusion.py                  # RRF + agreement boost → qualified + maybe pool
    gatekeeper.py              # frontier LLM → JSON {pass, drop, reason} + curated digest
    reader.py                  # fixed reader answers from package only
    mcp_server.py              # Save / Recall (stdio) — the seam everything calls
    cache.py                   # sha256(model+params+prompt) → disk; wraps all embed/LLM calls
    baselines/vanilla_rag.py   # day-1 baseline (Mem0 adapter = week 1)
  bench/{common.py, lme.py, personamem.py, locomo.py}
  run.py                       # run.py --bench lme --system pcp --subset 100 --mode A
  results/  runs/  stores/
```
`Save`/`Recall` and the shared `descent.py` are the whole point — build those first and correctly; everything else is adapters.

## D. Schedule (2 days, faithful-but-lite)

**Saturday — the spine**
| Block | Work |
|---|---|
| AM-1 | harness.yaml + `reader.py` + results/runs logging + spend cap. Pin Gemini Embeddings + BGE-Large. |
| AM-2 | `store.py` + `cards.py` + `descent.py` (the shared grader). Smoke: hand-build a 2-level tree, descend a query, watch it pick the right leaf. |
| PM-1 | `writer.py` `Save()` — distill + KV notes + place via descent + provenance. **Eyeball wiki quality on 3 real sessions; iterate the Writer prompt — highest-leverage hour.** |
| PM-2 | `retrievers.py` (tree+dense+grep parallel) + `fusion.py` + `gatekeeper.py` minimal. Wire `mcp_server.py` Recall. |
| Eve | `bench/lme.py` ingest 100-q subset (async, 8 workers) + `baselines/vanilla_rag.py`. **Gate: baseline sane on 20 Qs or debug.** |

**Sunday — numbers on all three**
| Block | Work |
|---|---|
| AM-1 | PCP-lite on the same 20 LME Qs; read every trace + Gatekeeper JSON. Fix obvious Writer/descent misses. |
| AM-2 | Full 100-q LME: vanilla RAG + PCP-lite → **first per-type table**. |
| PM-1 | `bench/personamem.py`: ingest + PCP-lite on 100 MCQs → **headline number** (Writer must emit `[implicit]` prefs). |
| PM-2 | `bench/locomo.py`: 100 QA → checkbox. |
| Eve | Launch overnight full runs; commit `results/` + `runs/`; push. |

## E. Model config (locked)
```yaml
host_model:        gemini-3.5-flash        # chats, calls Save/Recall
writer_model:      gemini-3.5-flash
gatekeeper_model:  gemini-3.5-flash
reader_model:      gemini-3.5-flash        # FROZEN — same for every system
judge_model:       gemini-3.5-flash        # LME/LoCoMo judge; PersonaMem MCQ needs none
ablation_tier:     [qwen3-4b, qwen3-32b, grok-4.5]   # subset runs only, week 1–2
embeddings:        [gemini-embeddings, bge-large-latest]   # dual; compare recall
reranker:          bge-reranker (cross-encoder)     # optional this weekend
seed: 42
subset: {lme: 100, personamem: 100, locomo: 100}
budgets: {max_steps: 12, max_tool_tokens: 2000, max_query_s: 120}
```
> Confirm exact provider IDs Saturday AM (gemini-3.5-flash, grok-4.5, qwen3-32b, gemini embedding model name). Set the spend cap before the first run.

## F. Definition of done (Sun night)
- [ ] Table: {vanilla-RAG, PCP-lite} × {LME-100 (per-type), PersonaMem-MCQ-100, LoCoMo-100}; cols = accuracy, tokens/q, latency, cost. Committed + pushed.
- [ ] Every number from `run.py` + config hash; `runs/` has traces + Gatekeeper JSON for reuse.
- [ ] 10 Recall traces human-read; failure buckets noted (write/route/nav-miss).
- [ ] Overnight full runs launched.
- **Deferred (not this weekend, and that's fine):** full card propagation, BM25 4th retriever, Cognee graph, git-diff staleness in Gatekeeper, abstention calibration, temporal-checkout replay, Qwen/Grok ablations, Zep/Letta/Cognee/ByteRover baselines, PersonaMem open-ended, local (non-API) serving, real personal archive.

## G. Weekend shortcuts (so they're never mistaken for the design)
1. Card propagation = leaf+parent only (full-to-root is wk1).
2. 3 retrievers not 4–5; no graph.
3. Gatekeeper filters/curates but skips git-diff staleness reasoning.
4. API models only; local llama.cpp swap later.
5. Subsets are dev sets; headline uses overnight full runs.
6. 2 baselines this weekend; the other 3 industry leaders in wk1–2 (they're what make it credible — don't skip them beyond wk2).
