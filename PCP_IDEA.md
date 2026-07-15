# PCP — Personal Context Protocol
### A deep, orchestrated, agentic memory engine over a versioned personal wiki — served over MCP

> **Status:** finalized idea doc (v0.3) · **Owner:** Iftekhar · **Date:** 2026-07-15
> **Audience:** PhD advisor + team members + AI collaborators picking this up cold.
> **v0.3 changes:** finalized layered architecture (Obsidian raw layer → git engine → fast router → agentic retriever), provenance drill-down (episodic → raw transcript), router stage replaces plain RAG-assist, optical compression formally deferred, MCP productization section added.

---

## 0. TL;DR (read this first)

PCP is a **personal memory layer for LLMs**. Everything the user has ever told an AI lives in a **git-versioned, human-readable wiki** (an Obsidian-compatible vault of markdown files). Retrieval is not a vector lookup — it is a **two-stage orchestrated process**:

1. A **fast router** (tiny model, target ~1000–1200 tok/s) instantly picks *where in the tree to look*.
2. A **small orchestrator (4B)** then **navigates agentically** — `ls`, `grep`, `cat`, and `git log`/`git diff` — until it has the precise memories that matter, or has *verified* that nothing exists.

- **Space** is indexed by the directory tree; **time** is indexed by git history — no temporal knowledge graph needed.
- **Compression is reversible:** every episodic memory carries a provenance link to the raw chat transcript it was distilled from, so the agent can drill down when the summary is too lossy.
- **Served as an MCP server** (local/self-hosted), so any host model — Claude, GPT, a local model — plugs into the same portable, private memory.

**What we honestly claim:** not a new storage mechanism (filesystem memory, small-model routing, and git-backed stores all exist — §4). We claim **two specific measured contributions** nobody has produced (§5), plus an evaluation on **real multi-year personal data** no one else has.

---

## 1. The problem

LLMs have **amnesia**: every session starts from zero. The industry fix — memory — almost universally works one way:

> extract facts → store as text/vectors → retrieve semantically similar chunks (RAG).

The retrieval substrate is commoditized (§9-E), and it has documented structural failures on **personal context** specifically:

1. **Aggregation failure** — flat retrieval can't combine facts spread across many sessions ("what's the latest on Y?", "how many times did I mention X?"). *Documented by the Mem0 paper.*
2. **Temporal reasoning & updates** — "we switched from Razorpay" — RAG happily returns the stale chunk. *Zep built a temporal knowledge graph precisely because of this.* → **Our answer: version control.** Files hold current state; `git log`/`git diff` hold how it got there.
3. **Lossy compression** — memory systems that summarize lose detail with no way back. → **Our answer: provenance links.** Every episodic note points at the raw transcript it came from.
4. **No abstention** — RAG always returns *something*; it can't say "you never told me this." → **Our answer: verified absence.** An agent that traversed the tree and found nothing has *evidence* of absence, not just a low cosine score.

**Our bet:** the fix isn't a better retriever — it's a better **organization + navigation** layer. Structure memory like a versioned filesystem a human could read, and let small reasoning models *route and navigate* it instead of cosine-matching it.

---

## 2. Architecture

```
 flat context (current conversation)
        │
        ▼
 ┌──────────────────────────────────────────────────────────┐
 │ (1) FAST ROUTER — tiny model, ~1000–1200 tok/s            │
 │     "which subtree(s) of the wiki are relevant?"          │
 │     assisted by: ANN (dense) + BM25 indexes over nodes    │
 └──────────────────────────┬───────────────────────────────┘
                            ▼
 ┌──────────────────────────────────────────────────────────┐
 │ (2) ORCHESTRATOR — 4B model (Qwen3-4B / Gemma-3-4B)       │
 │     agentic loop over the selected subtree(s):            │
 │       ls → grep → cat → git log → git diff → (repeat)     │
 │     assist signals it MAY consult: ANN, BM25, thermometer │
 │     provenance drill-down: episodic note → raw transcript │
 └──────────────────────────┬───────────────────────────────┘
                            ▼
 (3) returns a compact memory package
     — or verified abstention: "no prior context found
        (searched X, grepped Y)"
        │
        ▼  served over MCP (recall / remember tools)
      any host model

 ┌──────────────── THE STORE (one git repo, one Obsidian vault) ──────────────┐
 │  wiki/                      ← LLM Wiki: episodic + semantic memory nodes   │
 │    business/Armor/checkouts/razorpay.md   ←— provenance link ——┐           │
 │    personal/  research/                                        │           │
 │  chats/                     ← RAW LAYER: full transcripts,     │           │
 │    2026/07/session-0714.md     one entity per chat message ————┘           │
 │                                (Obsidian graph + backlinks)                │
 │  every update = a git commit  →  history IS the temporal index             │
 └────────────────────────────────────────────────────────────────────────────┘
```

