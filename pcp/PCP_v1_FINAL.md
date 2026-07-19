# PCP — Personal Context Protocol
## v1 Final Doc — the idea, the bet, and where it stands

> **Audience:** the team + any collaborator (human or AI) picking this up cold.
> **Purpose:** the single "what is PCP and why" reference. For *how we build it*, see `PCP_ARC.md`.
> **Status:** finalized v1 · a living doc — update as results land.

---

## 0. TL;DR

PCP is a **personal memory layer for LLMs, served over MCP.** Everything a user has ever told an AI lives in a **git-versioned, human-readable wiki** (an Obsidian-compatible vault). Memory is not a vector lookup — it is a **symmetric, orchestrated process**:

- A **Writer** files each memory into a **self-describing folder tree**, deciding *where* it belongs by descending the tree.
- A **Retriever** finds it back using the **same descent logic**, run in parallel with dense / keyword / grep search.
- A **Gatekeeper** model curates what actually reaches the host — dropping stale, contradictory, or irrelevant memories, and abstaining when nothing exists.

The host model (any model — Gemini, Claude, GPT, a local model) sees only two tools: **`Save`** and **`Recall`**. Everything else is invisible behind them.

**The identity:** PCP is a *personal context* system, and it is measured on *personal context*. The headline benchmark is **PersonaMem-v2**, where frontier LLMs manage only 37–48% and **no memory system has published a number at all.**

---

## 1. The problem

LLMs have **amnesia** — every session starts from zero. The industry fix is almost universally one shape:

> extract facts → embed as vectors → retrieve semantically similar chunks (RAG).

On **personal context** this has four documented, structural failures:

| Failure | What it looks like | Evidence | PCP's answer |
|---|---|---|---|
| **Aggregation** | can't combine facts spread across sessions ("how many times did I mention X?") | Mem0 paper | topic tree + agentic traversal + fusion |
| **Temporal / updates** | returns the *stale* value after something changed | Zep built a temporal KG for this | git history: files = now, `git log`/`diff` = how it changed |
| **Lossy compression** | summaries lose detail, no way back | *Verbatim Chunks Beat Extracted Artifacts* | provenance drill-down to the raw chat |
| **No abstention** | always returns *something*, even when it knows nothing | LongMemEval abstention split | Gatekeeper verified-absence from the retrieval trace |

**Our bet:** the fix isn't a better retriever — it's a better **organization + navigation + curation** layer. Structure memory like a versioned filesystem a human could read; let capable models *file, navigate, and curate* it instead of cosine-matching it.

---

## 2. What PCP is (and is not)

**PCP is:**
- A **protocol** (two MCP tools: `Save`, `Recall`) any host model plugs into.
- A **self-describing tree of memories** where the index *is* the folder structure — every folder carries a card (description + keywords + KV notes) summarizing its subtree.
- A **multi-retriever + Gatekeeper** pipeline that fuses tree-descent, dense, keyword, and grep signals and curates the result.
- **Private, portable, auditable:** it's a git repo and an Obsidian vault. Memory, models, and indexes can live entirely on the user's machine.

