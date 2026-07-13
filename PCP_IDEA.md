# PCP — Personal Context Protocol
### A Deep, Real-Time, Orchestrated, Agentic-RAG-Assisted Context Protocol

> **Status:** idea doc (v0.2) · **Owner:** Iftekhar · **Date:** 2026-07-13 (v0.1: 2026-07-08)
> **Audience:** team members + AI collaborators picking this up cold.
> **v0.2 changes:** added the git-temporal layer (§2, §4.5-1), navigation-grounded abstention (§4.5-2), retrieval-optimal writing as Phase 3 (§6), DiffMem as Baseline 3 (§5), new prior-art (§9-A2), Obsidian note (§2).

---

## 0. TL;DR (read this first)

PCP is a **personal memory layer for LLMs** that stores everything you've ever told/shown an AI as a **human-readable hierarchy of markdown files** (a "wiki"), and retrieves from it not with a vector database, but with a **small orchestrator model (a 4B) that navigates the tree agentically** — `ls` to see what exists, `grep`/`cat` to drill in — the same way Claude Code searches a codebase.

The store is **git-versioned**: every memory update is a commit, so the orchestrator also gets `git log` / `git diff` / `git blame` as tools — **version history IS the temporal reasoning layer** (no temporal knowledge graph needed).

- **In:** the flat context window (the current conversation / situation).
- **Out:** the specific past memories that will actually help, pulled by an agentic loop over the file tree — **or a verified "you never told me this"** when nothing fits.
- **Assisted by:** lightweight vector RAG for *coarse candidate-node* suggestion, then the agent refines.
- **Served as:** an MCP tool, so any model (Claude, a local model, whatever) can plug into the same portable memory.

**What we are honestly claiming:** not a new storage mechanism — filesystem memory, small orchestrators, and even git-backed memory all exist (see §4). We are **combining today's validated best-practice memory components into one system and producing measurements nobody has**: the first controlled comparison of version-history navigation vs. temporal-KG vs. vector RAG on the hard splits, a navigation-grounded abstention mechanism, and an evaluation on real personal data no one else has. (See [§4 Honest Scope](#4-honest-scope--what-we-are-and-are-not-claiming) and [§4.5](#45-the-two-mechanism-level-bets-v02).)

---

## 1. The problem

LLMs have **amnesia**: every session starts from zero. The industry "fix" — memory — almost universally works one way:

> extract facts → store as text/vectors → retrieve semantically-similar chunks back into the context window (RAG).