### Layers & components

| # | Layer | What it is | Notes |
|---|-------|-----------|-------|
| 1 | **Raw layer (Obsidian)** | Full chat transcripts stored as markdown, one entity per message; Obsidian graph/backlinks over them. | Obsidian is **demoted from retrieval DB to substrate + human viewport**. It stores everything, renders the graph, and lets the user read/edit their own memory. |
| 2 | **Wiki layer** | The LLM Wiki: self-authored **episodic memory nodes** (first-person, situation-anchored: "next time I integrate Razorpay, watch out for X because last time Y") organized in a topic **directory tree**. | Directories = the spatial index. The same folder is a valid Obsidian vault. |
| 3 | **Provenance links** | Every episodic node references the raw chat message(s) it was distilled from. | **Reversible compression:** if the summary is too lossy, the agent follows the link and reads the raw transcript. Progressive disclosure for memory. |
| 4 | **Git engine** | The whole store is one git repo; **every memory write is a commit**. | **History = the temporal index.** Temporal/update queries are answered by `git log`/`git diff`/`git blame`, not by a knowledge graph. Branches are used only for isolation (per-user / per-source), never as a topic index. |
| 5 | **Fast router** | A tiny, very fast model (target ~1000–1200 tok/s) that maps the flat context to candidate **subtrees/nodes**. | Replaces v0.2's plain embedding "RAG-assist" as the coarse stage. ANN + BM25 indexes over node summaries feed it candidates. Job = routing, not reasoning. |
| 6 | **Agentic retriever** | The 4B orchestrator navigates the routed subtree with `ls`/`grep`/`cat` + `git log`/`git diff` until done — **this is the core retriever.** | Hybrid signals (ANN, BM25, usefulness thermometer §9-F) are **assists the agent may consult**, each independently ablatable — never the retriever itself. |
| 7 | **Abstention** | The agent abstains via **verified absence**: subtrees traversed, terms grepped, nothing found — with confidence derived from navigation-trace features (coverage, subtrees visited, greps issued). | Structurally impossible for flat RAG (a similarity threshold is not proof of absence). Claim 2 in §5. |
| 8 | **Write path** | At session end, the model distills what it will need next time into episodic nodes (with provenance links) and **commits**. Periodic "knowledge linting" reorganizes the tree. | Self-curated; no hand-labeling. Phase-3 idea: reward the writer on downstream retrieval success (§6). |
| 9 | **MCP interface** | PCP runs as a **local/self-hosted MCP server** (stdio) exposing `recall(context)` and `remember(note)`. | Any MCP host plugs in. The agentic loop is invisible behind one tool call — the host never sees `ls`/`grep`. §8 covers product/deployment. |
| 10 | **Optical substrate (deferred)** | Rendering the returned memory package as an image (DeepSeek-OCR-style optical compression) on the **return path only**. | Prior art exists (AgentOCR, OCR-Memory, ScrapMem — §9-I); store and navigation stay text. A later ablation: same accuracy at fewer host tokens? Not a pillar. |

---

## 3. Three concrete walkthroughs

**A — Spatial retrieval.** *"I'm setting up checkout for the AU store, what should I watch for?"*
Router → `business/Armor/checkouts/`. Orchestrator `ls`es it, `cat`s `razorpay.md` + `gokwik.md`, notices an AUD reference, `grep`s the tree for `AUD` → finds `au-launch.md`. Returns: Razorpay AUD settlement gotcha, GoKwik theme conflict, AU rounding issue.

