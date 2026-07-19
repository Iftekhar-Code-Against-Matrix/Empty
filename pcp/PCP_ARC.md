# PCP — Architecture & Build Doc (`PCP_ARC.md`)
## What we're building, why, in what order, and the expected outcome at each stage

> **Audience:** the team + collaborators. **Companion to** `PCP_v1_FINAL.md` (the idea/claims).
> **This doc answers:** what each part *is*, *why* it exists, *what PCP-lite is*, *what we compare against*,
> and the **full sequenced plan** (no dates — just order: first this, then that, then maybe this/that, later optical & graph),
> with the **expected outcome** at every stage.

---

## PART A — THE SYSTEM

### A.1 One picture
```
   HOST MODEL (Gemini 3.5 Flash) —— sees only two tools ——►  Save(...)   Recall(...)
        │                                                        │
        ▼ SAVE                                                   ▼ RECALL
  ┌──────────────────────────┐                     ┌──────────────────────────────────────────┐
  │ WRITER                    │                     │ 4 RETRIEVERS (parallel)                   │
  │  distill episodic memory  │                     │  1 tree-descent (edges)                   │
  │  + KV notes (BM25/grep/ANN)│  ── same descent ──►│  2 dense over leaves                       │
  │  place via GRADER DESCENT │   (symmetry)        │  3 BM25 over leaves                        │
  │  update card + propagate  │                     │  4 agentic grep / git grep                │
  └──────────┬───────────────┘                     └───────────────┬──────────────────────────┘
             ▼                                                      ▼
   ┌──────────────────────────────┐                       ┌─────────────────────┐
   │ STORE: self-describing tree   │                       │ FUSION (RRF+agree)   │
   │  memories/<branch>/<sub>/…    │◄──────────────────────│ qualified + maybe    │
   │  each folder has _card.md      │      git repo         └──────────┬──────────┘
   │  chats/ = raw layer (provenance)│     Obsidian vault              ▼
   └──────────────────────────────┘                        ┌─────────────────────┐
                                                            │ RERANKER → GATEKEEPER│
                                                            │ filter stale/negative│
                                                            │ curate → JSON package│
                                                            └──────────┬──────────┘
                                                                       ▼  curated package / abstention
                                                                  reader answers
```

### A.2 The two paths (and the invariant that ties them)
- **Save:** host calls `Save(special_instructions, chat_metadata + context)` mid-chat when it judges something worth keeping → Writer distills it, writes KV notes, and **descends the tree to place it** (update an existing leaf if diff-compatible; create a new subfolder if genuinely new), then updates cards up the branch.
- **Recall:** host calls `Recall(special_instructions, context)` → the **same descent** finds candidate leaves, run in parallel with dense/BM25/grep → fusion → Gatekeeper → curated package (or abstention).
- **Symmetry principle (the invariant):** *the logic that decides **where to Save** is the logic that decides **where to Recall**.* A memory is findable because it was filed by the exact process that looks for it. This is the backbone of the whole design.