This is a solved, commoditized substrate (see [§9-E](#e-why-not-just-a-better-embedder-personalization-mechanisms-we-are-not-using)) and it has documented, structural failure modes on **personal context** specifically:

1. **Aggregation failure** — flat retrieval can't combine facts spread across many chunks/sessions ("how many times did I mention X", "what's the latest on Y"). *Established by the Mem0 paper.*
2. **Temporal reasoning & updates** — "I moved cities / we switched from Razorpay" — RAG happily returns the stale chunk. *Zep's temporal graph exists precisely because of this.* → **Our answer: version control. The file holds the current state; `git log`/`git diff` holds how it got there.**
3. **Lost-in-the-middle** — even when the right chunk is retrieved, long stuffed context buries it.
4. **No abstention** — RAG always returns *something*; it can't say "you never told me this." → **Our answer: an agent can *verify* absence by traversing the tree, not just fail to match.**

**Our bet:** the fix isn't a better retriever — it's a better **organization + navigation** layer. Structure the memory like a filesystem a human could read, version it like a repo, and let a reasoning model *navigate* it instead of cosine-matching it.

---

## 2. What PCP is (architecture)

```
                 ┌─────────────────────────────────────────────┐
   flat context  │                   PCP                        │
  (conversation) │                                              │
      ───────────►  (1) RAG-assist: embed context → top-k       │
                 │       candidate NODES (coarse)                │
                 │                    │                          │
                 │                    ▼                          │
                 │  (2) ORCHESTRATOR (4B Qwen/Gemma)             │
                 │       reasons: "which nodes help here?"       │
                 │                    │                          │
                 │                    ▼                          │
                 │  (3) AGENTIC LOOP over the markdown store:    │
                 │       ls → grep → cat → git log/diff/blame    │
                 │                    │        (repeat)          │
                 │                    ▼                          │
                 │  (4) returns the precise past memories        │
      ◄──────────   that matter (+ verified abstention if       │
                 │    nothing fits)                              │
                 └─────────────────────────────────────────────┘
                              │
                              ▼
                  MARKDOWN MEMORY STORE (the "wiki")
                  = a git repo (every update is a commit)
                  = an Obsidian-compatible vault (human viewport)
                  business/
                    Armor/
                      checkouts/
                        razorpay.md   ← episodic memory node
                        gokwik.md
                      ads/
                  personal/
                  research/
```

### Components

| # | Component | What it is | Notes |
|---|-----------|-----------|-------|
| 1 | **Memory store** | A directory tree of markdown files, one node per topic/situation. Human-readable, git-versioned, editable. | Nodes are **self-authored episodic memories** — first-person, situation-anchored. The folder doubles as an **Obsidian vault** — Obsidian is the human viewport (backlinks, graph view), git is the time axis, agent tools are the machine viewport. Same files, three windows; nothing conflicts (cf. `obsidian-git`). |
| 2 | **RAG-assist** | Small embedding index over node summaries, used only for **coarse candidate suggestion** to the orchestrator. | Safety net, not the retriever. Ablate to measure its contribution. |
| 3 | **Orchestrator** | A **4B model (Qwen3-4B / Gemma-3-4B)** that takes flat context + candidate nodes and decides *what to open and search*. | Job = reasoning + navigation, not world knowledge → small model is enough. |
| 4 | **Agentic loop** | The orchestrator calls filesystem tools (`ls`, `grep`, `cat`) **plus history tools (`git log`, `git diff`, `git blame`)** to walk the tree — and its past — until it has what it needs, then returns it (or abstains). | This is the "grep-not-vectors" core; git tools make it "navigate time, not just space." |
| 5 | **Temporal layer** | **Git itself.** Files always hold *current* state; updates never delete — they commit. Temporal/update queries ("what did we use before?", "when did this change?") are answered by navigating version history. | No KG schema, no extraction pipeline, human-auditable via `git log`. Prior art exists (DiffMem, §9-A2) — our contribution is **measuring it** (§4.5-1). |
| 6 | **Abstention** | The agent abstains via **verified absence**: it traversed the relevant subtree, grep'd the obvious terms, and found nothing — evidential "you never told me this", with confidence derived from navigation-trace features (coverage of candidates, subtrees visited, greps issued). | Structurally impossible for flat RAG (similarity threshold ≠ proof of absence). See §4.5-2. |
| 7 | **Write path** | At the end of a session, the model **writes what it thinks it'll need next time** into the tree (self-curated) as a **commit**, and periodically "lints"/reorganizes. | No hand-labeling. Model decides what to persist. Phase-3 idea: reward the writer on downstream retrieval success (§6). |
| 8 | **MCP interface** | PCP exposed as an MCP server so any host model can use the same portable memory. | Portability is the systems angle labs skip (walled gardens). |

---

## 3. How it works (two concrete walkthroughs)

**Walkthrough A — retrieval.** User starts a new chat: *"I'm setting up checkout for the AU store, what should I watch for?"*

1. **RAG-assist** embeds that line → suggests candidate nodes: `business/Armor/checkouts/razorpay.md`, `.../gokwik.md`, `business/Armor/au-launch.md`.
2. **Orchestrator (4B)** reasons: "checkout + AU → payment gateway history is relevant; also currency/GoKwik notes." Decides to `ls business/Armor/checkouts/` and `cat` the razorpay + gokwik nodes.
3. **Agentic loop** reads them, notices razorpay note references an AUD/INR issue, `grep`s the tree for `AUD` → finds `au-launch.md`, `cat`s it.
4. **Returns** a compact set: "Last time — Razorpay AUD settlement gotcha (X), GoKwik theme conflict (Y), AU currency rounding (Z)."

**Walkthrough B — temporal.** User asks: *"What were we using before GoKwik, and why did we switch?"*

1. RAG-assist points at `checkouts/`. The orchestrator `cat`s `gokwik.md` — current state only says "active since March."
2. It runs `git log --follow business/Armor/checkouts/` → sees the commit where `razorpay.md` was updated to "deprecated" the same week `gokwik.md` was created; `git diff` on that commit shows the note: "switched due to AUD settlement delays."
3. **Returns:** "Razorpay, until March — switched because of AUD settlement delays." No temporal KG was consulted, because none exists — **history answered the question.**

And if the tree (and its history) genuinely has nothing: **verified abstention** — "No prior checkout context found (searched `checkouts/`, `au-launch`, grep: razorpay|gokwik|AUD)."

---

## 4. Honest scope — what we ARE and ARE NOT claiming

**This matters. Read it so no one (including future-us) overclaims and gets embarrassed in review.**

- ❌ We are **not** inventing filesystem/markdown memory — Karpathy's *LLM Wiki* and *ByteRover* already did, and it's already SOTA. ([§9-A](#a-the-core-paradigm--filesystemmarkdownagentic-memory-what-we-build-on))
- ❌ We are **not** inventing small-model memory orchestration — *MemFlow* / *HORMA* already did. ([§9-B](#b-memory-orchestration--small-model-routing-the-orchestrator-design))
- ❌ We are **not** inventing git-backed memory — **DiffMem** already ships a git-based markdown store whose retrieval agent uses `git log`/`diff`/`blame`; *Git-Context-Controller* and *GitOfThoughts* version agent context/reasoning. ([§9-A2](#a2-version-controlled-memory-the-temporal-layer)) **But none of them report benchmark numbers** — the measurement is open, and that's ours (§4.5-1).
- ❌ We are **not** claiming a novel storage mechanism, and we should **not use the word "frontier/novel" loosely to reviewers.**

- ✅ We **are** building a clean, working system that **combines** these validated components, and **measuring where it lands.**
- ✅ Our ownable levers (need ≥1, ideally all):
  1. **Reference frame** — we run our own baselines (vector RAG + plain filesystem memory + git-memory à la DiffMem) so "PCP scored X" means something.
  2. **A testbed nobody has** — a **real, messy, multi-year, cross-tool personal+business archive** (Iftekhar's own chat/Armor history). Everyone else reports on *synthetic* LoCoMo/LongMemEval.
  3. **One honest takeaway** — an ablation ("the orchestrator matters more than the RAG-assist", or "holds at 90% of SOTA at 1/10 the tokens").
  4. **The two measured bets in §4.5** — the closest thing we have to mechanism-level contributions.

**One-line pitch for the topic sheet / teachers:**
> *A system combining current best-practice agentic memory components (git-versioned markdown store + small-model orchestrator + RAG-assist), contributing the first controlled measurement of version-history navigation against temporal-KG and RAG baselines on the temporal/update/abstention splits, evaluated additionally on real personal-context data.*

---

## 4.5 The two mechanism-level bets (v0.2)

### 1. Version-history navigation as the temporal layer — *the measured claim* 🏆

- **What exists:** DiffMem (git store + `git log`/`diff`/`blame` retrieval agent, in production, ~900 stars) proves the mechanism is buildable. Zep proves temporal *structure* beats embeddings (+18.5% on LongMemEval) — via a temporal knowledge graph.
- **What does NOT exist:** any benchmark number for the git approach. DiffMem reports **zero** results on LoCoMo/LongMemEval. Nobody has answered: *does version-history navigation match or beat a temporal-KG on the temporal & update splits — and at what token/latency cost?*
- **Our claim (falsifiable):** *"Temporal knowledge graphs are unnecessary for personal memory: a versioned filesystem plus an agent that reads history matches temporal-KG performance on temporal/update splits, with a 4B orchestrator, at a fraction of the infrastructure."* If it's false, that's still a publishable finding (git navigation has a measurable gap → KGs earn their complexity).
- **Cost:** three extra tools in the loop + commit-on-write. Days, not weeks (Week 2).

### 2. Navigation-grounded abstention — *the narrow-open mechanism*

- **What exists:** LongMemEval scores abstention as a split. *Learning When to Remember* (arXiv 2604.27283) does abstention-aware retrieval via a contextual bandit deciding whether to inject memory, and notes null-retrieval abstention is well-calibrated. **Must-cite.**
- **What does NOT exist:** abstention as **verified absence from navigation** — "I traversed the relevant subtrees, grep'd the obvious terms, and confirmed nothing exists" — with a confidence score derived from **trace features** (candidate coverage, subtrees visited, greps issued) rather than a similarity threshold.
- **Why it matters:** proof-of-absence is *evidential*; a cosine threshold is *statistical*. Flat RAG structurally cannot do the former. LongMemEval's abstention split scores it directly, and Baseline 1 cannot compete on it.
- **Cost:** mostly prompt design + logging we'd already do for ablations.

**Parked (Phase 3, only if ahead of schedule): retrieval-optimal writing** — reward the write-path on whether the orchestrator can later *find and use* the memory (synthetic future queries → navigation success as reward; the §9-F usefulness thermometer as the gate). Memory-R1/Mem-α do RL on memory ops over *flat* stores; co-adapting writer+navigator over a *hierarchy* is open. It is a research project of its own — do not start it before Weeks 1–2 land.

---

## 5. Evaluation plan

| Item | Choice | Why |
|------|--------|-----|
| **Primary benchmark** | **LongMemEval** (and LongMemEval-V2) | Headroom + tests the hard splits: updates, temporal, aggregation, abstention. |
| **Secondary benchmark** | **LoCoMo** | Lingua franca — everyone reports it (makes us comparable). Near-saturated (>90%), so it's for legibility, not the win. |
| **Distinguishing testbed** | **Real personal archive** (ours) | The ownable contribution. |
| **Baseline 1** | Vector RAG (Mem0-style) | The thing we must beat; the RAG-aggregation gap is documented. |
| **Baseline 2** | Plain filesystem memory (ByteRover-style, no orchestrator FT, **no git tools**) | Isolates *our* additions. |
| **Baseline 3** | **Git-memory (DiffMem-style: same store, big-model retrieval agent, no orchestrator/RAG-assist)** | Isolates the 4B-orchestrator + cascade against the closest prior system. |
| **Comparison point** | **Zep's published LongMemEval numbers** (temporal-KG) | The §4.5-1 claim is judged against these, esp. temporal/update splits. |
| **Metrics** | QA accuracy per split (single-hop / multi-hop / **temporal** / **update** / **abstention**), tokens/query, latency | Report per-split — the win lives in temporal/update/abstention. |

### Key ablations
1. ± RAG-assist (does coarse candidate suggestion earn its keep?)
2. ± git tools (Baseline 2 vs full PCP → isolates the temporal layer — **this is the §4.5-1 measurement**)
3. ± navigation-trace abstention vs naive "found nothing → abstain"
4. Orchestrator size (4B vs 7–8B vs big-model)

### 🚩 Methodology guardrails (do NOT skip)
- **Never train the orchestrator on the benchmark you report on** and then compare to training-free baselines — that's a fake win (in-distribution memorization on a ~500-question set).
- If we fine-tune, **train on a separate/synthetic source and test zero-shot**, OR do **cross-benchmark transfer** (train LoCoMo → test LongMemEval) which is a *stronger* claim.
- Small benchmarks = noisy scores → report bootstrap confidence intervals.
- "Real-Time" in the title is a **latency promise** — either measure & report latency, or drop the word.
- **Benchmark→git mapping must be honest:** LongMemEval gives session transcripts, not a commit history. The commit sequence must be derived mechanically from session order (ingest sessions chronologically, one commit per session/update) — never hand-crafted per question, or the temporal result is fake.

---

## 6. Training plan (the orchestrator)

**Sequencing is deliberate — do NOT front-load fine-tuning.**

- **Phase 1 (Week 1): prompted 4B orchestrator, zero training.** Off-the-shelf agentic navigation already works (per ByteRover / "Is Grep All You Need"). A well-prompted 4B may already clear RAG → core done, everything de-risked.
- **Phase 2 (only if Phase 1 plateaus): distillation SFT.** The benchmark gives Q+A+haystack but **no gold navigation traces**, so:
  > Let a strong model (Claude / GPT / big Qwen) run the ls→grep→cat→git-log loop on the training split, log `(context + wiki-state → action)` traces, keep the ones that reached the correct answer, and **SFT the 4B on those traces** (trace distillation).
- **Phase 3 (stretch, only if ahead): retrieval-optimal writing.** Reward the write-path model on downstream navigation success over synthetic future queries; use the usefulness thermometer (§9-F) as the persistence gate. See §4.5 "parked."
- Target model: **Qwen3-4B-Base/Instruct** or **Gemma-3-4B** — reasoning + density over size, as intended.

---

## 7. Build phases / timeline (≈1 month)

- **Week 1 — Baseline & pipeline:** build the markdown store schema + the prompted agentic loop; run RAG and filesystem baselines on LongMemEval → **have numbers by day 7.**
- **Week 2 — PCP v1 + git-temporal + RAG-assist:** commit-on-write + `git log`/`diff`/`blame` tools; candidate-node suggestion; navigation-trace abstention; per-split eval; ablations 1–3. **The §4.5-1 measurement lands here.**
- **Week 3 — Real-data testbed + (optional) distillation SFT:** run on the personal archive; if time, Phase-2 fine-tune.
- **Week 4 — Write-up + scaling curve:** results, ablations, honest positioning, limitations; synthetically grow the tree (1×/10×/100× nodes) and plot navigation success/tokens/latency vs tree size against RAG's flat curve (answers §8's open question — cheap, one script, one citable figure).

---

## 8. Risks & open questions

- **Crowded field** — memory/agents is the most-published area in ML right now (see the dates on §9). Protection = the honest "build + measure on real data" framing, not a novelty claim.
- **DiffMem proximity** — the closest system to PCP overall. Protection = cite it prominently, run it as Baseline 3, and be explicit that our contribution is the orchestrator/cascade/abstention **plus the measurements it never produced**. Finding it now, not in review, is the win.
- **The GitOfThoughts null result** — they found agent memory mostly *doesn't* help on novel problems; it helps when the new problem resembles a stored one (similarity >0.8). **This is an argument FOR our setting, not against:** personal context is precisely the high-resemblance regime ("what did I do about Razorpay last time"). Cite it and say so explicitly — a reviewer will otherwise raise it.
- **4B might be too weak** for multi-hop agentic reasoning — check *prompted* before committing to FT; fall back to 7–8B if needed. Git-history navigation adds hops (log → pick commit → diff), so re-check at Week 2.
- **Real-data eval rigor** — personal archive has no gold labels; need a labeling protocol (self-authored QA pairs incl. temporal/update/abstention cases, contamination-controlled) to make it measurable, not just a demo. If the protocol generalizes ("turn any personal archive into a memory benchmark"), it's a contribution in its own right.
- **Write-path quality** — "let the model write what it needs" can drift/bloat; may need periodic reorganization ("knowledge linting"). Note: reorganization = renames/moves, which `git log --follow` handles — but grep-over-history doesn't; test this.
- **Open Q:** does agentic navigation degrade gracefully as the tree grows to thousands of nodes? (→ Week-4 scaling curve.)

---

## 9. Research papers & prior work (annotated reading list)

> Notes: IDs/links gathered from literature search — **double-check each before formal citation.** Grouped by role in PCP.

### A. The core paradigm — filesystem/markdown/agentic memory (what we build ON)
- **Karpathy — "LLM Wiki"** (GitHub gist, Apr 2026). Markdown-first, interlinked memory the LLM maintains ("knowledge linting"); explicitly *not RAG*. → *The intellectual anchor for our store.* `gist.github.com/karpathy/442a6bf555914893e9891c11519de94f`
- **ByteRover: Agent-Native Memory Through LLM-Curated Hierarchical Context** (arXiv 2604.01599). SOTA on LoCoMo, competitive on LongMemEval, zero infra, human-readable markdown, hierarchical. → *Closest prior system on the store side; our Baseline 2 and the thing we extend.*
- **Is Grep All You Need? How Agent Harnesses Reshape Agentic Search** (arXiv 2605.15184). grep vs vector on LongMemEval samples; filesystem agent wins. → *Justifies the "navigate, don't embed" core.*
- **Organize then Retrieve: Hierarchical Memory Navigation for Efficient Agents (HORMA)** (arXiv 2606.11680). "Optimal memory is a navigable directory, not a flat DB." → *Directly supports our tree design.*
- **LlamaIndex — "Did Filesystem Tools Kill Vector Search?"** (blog, 2026 benchmarks). Filesystem agent beat RAG (correctness 8.4 vs 6.4). → *Industry evidence.*
- **"Beyond Flat Retrieval: Why Hierarchical Navigation…"** (Medium, Jun 2026). → *Accessible framing of the thesis.*

### A2. Version-controlled memory (the temporal layer) — *added v0.2*
- **DiffMem: Git-Based Differential Memory for AI Agents** (`github.com/Growth-Kinetics/DiffMem`, ~900★, production). Git-backed markdown store; retrieval agent shells out to `grep`/`git log`/`git diff`/`git blame`; writer + consolidator agents. **No benchmark results, no small orchestrator, no MCP, no abstention.** → *Closest prior system overall. Our Baseline 3. The mechanism exists; the measurement doesn't.*
- **Git Context Controller** (arXiv 2508.00031). COMMIT/BRANCH/MERGE over agent *context* for long-horizon tasks. → *Adjacent (context management, not personal memory); cite to delimit.*
- **GitOfThoughts: Version-Controlled Reasoning and Agent Memory You Can Replay, Diff, and Merge** (arXiv 2606.14470). Versions *reasoning traces*; five-substrate comparison; **null result:** memory helps only when new problems resemble stored ones; git's value = auditability/history/merge. → *Must-cite; see §8 for why the null result favors our setting.*

### B. Memory orchestration & small-model routing (the orchestrator design)
- **MemFlow: Intent-Driven Memory Orchestration for Small Language Model Agents** (arXiv 2605.03312). Router-vs-Executor split; SLM does routing. → *Blueprint for our 4B orchestrator; closest to our routing idea.*
- **Hierarchical Memory Orchestration for Personalized Persistent Agents** (arXiv 2604.01670). → *Same problem framing; compare design choices.*
- **SWE-Grep / SWE-Grep-Mini** (HN 45607822). RL-trained small model for fast multi-turn grep retrieval. → *Precedent for a small model doing the navigation job; relevant if we do Phase-2 SFT/RL.*
- **MEMTIER: Tiered Memory Architecture & Retrieval Bottleneck Analysis** (arXiv 2605.03675). → *Tiering ideas for hot/cold nodes.*
- **AgentIR: Workload-Adaptive Cascade Retrieval Substrate for Long-Term Conversational Memory** (arXiv 2605.25092). → *Cascade = our RAG-assist → agentic refinement pattern.*
- **Learning When to Remember: Risk-Sensitive Contextual Bandits for Abstention-Aware Memory Retrieval in LLM-Based Coding Agents** (arXiv 2604.27283). Bandit controller decides inject/abstain/ask; notes null-retrieval abstention is well-calibrated. → *Must-cite for §4.5-2; our abstention differs: verified absence from navigation traces, not an injection-routing decision.*

### C. Structured memory systems (baselines & comparison)
- **Mem0** (ECAI 2025). First broad head-to-head of 10 memory approaches on LoCoMo; documents **RAG's aggregation failure**. → *Primary comparison + our motivation source. Baseline 1.*
- **Zep** — temporal knowledge-graph memory; +18.5% on LongMemEval via temporal structure. → *Shows structure > embeddings; the comparison point for the §4.5-1 claim.*
- **Letta / MemGPT** — OS-style paged memory for agents. → *Conceptual ancestor of orchestrated memory.*
- **PersonaAgent: Bridging Memory and Action for Personalized LLM Agents** (arXiv 2506.06254). Episodic + semantic persona memory. → *Personalization comparison.*
- **PersonaTree: Structured Lifecycle Memory for Person Understanding** (arXiv 2606.04780). → *Another hierarchical personal-memory point.*
- **Memory-R1 / Mem-α** — RL for explicit memory operations (extract/consolidate/forget) over flat stores. → *Relevant to Phase-3 retrieval-optimal writing; our delta = hierarchical store + navigation-success reward.*
- **ShardMemo** (arXiv 2601.21545), **CALMem** (arXiv 2605.20724). → *Adjacent memory architectures for breadth.*

### D. Benchmarks (evaluation targets)
- **LongMemEval / LongMemEval-V2** (arXiv 2605.12493). **Primary target.** Tests updates, temporal, aggregation, abstention. → *Where the win must show.*
- **LoCoMo.** Standard multi-session conversational memory benchmark. **Secondary/legibility.**
- **PersonaMem-v2** (arXiv 2512.06688). Implicit user personas + agentic memory. → *Personalization-flavored eval.*
- **PERMA: Benchmarking Personalized Memory Agents** (arXiv 2603.23231). → *Event-driven personal eval.*
- **MCP-Persona: Benchmarking LLM Agents on Real-World Personal Applications** (arXiv 2606.02470). → *Closest to our "real personal data" ethos; check their protocol for our testbed.*
- **Towards Root Memories: Implicit Logical Memory Retrieval for Personalized LLMs** (arXiv 2606.23283). → *Hard-recall cases for personal memory.*
- **BEAM** (referenced in Mem0's 2026 benchmark roundup). → *Additional memory benchmark to consider.*

### E. Why NOT just a better embedder / personalization mechanisms we are NOT using
*(Context so collaborators know these roads were considered and rejected — the retrieval substrate is saturated.)*
- **Jina-embeddings-v4** — unified 3.8B embedder beating ColPali on ViDoRe + CLIP-level image retrieval. → *Evidence the embedding substrate is solved; don't compete here.*
- **SteerX** (arXiv 2510.22256), **Contrastive Activation Steering for Personalization** (arXiv 2503.05213), **Steerable Chatbots** (arXiv 2505.04260), **persona vectors**. → *Activation-steering personalization — a whole crowded subfield we deliberately avoid.*
- **Embedding-to-Prefix** (arXiv 2505.17051), **POPI** (arXiv 2510.17881), **TSUBASA** (arXiv 2604.07894). → *User-embedding / prefix personalization — likewise occupied.*

### F. The usefulness signal (our own prior work — optional governor)
- **Usefulness thermometer:** `u(m | ctx, a) = logP(a | m+ctx) − logP(a | ctx)` — a measured (not judged) usefulness ruler; basis in **REPLUG** and **Atlas** (perplexity-as-retrieval-signal). → *Prior experiments showed it ≈ similarity for retrieval, so it is NOT the core mechanism — but it is the natural persistence gate / reward for Phase-3 retrieval-optimal writing (§6).* See internal `project-ttl-memory-probe`.

### G. Foundations & context
- **Lost in the Middle: How LMs Use Long Contexts** (Liu et al.). → *Core motivation for external memory over context-stuffing.*
- **Model Context Protocol (MCP)** — Anthropic. → *Our serving/interoperability layer.*

### H. Surveys (for fast orientation of new readers)
- **Memory in the Age of AI Agents** (arXiv 2512.13564).
- **Externalization in LLM Agents: A Unified Review of Memory, Skills, Protocols and Harness Engineering** (arXiv 2604.08224).
- **Memory in Large Language Models: Mechanisms, Evaluation and Evolution** (arXiv 2509.18868).
- **Mem0 — "State of AI Agent Memory 2026"** (blog). → *Current leaderboard numbers (LoCoMo/LongMemEval).*

---

## 10. Glossary
- **Node** — one markdown file in the store = one topic/situation/episodic memory.
- **Orchestrator** — the small (4B) model that decides what to read/search.
- **Agentic loop** — iterative `ls`/`grep`/`cat`/`git log`/`git diff` navigation until the answer is found or abstained.
- **RAG-assist** — coarse embedding-based candidate-node suggestion feeding the orchestrator.
- **Episodic memory** — first-person, situation-anchored note ("next time I…, watch out for… because last time…").
- **Temporal layer** — git history; current state lives in files, change history lives in commits.
- **Verified abstention / proof-of-absence** — abstaining because the agent traversed the relevant subtree and confirmed nothing exists, with confidence from navigation-trace features (vs. a similarity threshold).
- **Trace distillation** — generating navigation supervision by logging a strong model's successful loop, then SFT-ing the small one on it.
- **Retrieval-optimal writing** (Phase 3) — rewarding the write path on whether the navigator can later find and use what it wrote.

---
*v0.2 — living document. Update as design/results evolve.*