**B — Temporal retrieval.** *"What were we using before GoKwik, and why did we switch?"*
`gokwik.md` only says "active since March." The agent runs `git log --follow business/Armor/checkouts/` → finds the commit where `razorpay.md` was marked deprecated the week `gokwik.md` appeared; `git diff` on it shows "switched due to AUD settlement delays." **History answered the question — no temporal KG exists in the system.**

**C — Provenance drill-down.** *"What exactly did the Razorpay support agent tell me about settlement timing?"*
The episodic note says only "settlement delays on AUD." Too compressed. The agent follows the note's provenance link into `chats/2026/03/…`, reads the raw transcript, and returns the exact quoted commitment. **Compression was reversible.**

And when the store genuinely has nothing: **verified abstention** — *"No prior checkout context found (searched `checkouts/`, `au-launch`; grep: razorpay|gokwik|AUD)."*

---

## 4. Honest scope — what we are NOT claiming

**Read this so no one (including future-us) overclaims and gets embarrassed in review.**

- ❌ Not inventing filesystem/markdown memory — Karpathy's *LLM Wiki*, *ByteRover* (§9-A).
- ❌ Not inventing small-model memory routing — *MemFlow*, *HORMA* (§9-B).
- ❌ Not inventing git-backed memory — **DiffMem** already ships a git store whose retrieval agent uses `git log`/`diff`/`blame`; *Git-Context-Controller* and *GitOfThoughts* version agent context/reasoning (§9-A2). **None of them report benchmark numbers** — the measurement is open, and that is ours (§5).
- ❌ Not inventing optical memory — DeepSeek-OCR, AgentOCR, OCR-Memory, ScrapMem (§9-I). Hence deferred.
- ❌ Not claiming a novel storage mechanism, and we do **not** use the word "novel" loosely to reviewers.

✅ We **are** building the clean system that combines these validated parts — and producing **measurements that don't exist** (§5), on a **testbed nobody has** (a real, messy, multi-year, cross-tool personal+business archive), against **honest baselines** (§5).

**One-line pitch:**
> *A git-versioned, provenance-linked personal memory engine — fast router + small agentic navigator over a human-readable wiki — contributing the first controlled measurement of version-history navigation against temporal-KG and RAG baselines on the temporal/update/abstention splits, evaluated additionally on real personal-context data, and served over MCP.*

---

## 5. The two measured claims + eval plan

### Claim 1 — Version-history navigation as the temporal layer 🏆
- **Exists:** DiffMem (git + `git log`/`diff` retrieval agent, production, ~900★) proves buildability. Zep proves temporal *structure* beats embeddings (+18.5% LongMemEval) — via a temporal KG.
- **Does NOT exist:** any benchmark number for the git approach. Nobody has answered: *does version-history navigation match a temporal-KG on the temporal & update splits — at what token/latency cost?*
- **Falsifiable claim:** *"A versioned filesystem plus an agent that reads history matches temporal-KG performance on temporal/update splits, with a small orchestrator, at a fraction of the infrastructure."* If false, that's still a publishable finding (KGs earn their complexity).

### Claim 2 — Navigation-grounded abstention
- **Exists:** LongMemEval scores abstention; *Learning When to Remember* (arXiv 2604.27283) does abstention-aware retrieval via a bandit deciding whether to inject memory (must-cite).
- **Does NOT exist:** abstention as **calibrated proof-of-absence from navigation traces** (coverage of candidates, subtrees visited, greps run) rather than a similarity threshold.
- Directly scored by LongMemEval's abstention split; Baseline 1 structurally cannot compete on it.

### Eval plan