**PCP is not** (we say this plainly so no one overclaims):
- Not the inventor of filesystem/markdown memory (Karpathy's *LLM Wiki*, ByteRover).
- Not the inventor of the memory tree — that's the **MemTree / RAPTOR** family. *Our differentiator is edge-traversal descent that's symmetric with the writer, plus fusion + Gatekeeper + git provenance — measured on personal context.*
- Not the inventor of git-backed memory (**DiffMem** ships one) — but DiffMem has **no benchmark numbers anywhere** (§5).
- Not claiming a novel storage mechanism, and not using the word "novel" loosely.

**One-line pitch:**
> *A git-versioned, provenance-linked personal memory engine — a symmetric tree index with multi-retriever fusion and a curation gatekeeper over a human-readable wiki — the first memory system measured on implicit personalization, and served over MCP.*

---

## 3. The claims we will measure

### Claim 0 — Headline: a Personal Context Protocol, measured on personal context 🏆
PCP is judged on **PersonaMem-v2** (implicit personalization). Frontier long-context LLMs score **37–48%**; the paper's own *trained* 4B-with-memory beats GPT-5 long-context; **no external memory system has any number.** Target: **beat 48% prompted, approach/pass ~55%** — while staying model-agnostic, private, and auditable (their trained model can only serve itself; PCP serves any host over MCP).

### Claim 1 — Mechanism: version-history navigation as the temporal layer
A versioned filesystem + an agent that reads history can match a temporal knowledge graph on temporal/update questions, at a fraction of the infrastructure. Reported on the labeled **update-chain subset** with **tokens/query** as a co-equal metric. *Git is plumbing we prove works — not the identity we defend.*

### Claim 2 — Mechanism: navigation-grounded abstention
Abstention as **calibrated proof-of-absence** from the retrieval trace (what was searched, what agreed, what the Gatekeeper found), not a similarity threshold. Reported with **risk–coverage / ECE / reliability** curves — a demoable "it knows when it doesn't know" result no vendor self-report can imitate.

---

## 4. Benchmarks & the competitive landscape

### The stack
| Role | Benchmark | Why | State |
|---|---|---|---|
| **Headline** | **PersonaMem-v2** | personal-context identity; implicit preferences over long histories | frontier 37–48%; **memory-system leaderboard empty** |
| **Rigor** | **LongMemEval** (`longmemeval-cleaned`) | industry standard; the temporal/update/abstention splits | Zep 71.2 (temporal 63.8); vendor self-reports 94–95 (uncontrolled) |
| **Checkbox** | **LoCoMo** | lingua franca | near-saturated (ByteRover 96.1, Mem0 91.6) — report, don't chase |
| **Ownable** | **Real personal archive** (ours) | messy multi-year cross-tool data + a labeling protocol | unique to us |

### Where the git-versioned competitor stands: **DiffMem → nowhere**
DiffMem (git + markdown, ~896★, production) is our closest overall prior. Its leaderboard standing, verified three ways: **no numbers in its repo**, **absent from the public LongMemEval leaderboard**, and **unmentioned in the field's 2026 state-of-memory report.** The mechanism exists in production; the measurement does not exist anywhere. That gap is Claim 1.

### Leaderboard reality (why our numbers are reported differently)
The public "leaderboard" is **vendor self-reports** under undisclosed harnesses; independent work (*Is Grep All You Need*) shows the **harness dominates the retrieval algorithm**, making cross-paper score comparisons near-meaningless. So: **we reproduce every baseline ourselves, under one fixed reader model and one harness, and publish it.** In a field of self-reports, a controlled open harness is itself a contribution.

### Who we compare against (all under our fixed reader/judge)
Vanilla vector RAG (floor) · **Mem0** (the default, vector+graph+KV) · **Zep/Graphiti** (temporal-KG leader) · **Letta/MemGPT** (stateful runtime) · **Cognee** (graph — and our future graph layer) · **ByteRover** (filesystem SOTA on LoCoMo) · **PCP**.

---

## 5. Models
- **Host / Writer / Gatekeeper / reader / judge:** Gemini 3.5 Flash (temperature 0).
- **Embeddings:** Gemini Embeddings + BGE-Large (dual, compared).
- **Ablation tier (subset runs):** Qwen3-4B, Qwen3-32B, Grok 4.5 — to plot quality-vs-model and prove PCP isn't model-locked.
- **Frontier-first:** we iterate on strong models; no tiny embedders in the critical path.

---

## 6. Product & deployment vision
- Ships as a **local / self-hosted MCP server** (stdio now, streamable-HTTP + auth later). Configured into any MCP host in one line.
- **Tiny tool surface:** `Save`, `Recall` (+ `Recall_source` / `Recall_full` for provenance drill-down). The whole pipeline is internal — the host never sees `ls`/`grep`.
- **Privacy is the point:** memory, models, and indexes never leave the user's machine. **Portable** (a git repo), **auditable** (`git log`), **editable** (an Obsidian vault).
- **Roadmap:** local → self-hosted → hosted product. The research scope ends at "local."

---

## 7. The honest risks (name them before a reviewer does)
1. **Cost / latency.** Multi-retriever + a frontier Gatekeeper on every recall + card propagation on every save is heavy. If PCP costs many× a single-substrate system, the "fraction of infrastructure" story weakens. **Tokens/query is a first-class metric from day one.**
2. **Crowded field.** Protection = the honest "measure, don't invent" framing and the empty PersonaMem leaderboard.
3. **Novelty.** The tree is MemTree/RAPTOR family — win on the *combination* and the *measurement*, not the tree.
4. **Real-data rigor.** The archive has no gold labels; the contamination-controlled labeling protocol is what turns a demo into a finding (and may be a contribution in its own right).

---

## 8. Glossary
- **`Save` / `Recall`** — the two MCP tools the host model calls.
- **Node card (`_card.md`)** — description + keywords + KV notes on every folder; summarizes its subtree; what the grader scores.
- **Grader descent** — recursive ANN+BM25+grep+ls scoring of cards, root → leaf. Same logic for Save and Recall (the *symmetry principle*).
- **Fusion** — combining tree-descent + dense + BM25 + grep results (RRF + agreement boost).
- **Gatekeeper** — the frontier model that filters stale/negative memories, curates the package, and abstains.
- **Provenance drill-down** — `Recall_source` (raw messages) / `Recall_full` (whole chat) behind memory IDs.
- **Temporal checkout** — `git checkout` the memory as-of any past moment; free from per-message commits.
- **PCP-lite** — the faithful day-1 subset of the full architecture (see `PCP_ARC.md`).

---
*v1 Final — the idea is sound and the window is open. Build, measure, update this doc as results land.*