### A.3 Components — what & why
| Component | What it is | Why it exists |
|---|---|---|
| **Store (tree)** | `memories/` folders; each has `_card.md` (description + keywords + KV notes + child summaries); `chats/` = append-only raw layer | The index *is* the structure — human-auditable, no training, Obsidian-native |
| **Node cards** | per-folder summary the grader scores | lets the grader prune correctly at every level; BM25/ANN/grep/ls-friendly |
| **Upward propagation** | on write, update the leaf **and every ancestor card to root** | every ancestor summarizes its subtree → descent stays accurate as the tree grows |
| **Grader descent** | recursive ANN+BM25+grep+ls over cards, keep top-k branches | the shared Save/Recall core; edges do work (unlike MemTree/RAPTOR's collapse) |
| **Writer** | frontier model: distill + KV notes + placement + provenance | quality of writing = quality of the index; **implicit-preference capture wins PersonaMem** |
| **4 retrievers** | tree-descent, dense-over-leaves, BM25, agentic grep — in parallel | different failure modes; grep runs *while* the tree descent computes |
| **Fusion** | RRF + agreement boost → qualified candidates + a "maybe" pool | agreement across methods raises confidence without hard-gating (intersection can be empty) |
| **Reranker** | BGE cross-encoder | cheap relevance ordering → shortlist, *before* the Gatekeeper; independently ablatable |
| **Gatekeeper** | frontier model → JSON `{pass, drop, reason}` + curated digest | filters **stale/contradictory/negative** memories (via `git diff`), abstains, and curates — the anti-hallucination gate |
| **Provenance** | memory frontmatter → source message IDs; `Recall_source`/`Recall_full` | reversible compression: drill down to raw/full chat on demand |
| **Git** | per-message raw commits; per-write memory commits | temporal layer (`log`/`diff`) + free **temporal checkout** (as-of-past-state) |
| **Graph (deferred)** | Cognee or Obsidian backlinks as a 5th retriever | multi-hop reasoning — an *experiment*, off by default |

### A.4 Reranker vs Gatekeeper — why they're split
Relevance and truth/freshness are **different axes.** A reranker knows *topically relevant*; only the Gatekeeper knows *superseded last week / contradicts a newer note / false-premise trap*. Splitting them is cheaper (don't burn a frontier model sorting), independently ablatable, and cleanly separates "relevant" from "true" — the exact distinction that stops stale-info leakage.

---

## PART B — WHAT IS "PCP-LITE"

The full architecture (A.1–A.4) is the destination. **PCP-lite is the faithful minimum-viable spine** we build first, so we get scored numbers on all three benchmarks fast without waiting on the whole system.

| Full v2 | PCP-lite (first build) | Why the cut is safe |
|---|---|---|
| Card tree + full upward propagation | Card tree + **leaf+parent** propagation | descent still works; full propagation is a quality refinement |
| 4–5 retrievers | **3**: tree-descent + dense + grep | covers the main failure modes; BM25/graph add margin later |
| Reranker stage | optional | fusion + Gatekeeper carry ranking initially |
| Gatekeeper (filter + curate + git-staleness) | **filter + curate** (skip git-diff staleness) | staleness reasoning is additive |
| 6 baselines | **vanilla RAG only** | goal is *PCP scored on 3 benchmarks*, not a baseline suite, on day one |
| Local (llama.cpp) serving | **API models** | serving is an ops task, not a research variable yet |

**PCP-lite is not a different design — it's the same spine with the optional layers turned off.** Every deferred piece slots into the same seams.

---

## PART C — THE SEQUENCED PLAN (order, not dates)

> Read as: *first this → then that → then try this or that → maybe this → later optical & graph.*
> Each stage states **what we build**, **why**, and the **expected outcome**.

### Stage 0 — PCP-lite spine + 3 benchmark subsets  *(first)*
- **Build:** store + cards + shared descent → Writer → 3-retriever fusion + Gatekeeper → reader; adapters for LongMemEval, PersonaMem-v2 (MCQ), LoCoMo; caching + reproducibility from line one; vanilla-RAG baseline.
- **Why:** prove the spine end-to-end and get real numbers on the smallest slice before scaling anything.
- **Expected outcome:** {RAG, PCP-lite} scored on 3× subsets (per-type for LongMemEval) with tokens/latency/cost; traces saved. **Signal we want:** PCP-lite clearly beats vanilla RAG, and **beats ~48% on PersonaMem-v2 MCQ** (frontier ceiling). If yes → the core thesis holds and everything after is refinement.

### Stage 1 — Full v2 + credible baselines  *(then)*
- **Build:** full upward propagation, BM25 (4th retriever), reranker stage, Gatekeeper git-staleness reasoning, `Recall_source/full`. Stand up **Mem0**, then **Zep, Letta, ByteRover** under the fixed harness. Run **full** benchmarks (not subsets).
- **Why:** vanilla RAG is a strawman; credibility comes from beating the systems reviewers know. Full runs replace dev-subset noise with reportable numbers.
- **Expected outcome:** first real per-split tables vs the field, and the **accuracy-vs-cost Pareto plot** (our headline figure). **Signal:** PCP competitive-or-better on accuracy at materially lower cost/infra than graph/KG systems.

### Stage 2 — Mechanism claims + ablations  *(then)*
- **Build:** Claim 1 (±git-tools on the labeled update-chain subset, + temporal-checkout replay); Claim 2 (Gatekeeper confidence → risk–coverage / ECE calibration); the full **ablation grid** (±reranker, ±each retriever, ±Gatekeeper, ±propagation, model tier, embeddings).
- **Why:** turn "it works" into "we know *why* it works, and each part earns its place."
- **Expected outcome:** a defensible contribution table — what each component contributes, where git helps (and at what token cost), and a calibrated abstention curve no vendor can match.

### Stage 3 — Headline hardening + the ownable testbed  *(then)*
- **Build:** PersonaMem-v2 **full + open-ended track**; push the **Writer's implicit-preference distillation** (where the headline number is really won). Build the **real personal-archive** ingestion adapters + contamination-controlled **labeling protocol**.
- **Why:** the headline benchmark and the data nobody else has are what make PCP *ours*, not a reproduction.
- **Expected outcome:** the strongest possible PersonaMem number + a first result on real multi-year personal data. The labeling protocol ("turn any personal archive into a memory benchmark") may become a contribution on its own.

### Stage 4 — Scale, package, write-up  *(then)*
- **Build:** scaling curve (grow the tree 1×/10×/100×; navigation success / tokens / latency / `git log` cost vs RAG's flat curve); **containerize** the local MCP server; the write-up (tables + CIs, ablations, Pareto figure, prior-art honesty, limitations, released harness).
- **Why:** show it holds as memory grows, make it runnable by others, and land the result.
- **Expected outcome:** a complete, reproducible story: PCP scales where flat RAG degrades, runs as a one-line local MCP server, with an open harness.

### Stage X — Experiments to *try* (parallel / opportunistic — "maybe this or that")
> Not on the critical path. Attempt when a stage is ahead of schedule or a result motivates it. Each is ablatable and off by default.
- **Cognee graph as a 5th retriever** *(try after the core works)* — plug into the same fusion stage; **expected outcome:** measured Δrecall/precision on multi-hop questions; keep only if it pays.
- **Optical / image-based retrieval on the return path** *(later, maybe)* — render the memory package as an image (DeepSeek-OCR-style) to cut host tokens; **expected outcome:** same accuracy at fewer host tokens, or we drop it. Prior art exists — it's an ablation, never a pillar.
- **Trace distillation into the small models** *(only if a tier plateaus)* — SFT Qwen on successful Writer/Retriever traces; **expected outcome:** small-model quality approaching frontier at lower cost.
- **Retrieval-optimal writing** *(stretch, parked)* — reward the Writer on downstream recall success; **expected outcome:** a self-improving write path — a project of its own.

---

## PART D — WHAT WE COMPARE AGAINST
Every system runs under the **same fixed reader + judge**:
`vanilla RAG` (floor) → `Mem0` (default) → `Zep/Graphiti` (temporal-KG) → `Letta/MemGPT` (runtime) → `Cognee` (graph, also our future layer) → `ByteRover` (filesystem SOTA) → `PCP`.
The number that matters is not a single leaderboard cell — it's the **accuracy-vs-cost frontier**, quality first.

## PART E — RISKS WE STEER BY
1. **Cost/latency** can quietly kill the Pareto claim → tokens/query is first-class from Stage 0.
2. **Greedy descent** can pick the wrong branch → keep top-k branches; parallel dense/grep are the safety net; measure route-miss.
3. **Novelty overclaim** → tree = MemTree/RAPTOR; we win on edge-traversal + fusion + Gatekeeper + git + personal-context measurement, and we say so first.
4. **Write quality is the real lever** → both the temporal split (dates in notes) and the PersonaMem headline (implicit preferences) are won in the Writer, not the retriever.

---
*Build the spine, prove it beats the frontier ceiling, then earn every added layer with a measurement.*