| Item | Choice | Why |
|------|--------|-----|
| **Primary benchmark** | **LongMemEval / -V2** | Headroom + the hard splits: updates, temporal, aggregation, abstention. |
| **Secondary** | **LoCoMo** | Lingua franca; near-saturated — legibility, not the win. |
| **Distinguishing testbed** | **Real personal archive** (ours) | The ownable data. Requires a labeling protocol (§7 risks) to be a finding, not a demo. |
| **Baseline 1** | Vector RAG (Mem0-style) | The thing to beat; its aggregation gap is documented. |
| **Baseline 2** | Plain filesystem memory (ByteRover-style; no router, no git tools) | Isolates our additions. |
| **Baseline 3** | Git-memory (DiffMem-style; big-model agent, no router/cascade) | Isolates the router + small-orchestrator design. |
| **Comparison point** | Zep's published LongMemEval numbers | Claim 1 is judged against these. |
| **Metrics** | Per-split QA accuracy (single-hop / multi-hop / **temporal** / **update** / **abstention**), tokens/query, latency | The win lives in temporal/update/abstention. |

**Key ablations:** ± router (vs plain embedding assist) · ± each assist signal (ANN / BM25 / thermometer) · ± git tools (**= the Claim-1 measurement**) · trace-based vs naive abstention · ± provenance drill-down · orchestrator size (4B vs 7–8B) · (later) ± optical return path.

### 🚩 Methodology guardrails
- Never train the orchestrator on the reported benchmark and compare against training-free baselines. If fine-tuning: separate/synthetic training source tested zero-shot, or cross-benchmark transfer (train LoCoMo → test LongMemEval).
- **Benchmark→git mapping must be mechanical:** ingest sessions chronologically, one commit per session/update — never hand-crafted per question, or the temporal result is fake.
- Small benchmarks are noisy → bootstrap confidence intervals.
- Latency is a promise: measure and report it (router + loop end-to-end), or don't call anything "real-time."

---

## 6. Training plan

**Sequencing is deliberate — do NOT front-load fine-tuning.**

- **Phase 1 (Week 1): everything prompted, zero training.** Prompted 4B navigation already works per ByteRover / *Is Grep All You Need*. Router starts as the ANN+BM25 candidate list + a prompted tiny model. If prompted PCP already clears RAG, the core is done and de-risked.
- **Phase 2 (if Phase 1 plateaus): trace distillation.** Let a strong model run the route→navigate loop on the training split, log `(context + wiki-state → action)` traces, keep only traces that reached the correct answer, SFT the 4B on them. Router can likewise be distilled into a fast classifier over subtrees.
- **Phase 3 (stretch, only if ahead): retrieval-optimal writing.** Reward the write path on whether the navigator can later *find and use* what it wrote (synthetic future queries → navigation success as reward; the §9-F usefulness thermometer as persistence gate). Memory-R1/Mem-α do RL over flat stores; co-adapting writer+navigator over a hierarchy is open — but it is a project of its own. Parked.
- **Models:** orchestrator Qwen3-4B / Gemma-3-4B; router in the ≤1B class (the ~1000–1200 tok/s target implies sub-1B or aggressive serving — treat the number as a target to validate, not a spec).

---

## 7. Timeline (≈1 month) & risks

- **Week 1 — Baselines & pipeline:** store schema (wiki + chats + provenance), prompted agentic loop; run Baselines 1–2 on LongMemEval → **numbers by day 7**.
- **Week 2 — PCP v1:** commit-on-write + git tools; router + ANN/BM25 assists; trace-based abstention; per-split eval; ablations. **Claims 1–2 measured here.**
- **Week 3 — Real-data testbed (+ optional Phase-2 SFT):** labeling protocol + run on the personal archive.
- **Week 4 — Write-up + scaling curve:** results, ablations, limitations; grow the tree synthetically (1×/10×/100× nodes) and plot navigation success/tokens/latency vs tree size against RAG's flat curve.

**Risks:**
- **Crowded field** — protection is the honest measure-don't-invent framing.
- **DiffMem proximity** — cite prominently, run as Baseline 3; our delta = router + small orchestrator + abstention + provenance + *the measurements it never produced*.
- **GitOfThoughts null result** (memory helps only when new problems resemble stored ones) — an argument *for* personal context, which is exactly the high-resemblance regime. Say so before a reviewer does.
- **Router speed target** — 1000–1200 tok/s is hardware/serving-dependent; validate early, don't promise it in writing until measured.
- **4B too weak for multi-hop** — check prompted first; fall back to 7–8B.
- **Real-data rigor** — the archive has no gold labels; the labeling protocol (self-authored QA incl. temporal/update/abstention cases, contamination-controlled) is what turns a demo into a finding. If it generalizes ("turn any personal archive into a memory benchmark"), it's a contribution in its own right.
- **Write-path drift/bloat** — knowledge linting; note reorganization = renames, which `git log --follow` survives but grep-over-history doesn't. Test.
- **Provenance link rot** — raw transcripts must be append-only; linting must never rewrite `chats/`.

---

## 8. System & deployment (the product angle)

PCP ships as a **local or self-hosted MCP server** — stdio transport, installable via `uvx pcp-server`, configured into Claude Desktop/Code, Cursor, or any MCP host in one line.

- **Tool surface (deliberately tiny):** `recall(context)` → memory package or verified abstention; `remember(note)` → commit. The navigation loop is internal — exposing `ls`/`grep` to the host would burn host tokens and bypass the orchestrator.
- **Overhead accounting:** MCP protocol ≈ milliseconds; host context cost ≈ tool schemas (~200 tokens) + the returned package (content you wanted injected anyway). The real latency is the router+loop itself — which is a reported metric (§5). Deployment prerequisite: a locally served ≤1B router + 4B orchestrator (ollama / llama.cpp) and the embedding index.
- **Privacy is the point:** memory, models, and indexes never leave the user's machine. Portable (it's a git repo), auditable (`git log`), editable (it's an Obsidian vault).
- **Roadmap:** local first → self-hosted (streamable HTTP + auth) → hosted product later. Research doc concerns end at "local."

---

## 9. Prior work (annotated, grouped by role)

> IDs from literature search — **double-check before formal citation.**

### A. Filesystem/markdown agentic memory (what we build ON)
- **Karpathy — "LLM Wiki"** (gist, Apr 2026). Markdown-first, interlinked, model-maintained ("knowledge linting"); explicitly not RAG. → *Intellectual anchor.*
- **ByteRover** (arXiv 2604.01599). SOTA LoCoMo, hierarchical markdown, zero infra. → *Closest store-side prior; Baseline 2.*
- **Is Grep All You Need?** (arXiv 2605.15184). Filesystem agent beats vectors on LongMemEval samples. → *Justifies navigate-don't-embed.*
- **HORMA** (arXiv 2606.11680). "Optimal memory is a navigable directory." → *Supports the tree.*
- **LlamaIndex — "Did Filesystem Tools Kill Vector Search?"** (blog, 2026). → *Industry evidence.*

### A2. Version-controlled memory (the temporal layer)
- **DiffMem** (github.com/Growth-Kinetics/DiffMem, ~900★, production). Git markdown store; retrieval agent shells out to `grep`/`git log`/`diff`/`blame`; writer + consolidator. **No benchmarks, no small orchestrator, no MCP, no abstention.** → *Closest overall prior; Baseline 3. Mechanism exists; measurement doesn't.*
- **Git Context Controller** (arXiv 2508.00031). COMMIT/BRANCH/MERGE over agent context. → *Adjacent; cite to delimit.*
- **GitOfThoughts** (arXiv 2606.14470). Versions reasoning traces; null result on memory transfer; git's value = auditability. → *Must-cite; see §7 risks.*

### B. Orchestration & small-model routing
- **MemFlow** (arXiv 2605.03312). Router-vs-executor split; SLM routes. → *Blueprint for our router/orchestrator split.*
- **Hierarchical Memory Orchestration for Personalized Persistent Agents** (arXiv 2604.01670).
- **SWE-Grep / SWE-Grep-Mini** (HN 45607822). RL-trained small fast grep-retrieval model. → *Precedent for the fast-navigator job.*
- **MEMTIER** (arXiv 2605.03675) — hot/cold tiering. **AgentIR** (arXiv 2605.25092) — cascade retrieval = our router→agent pattern.
- **Learning When to Remember** (arXiv 2604.27283). Bandit abstention-aware injection; null-retrieval abstention is well-calibrated. → *Must-cite for Claim 2; our delta = verified absence from navigation traces, not an injection-routing decision.*

### C. Structured memory systems (comparisons)
- **Mem0** (ECAI 2025) — documents RAG's aggregation failure; Baseline 1 source. · **Zep** — temporal KG, +18.5% LongMemEval; Claim-1 comparison point. · **Letta/MemGPT** — OS-style ancestor. · **PersonaAgent** (2506.06254), **PersonaTree** (2606.04780). · **Memory-R1 / Mem-α** — RL memory ops over flat stores (Phase-3 relevant). · **ShardMemo** (2601.21545), **CALMem** (2605.20724).
- **Verbatim Chunks Beat Extracted Artifacts** (arXiv 2601.00821). Raw beats summarized in controlled ablation. → *Direct support for provenance drill-down.*

### D. Benchmarks
- **LongMemEval / -V2** (2605.12493) — primary. · **LoCoMo** — secondary. · **PersonaMem-v2** (2512.06688), **PERMA** (2603.23231), **MCP-Persona** (2606.02470 — check their protocol for our testbed), **Towards Root Memories** (2606.23283), **BEAM**.

### E. Roads considered and rejected (retrieval substrate is saturated)
- **Jina-embeddings-v4** — embedding substrate is solved; don't compete. · Activation steering (**SteerX** 2510.22256, contrastive steering 2503.05213, steerable chatbots 2505.04260, persona vectors) · user-embedding/prefix personalization (**Embedding-to-Prefix** 2505.17051, **POPI** 2510.17881, **TSUBASA** 2604.07894).

### F. The usefulness signal (our prior work — optional governor)
- **Usefulness thermometer:** `u(m | ctx, a) = logP(a | m+ctx) − logP(a | ctx)`; basis in REPLUG/Atlas. Prior experiments showed ≈ similarity for retrieval → NOT the core mechanism; used as (a) one ablatable assist signal and (b) the natural Phase-3 write gate. See internal `project-ttl-memory-probe`.

### G. Foundations
- **Lost in the Middle** (Liu et al.) — motivation for external memory. · **MCP** (Anthropic) — serving layer.

### H. Surveys
- Memory in the Age of AI Agents (2512.13564) · Externalization in LLM Agents (2604.08224) · Memory in LLMs (2509.18868) · Mem0 "State of AI Agent Memory 2026" (blog — current leaderboards).

### I. Optical substrate (deferred; prior art that defers it)
- **DeepSeek-OCR** (2510.18234) — ~10× optical compression @97%; proposed memory-forgetting via progressive downscaling. · **AgentOCR** (2601.04786, ACL 2026) — agent history as rendered image, >95% perf at >50% fewer tokens. · **OCR-Memory** (2604.26622) — optical context retrieval, locate-and-transcribe. · **ScrapMem** (2605.03804) — on-device *personalized* memory via optical forgetting. → *Mechanism taken several times over; PCP keeps store+navigation textual and, at most, ablates an optical **return path** later.*

---

## 10. Glossary
- **Node** — one markdown file in the wiki = one topic/situation memory.
- **Raw layer** — full chat transcripts in `chats/`; append-only; Obsidian graph entities.
- **Provenance link** — reference from an episodic node to the raw message(s) it was distilled from; enables drill-down.
- **Router** — tiny fast model choosing candidate subtrees (coarse stage).
- **Orchestrator** — the 4B model running the agentic loop (fine stage, core retriever).
- **Agentic loop** — iterative `ls`/`grep`/`cat`/`git log`/`git diff` until answer or verified abstention.
- **Assist signals** — ANN, BM25, usefulness thermometer; consultable by the agent, each ablatable.
- **Temporal layer** — git history: current state in files, change history in commits.
- **Verified abstention** — abstaining on evidence of absence (trace features), not a similarity threshold.
- **Trace distillation** — SFT the small models on a strong model's successful navigation traces.
- **Retrieval-optimal writing** — (Phase 3) rewarding the writer on downstream navigation success.

---
*v0.3 — finalized initial doc. Update as results land.*
