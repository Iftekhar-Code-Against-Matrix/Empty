# PCP — Personal Context Protocol
### Finalized v1 research doc
### A deep, orchestrated, agentic memory engine over a versioned personal wiki — served over MCP

> **Status:** FINAL v1.2 (supersedes idea doc v0.3) · **Owner:** Iftekhar · **Date:** 2026-07-16
> **Audience:** PhD advisor + team + AI collaborators picking this up cold.
> **v1.0 changes (vs v0.3):** benchmark decision corrected and finalized (LongMemEval-V2 **dropped as primary** — it is a *web-agent trajectory* benchmark, not chat memory; original LongMemEval is primary); competitor analysis (DiffMem) completed with verified facts and leaderboard standing; "leaderboard reality" section added (vendor self-reports vs controlled comparisons — this reshapes how Claim 1 is judged); drawbacks-of-git-versioned section made explicit; methodology guardrails hardened (fixed reader model, self-reproduced baselines); sanity-check verdict recorded; implementation steps split into `PCP_IMPLEMENTATION_v1.md`.
> **v1.1 changes (discussion round, same day):** commit granularity corrected — **real-time, one commit per message** (not per session); **temporal checkout** added as a claimed capability and eval mode (§2.1); write path elevated to first-class — *writing = the index* — with failure decomposition metrics (§5.5); abstention upgraded to calibrated selective prediction; headline framing = accuracy-vs-cost **Pareto frontier**; router made escapable with hit-rate as a first-class metric; usefulness thermometer **cut from v1** (parked with Phase 3).
> **v1.2 changes (positioning round, same day):** **PersonaMem-v2 promoted to headline benchmark** — PCP's identity is *personal context*, and the headline claim (§5.0) is now the first external-memory-system measurement on implicit personalization; LongMemEval demoted to the rigor/mechanism layer (git C-subset + abstention calibration as ablation-level proof points, per the Day-0 pilot in `pilot/`); git reframed as plumbing we *prove* works, not the identity we defend.

---

## 0. TL;DR (read this first)

PCP is a **personal memory layer for LLMs**. Everything the user has ever told an AI lives in a **git-versioned, human-readable wiki** (an Obsidian-compatible vault of markdown files). Retrieval is not a vector lookup — it is a **two-stage orchestrated process**:

1. A **fast router** (tiny model, target ~1000–1200 tok/s — a target to validate, not a spec) instantly picks *where in the tree to look*.
2. A **small orchestrator (4B)** then **navigates agentically** — `ls`, `grep`, `cat`, and `git log`/`git diff` — until it has the precise memories that matter, or has *verified* that nothing exists.

- **Space** is indexed by the directory tree; **time** is indexed by git history — no temporal knowledge graph needed.
- **Compression is reversible:** every episodic memory carries a provenance link to the raw chat transcript it was distilled from.
- **Time travel is free:** memory is written in real time — every message is a commit — so the store can be checked out *as of any past moment* (§2.1): an eval superpower (point-in-time replay) and a user feature ("answer as I knew it in March").
- **Served as an MCP server** (local/self-hosted): `recall(context)` / `remember(note)` — any host model plugs in.

**What we claim (v1.2):** not a new storage mechanism (filesystem memory, small-model routing, and git-backed stores all exist — §4). We claim **one headline measurement** — the first external memory system evaluated on implicit personalization (PersonaMem-v2, where frontier LLMs score 37–48% — §5.0) — plus **two mechanism claims** nobody has measured (§5.1–5.2), on a **testbed nobody has** (a real multi-year personal archive), under a **controlled harness nobody in this space uses** (§5.4 — the field runs on vendor self-reports).

---

## 1. The problem (unchanged from v0.3, condensed)

LLMs have amnesia; the industry fix is extract → embed → cosine-retrieve (RAG). On personal context this has four documented structural failures, each of which maps to a PCP mechanism:

| # | RAG failure | Evidence | PCP answer |
|---|---|---|---|
| 1 | **Aggregation** — can't combine facts spread across sessions | Mem0 paper (ECAI 2025) | Topic tree + agentic traversal |
| 2 | **Temporal reasoning / updates** — returns stale chunks | Zep built a temporal KG precisely for this (arXiv 2501.13956) | **Version control**: files = now; `git log`/`diff` = how it got there |
| 3 | **Lossy compression** — summaries with no way back | *Verbatim Chunks Beat Extracted Artifacts* (arXiv 2601.00821) | **Provenance links** episodic note → raw transcript |
| 4 | **No abstention** — always returns *something* | LongMemEval abstention split | **Verified absence** from navigation traces |

**Our bet:** the fix isn't a better retriever — it's a better **organization + navigation** layer.

---

## 2. Architecture (finalized — carried from v0.3 unchanged)

```
 flat context (current conversation)
        │
        ▼
 ┌──────────────────────────────────────────────────────────┐
 │ (1) FAST ROUTER — tiny model (≤1B class)                  │
 │     "which subtree(s) of the wiki are relevant?"          │
 │     assisted by: ANN (dense) + BM25 indexes over nodes    │
 └──────────────────────────┬───────────────────────────────┘
                            ▼
 ┌──────────────────────────────────────────────────────────┐
 │ (2) ORCHESTRATOR — 4B model (Qwen3-4B / Gemma-3-4B)       │
 │     agentic loop over the selected subtree(s):            │
 │       ls → grep → cat → git log → git diff → (repeat)     │
 │     assist signals it MAY consult: ANN, BM25 (hybrid)    │
 │     provenance drill-down: episodic note → raw transcript │
 └──────────────────────────┬───────────────────────────────┘
                            ▼
 (3) compact memory package — or verified abstention
        │
        ▼  served over MCP (recall / remember)
      any host model

 ┌────────────── THE STORE (one git repo, one Obsidian vault) ──────────────┐
 │  wiki/    ← episodic + semantic memory nodes (topic directory tree)      │
 │  chats/   ← RAW LAYER: full transcripts, append-only, provenance targets │
 │  every update = a git commit  →  history IS the temporal index           │
 └───────────────────────────────────────────────────────────────────────────┘
```

Ten layers as in v0.3 §2 (raw layer, wiki layer, provenance, git engine, router, agentic retriever, abstention, write path, MCP, deferred optical substrate). The three walkthroughs (spatial / temporal / provenance drill-down) carry over verbatim from v0.3 §3.

**Write path, corrected (v1.1):** memory is written **in real time as the chat grows — every message is a commit.** The hot path is cheap (append to `chats/`, commit; no LLM); distillation into wiki episodic nodes runs incrementally/async as its own commits. This kills DiffMem's 60–600s write-latency problem by construction and makes the temporal index **message-granular**.

**Router discipline (v1.1):** the router is a hint, not a cage — the orchestrator can always back out to the tree root when a routed subtree dead-ends. **Router hit-rate** (gold subtree ∈ routed set) is a first-class reported metric, so a routing failure can never masquerade as a navigation failure.

### 2.1 Temporal checkout (new claimed capability, v1.1)

Because the store is one git repo with per-message commits, `git checkout <commit>` reconstructs the **entire memory state as of any past moment** — deterministically, for free. Nothing else in the field can replay its own past states this cheaply (Zep's bi-temporal queries require explicit bitemporal graph modeling; git gives snapshots as a side effect of the write path). Three uses:

1. **Eval superpower — point-in-time replay:** re-ask any benchmark question against the store as-of-session-k and verify the answer *evolves correctly* as knowledge accumulates (before the switch it should say Razorpay; after, GoKwik). This is a knowledge-update evaluation mode no baseline can run, and it goes in the eval plan (§5).
2. **User feature:** "answer this as I would have known it in March" — a knowledge-cutoff query.
3. **Debugging/forensics:** `git bisect` finds exactly when a memory was corrupted, or when the writer first learned a fact.

---

## 3. FINAL benchmark decision (corrects v0.3)

### 3.1 The correction: LongMemEval-V2 is NOT our benchmark

v0.3 listed "LongMemEval / -V2" as primary. **This was wrong and is fixed here.** Verified against the paper (arXiv 2605.12493, May 2026): **LongMemEval-V2 evaluates *web-agent trajectory* memory** — 451 questions over 100–500 WebArena/WorkArena trajectories (25M–115M tokens), testing static state recall, dynamic state tracking, workflow knowledge, environment gotchas, and premise awareness. It is about agents becoming "experienced colleagues in specialized environments." It is **not** user-assistant chat memory, and its top baselines are coding-agent-style systems (AgentRunbook-C, 72.5%).

- **Consequence for PCP:** V2 is *out of scope for v1* but is flagged as **future work** — PCP's navigate-a-filesystem design is exactly the shape of V2's best baseline (a file-based agent), so an eventual "PCP for agent experience" extension is natural. Do not chase it now.

### 3.2 Final benchmark stack (restructured in v1.2)

| Role | Benchmark | Why | Status of field |
|---|---|---|---|
| **HEADLINE** | **PersonaMem-v2** (arXiv 2512.06688; HF `bowen-upenn/PersonaMem-v2`) — 1,000 personas, 20k+ implicit preferences, 300+ scenarios, multi-session, up to 128k tokens; MCQ + open-ended | This *is* personal context — implicit preferences revealed over long histories, the exact regime PCP is for. **Massive headroom:** frontier LLMs (GPT-5-class) score **37–48%**. Their own trained Qwen3-4B agentic-memory model (55.2 MCQ / 60.7 open) *beats GPT-5 long-context* — independent validation of the small-orchestrator thesis | **No external memory system (Mem0, Zep, anyone) has published a number.** First-mover measurement, on the headline axis |
| **Rigor / mechanism layer** | **LongMemEval (original, ICLR 2025, arXiv 2410.10813)** — pin the **`longmemeval-cleaned`** HF release | The splits the *mechanism* claims live on: knowledge-update **C-subset** (per the Day-0 pilot: ~3–4% of questions are genuinely history-required — reported per-bucket, with tokens/query), **abstention** (calibration), temporal (won by dates in notes). Baselines with published controlled numbers exist here (Zep) | Vendor self-reports of 94–95% are uncontrolled (§5.4); Zep gpt-4o temporal 62.4% is the honest reference |
| **Secondary** | **LoCoMo** | Lingua franca; legibility with reviewers | Near-saturated (ByteRover 96.1% SOTA; Mem0 92.5; single-session categories 96–99). Not where the win lives — report it, don't optimize for it |
| **Distinguishing** | **Real personal archive** (ours) | The ownable data nobody else has; requires the labeling protocol (§7) to be a finding rather than a demo | Unique to us |
| **Stretch (optional, week 4+)** | **BEAM** (scale: scores collapse 64.1→48.6 from 1M→10M tokens; temporal hardest category) or **MemoryArena** (active memory use: LoCoMo-saturated systems drop to 40–60%) | If time allows, one scale or one agentic-use datapoint inoculates against "you only measured passive recall" | Emerging; do not block v1 on these |

**Metrics:** per-split QA accuracy, tokens/query, end-to-end latency (router + loop). The win lives in **temporal / update / abstention**.

**Headline framing (v1.1): the Pareto frontier, quality first.** The money-plot is **accuracy vs cost** (tokens/query, latency, $/query, infrastructure footprint) — git + local 4B + zero infra vs graph-DB + extraction pipeline + cloud LLM — not an accuracy bar chart where uncontrolled vendor numbers loom. Quality first, then speed; but parity-at-a-fraction-of-the-cost is a win on this axis, and vendors cannot compete on it because they cannot show their harness.

---

## 4. The git-versioned competitor: DiffMem — full analysis

### 4.1 What it is (verified 2026-07-16)

**DiffMem** (github.com/Growth-Kinetics/DiffMem, **896★**, production — powers "Annabelle," a persistent-memory companion on WhatsApp/Messenger):

- Git + markdown store; files hold only the **"now" view**; git diffs/logs hold evolution — *the same core bet as PCP's temporal layer.*
- Three agents: **Writer** (transcript → staged git updates), **Retrieval** (shells out to `grep`, `git log`, `git diff`, `git blame` — "no vector databases, no embeddings, no BM25 — just git and an LLM"), **Consolidator** (out-of-band dedupe/redistribute/link).
- Runs on **OpenRouter, GPT-4o-class models**; the README itself states smaller models produce materially worse entity linking and temporal reasoning.

### 4.2 Where it stands on the leaderboard: **nowhere**

This is the central competitive fact, now verified from three independent angles:

1. The DiffMem repo reports **no LoCoMo and no LongMemEval numbers** — none in README or docs.
2. The public LongMemEval leaderboard (omegamax.co/benchmarks) lists OMEGA (95.4%), Mastra (94.87%), Emergence AI (86%), Zep/Graphiti (71.2%), with Mem0/Letta/others at N/A — **DiffMem does not appear at all**.
3. Mem0's "State of AI Agent Memory 2026" survey of the field **does not mention DiffMem, ByteRover, or any git/filesystem-based system** — the entire git-versioned approach is invisible in the benchmark discourse.

**So: our closest overall prior has zero measured standing.** The mechanism exists in production; the measurement does not exist anywhere. That is precisely the gap PCP's Claim 1 fills, and it is why "measure, don't invent" survives review.

### 4.3 Drawbacks of the git-versioned approach (DiffMem's and, honestly, ours)

These are the weaknesses we must engineer around and *report*, not hide:

| # | Drawback | Who it bites | PCP mitigation |
|---|---|---|---|
| 1 | **Write latency.** DiffMem documents 60–600s per write (LLM + git I/O). Commit-on-every-write is expensive if the LLM sits in the hot path. | DiffMem | Per-message commits touch only the raw append (no LLM); distillation runs incrementally/async; write latency still reported as a metric |
| 2 | **Big-model dependence.** DiffMem needs GPT-4o-class for usable entity linking/temporal reasoning — no small-model story. | DiffMem | The router + 4B-orchestrator cascade **is our delta**; if 4B fails multi-hop, fall back 7–8B (risk §7) |
| 3 | **Lexical-only retrieval.** Pure grep fails on paraphrase/topical queries; *Is Grep All You Need* (arXiv 2605.15184) confirms vectors win when queries are genuinely paraphrased or the corpus outgrows linear scan. | DiffMem | PCP keeps ANN+BM25 as **assist signals** — hybrid, each ablatable |
| 4 | **History doesn't survive reorganization cheaply.** `git log --follow` survives renames; **grep-over-history does not**; knowledge linting = renames. | Both | Linting policy: prefer edits over moves; test rename-survival explicitly (risk §7) |
| 5 | **Repo growth.** Append-only transcripts + full history grow unboundedly; `git log` over a large repo slows. | Both | Scaling curve is a deliverable (1×/10×/100× nodes, week 4); shallow-clone/pack strategies if needed |
| 6 | **No proof it's better.** Without benchmark numbers the whole approach is a plausibility argument. | DiffMem (fatal for a paper) | **The entire point of PCP v1** |
| 7 | **No abstention, no router, no MCP, no provenance drill-down** in DiffMem. | DiffMem | These four are exactly PCP's additions; DiffMem-style config runs as **Baseline 3** to isolate them |
| 8 | **Security surface.** A retrieval agent shelling out to `grep`/`git` must be sandboxed (path traversal, command injection via query strings). | Both | Tool layer is a whitelisted, arg-sanitized wrapper — never raw shell (implementation doc §3) |
| 9 | **Concurrency.** One git repo, one writer; concurrent sessions can race. | Both | v1 is single-user/single-writer by scope; serialize commits via a write queue |

### 4.4 Leaderboard reality check (new section — reshapes Claim 1)

The public "leaderboard" for LongMemEval is **not a controlled comparison**:

- Top numbers (OMEGA 95.4, Mastra 94.87, Mem0 94.4) are **vendor self-reports** with different reader models, harnesses, and question subsets; several major systems publish nothing (N/A). Community critique ("benchmark theatre") documents that reported numbers are unstable and prone to silent revision.
- The only *peer-reviewed, per-split, baseline-controlled* numbers remain **Zep's paper** (arXiv 2501.13956): gpt-4o overall **71.2%** vs 60.2% full-context baseline; per-split gpt-4o: single-session-user 92.9, single-session-assistant 80.4, preference 56.7, multi-session 57.9, **knowledge-update 83.3**, **temporal-reasoning 62.4** (latency 2.58s vs 28.9s).
- *Is Grep All You Need* (arXiv 2605.15184) shows end-to-end accuracy is **dominated by the harness and tool-calling style, not the retrieval algorithm** — meaning cross-paper score comparisons are close to meaningless.

**Consequences, now baked into the eval plan:**
1. **Claim 1 is judged against baselines we reproduce ourselves under one fixed harness and one fixed reader model** — not against Zep's published 71.2% (different reader, different year). Zep's paper numbers remain the *published reference point*; the *measured* comparison is our own Graphiti/Zep-OSS run (or, if infra cost is too high, the documented published-number comparison with the caveat stated).
2. We **publish per-split numbers, tokens/query, latency, and the full harness** (reader model, prompts, seeds). In a field of vendor self-reports, a controlled open harness is itself a contribution.
3. We never compare our best config against baselines' worst; every baseline gets the same reader model and the same answer-extraction prompt.

---

## 5. The measured claims (restructured in v1.2: one headline + two mechanism claims)

### Claim 0 (HEADLINE) — A Personal Context Protocol, measured on personal context 🏆
- **The identity claim:** PCP is a personal context layer; it gets judged on a *personal context* benchmark, not a generic recall benchmark.
- **Exists:** PersonaMem-v2 shows frontier long-context LLMs manage only 37–48% on implicit personalization, and that a *trained* Qwen3-4B with agentic memory beats GPT-5 long-context — the small-model-with-memory thesis is independently validated.
- **Does NOT exist:** any external memory system (Mem0, Zep, Letta, anything) has published a PersonaMem-v2 number. The personalization leaderboard for memory systems is empty.
- **Falsifiable claim:** *"A prompted, off-the-shelf PCP stack (tiny router + 4B navigator over a versioned personal wiki) with a fixed reader model beats frontier long-context on PersonaMem-v2 and is competitive with their trained end-to-end 4B — while being model-agnostic, private, and auditable."* Their trained 4B cannot serve other models; PCP serves any host over MCP.
- **Note the fit:** implicit-preference inference stresses the **write path** (distilling unstated preferences into wiki nodes) — exactly where §5.5 says the results are decided. The headline benchmark and the write-path investment point the same direction.

### Claim 1 (mechanism) — Version-history navigation as the temporal layer
- **Exists:** DiffMem proves buildability (production, 896★). Zep proves temporal *structure* beats embeddings (+18.5% relative on LongMemEval; temporal split 62.4% gpt-4o) — via a temporal KG.
- **Does NOT exist:** any benchmark number for the git approach (verified §4.2).
- **Falsifiable claim:** *"A versioned filesystem plus a small agent that reads history matches temporal-KG performance on the temporal and knowledge-update splits, at a fraction of the infrastructure, under an identical harness."* If false, that's still publishable (KGs earn their complexity).
- **Scoped by the Day-0 pilot (v1.2):** only ~3–4% of LongMemEval questions are genuinely history-required, so this claim is reported on the hand-labeled **update-chain (C) subset** with **tokens/query** as the co-equal metric (the old value is always recoverable from raw `chats/` — git makes it *cheap*). Git is plumbing we prove works, not the identity we defend; if the ablation is null, PCP loses nothing — the headline claim doesn't depend on it.

### Claim 2 (mechanism) — Navigation-grounded abstention
- **Exists:** LongMemEval scores abstention; *Learning When to Remember* (arXiv 2604.27283) does abstention-aware injection via bandit (must-cite).
- **Does NOT exist:** abstention as **calibrated proof-of-absence from navigation traces** (coverage of routed candidates, subtrees visited, greps issued) rather than a similarity threshold.
- Scored on LongMemEval's abstention questions; vector-RAG Baseline 1 structurally cannot compete (a low cosine score is not evidence of absence).
- **Upgraded to calibrated selective prediction (v1.1):** not just abstention-split accuracy — report **risk–coverage curves, ECE, and reliability diagrams** for the trace-derived confidence score vs the naive similarity threshold. "PCP knows when it doesn't know, with a calibration curve to prove it" is a demoable result no vendor self-report can imitate, and it plugs into the selective-prediction/hallucination literature.

### Baselines (unchanged roles, hardened execution)

| Baseline | What it isolates | Execution note |
|---|---|---|
| 1. Vector RAG (Mem0-style) | The thing to beat | Run Mem0 OSS ourselves, same reader model |
| 2. Plain filesystem memory (ByteRover-style: tree, no router, no git tools) | Our additions vs "just files" | ByteRover (arXiv 2604.01599) is LoCoMo SOTA at 96.1% — cite prominently; reimplement the pattern, don't fight their number on their benchmark |
| 3. Git-memory (DiffMem-style: big-model agent, no router/cascade) | Router + small-orchestrator design | Same store, GPT-4o-class agent, no router — the cleanest Claim-1 ablation |
| Reference point | Zep paper per-split numbers | Published comparison; reproduced run if budget allows |

**Key ablations:** ± router · ± each assist signal (ANN / BM25 — thermometer cut in v1.1, parked with Phase 3) · **± git tools (= Claim 1)** · trace-based vs naive abstention · ± provenance drill-down · orchestrator 4B vs 7–8B · (later) ± optical return path.

### 5.5 Write path = the index (elevated in v1.1)

Retrieval can only find what the writer wrote, in the tree the writer built — ByteRover's 96.1% is mostly *curation* quality. Treat the wiki like a large, well-organized codebase: main folders → subfolders → things are easy to find because **writing IS the index.** Consequence for eval: every miss must be attributable. For each failed query, log exactly one bucket:

- **write-miss** — the gold fact exists in no node (writer/curation failure);
- **route-miss** — the fact's subtree was not in the routed candidate set (router failure);
- **nav-miss** — the router was right but the orchestrator never reached the node (navigation failure).

Without this decomposition, week-2 results are un-debuggable and a bad tree makes the retriever look bad with no way to tell.

### 🚩 Methodology guardrails (hardened in v1)
1. **One harness, one reader model, all systems.** (New — forced by §4.4.)
2. Never train the orchestrator on the reported benchmark vs training-free baselines; if fine-tuning: synthetic/separate training source tested zero-shot, or cross-benchmark transfer (train LoCoMo → test LongMemEval).
3. **Benchmark→git mapping must be mechanical and mirror the real write path:** replay benchmark histories chronologically, message by message — raw append + **one commit per message** (no LLM in the hot path), distillation commits interleaved async — never hand-crafted per question, or the temporal result is fake.
4. Bootstrap confidence intervals (500-question benchmark = noisy splits; abstention split is small).
5. Latency is a promise: measure router+loop end-to-end or don't say "real-time." The ~1000–1200 tok/s router figure is a **target to validate**, never written as a spec.
6. Report negative results per-split; do not average away a losing split.

---

## 6. Training plan (unchanged from v0.3)

- **Phase 1 (week 1): everything prompted, zero training.** Prompted 4B navigation is plausible per ByteRover / *Is Grep All You Need*; router starts as ANN+BM25 candidates + a prompted tiny model. If prompted PCP clears reproduced-RAG, the core is de-risked.
- **Phase 2 (if plateau): trace distillation.** Strong model runs the loop on the training split; keep success traces; SFT the 4B; distill router into a fast subtree classifier.
- **Phase 3 (stretch, parked): retrieval-optimal writing** (reward writer on downstream navigation success; thermometer as persistence gate).
- **Models:** orchestrator Qwen3-4B / Gemma-3-4B (fallback 7–8B); router ≤1B class.

---

## 7. Timeline & risks (updated)

≈1 month, aggressive but staged so every week ends with a standalone result:

- **Week 1 — Baselines & pipeline:** store schema; prompted loop; **reproduce Baselines 1–2 on LongMemEval_S under the fixed harness → numbers by day 7.** (This is the hard gate: if baseline reproduction slips, cut Baseline 2 before cutting the harness discipline.)
- **Week 2 — PCP v1:** commit-on-write + git tools; router + assists; trace-based abstention; per-split eval + ablations. **Claims 1–2 measured here.**
- **Week 3 — Real-data testbed** (+ optional Phase-2 SFT): labeling protocol + personal-archive run.
- **Week 4 — Write-up + scaling curve** (1×/10×/100× nodes: navigation success/tokens/latency vs RAG's flat curve) + optional BEAM/MemoryArena datapoint.

**Risks (v0.3 list carries over; updated/new items):**
- **Crowded field** → protection remains the honest measure-don't-invent framing; §4.2 verifies the measurement gap is still open as of 2026-07-16.
- **DiffMem proximity** → cite prominently, run as Baseline 3; delta = router + small orchestrator + abstention + provenance + MCP + *the measurements*.
- **Leaderboard optics (new):** reviewers may ask "why is your overall number below OMEGA's 95.4?" → preempt: those are uncontrolled vendor self-reports with undisclosed harnesses; our contribution is a controlled per-split comparison, and we publish the harness.
- **Reader-model confound (new, from *Is Grep All You Need*):** harness dominates retrieval algorithm → fixed reader model everywhere; harness in the repo.
- **GitOfThoughts null result** → memory transfers only in high-resemblance regimes = an argument *for* personal context; say it before a reviewer does.
- Router speed target unvalidated · 4B too weak (fallback 7–8B) · real-data labeling rigor · write-path drift + rename-vs-grep-history · provenance link rot (chats/ append-only, linting never rewrites it) — all as in v0.3.

---

## 8. Sanity-check verdict (recorded 2026-07-16)

**Overall: the project is sound and the window is still open.** Specifically:

1. **The gap is real and verified.** No git-versioned memory system has any benchmark number anywhere (repo, leaderboards, or the field's own 2026 state report). Claim 1 remains unclaimed territory.
2. **The framing is right.** "Measure, don't invent" + honest §4 scope is the correct defense in a crowded field; keep it.
3. **The architecture needed no change** — v1 confirms v0.3's layered design. What needed fixing was measurement: the V2 mix-up (§3.1) and the naive "compare to Zep's published number" plan (§4.4).
4. **Biggest scientific risk:** the field's headline numbers (94–95%) make an "our number is lower but controlled" story harder to sell casually — mitigated by per-split focus (temporal/update/abstention, where even Zep's controlled numbers are 57–83%) and by publishing the harness.
5. **Biggest execution risk:** the 1-month timeline with baseline reproduction in week 1. Baseline reproduction is unglamorous and always slower than expected; it is also non-negotiable (§5 guardrail 1). Protect week 1.
6. **Additions in v1:** leaderboard-reality section; fixed-harness guardrail; drawbacks table (§4.3); optional BEAM/MemoryArena stretch; V2 flagged as future work for an agentic-experience extension.
7. **Subtractions in v1:** LongMemEval-V2 as primary (wrong domain); comparing directly against vendor self-reported numbers; **(v1.1)** usefulness thermometer cut from the assist set (own prior work showed ≈ similarity; parked with Phase 3 as the write gate). Optical substrate stays deferred, Phase 3 stays parked.
8. **v1.1 additions:** temporal checkout (§2.1) as claimed capability + eval mode; write-path failure decomposition (§5.5); calibrated selective-prediction methodology for Claim 2; Pareto-frontier headline framing; per-message real-time commits; escapable router with hit-rate metric.
9. **v1.2 repositioning:** the project's identity is *personal context*, and the headline now matches it — PersonaMem-v2 (empty memory-system leaderboard, 37–48% frontier ceiling, and its own paper independently validates the 4B-with-memory-beats-GPT-5 thesis). LongMemEval becomes the rigor/mechanism layer; the git result is scoped to the update-chain C-subset per the Day-0 pilot and no longer carries the story. This removes v1's biggest optics risk (item 4 above) entirely: on the headline benchmark there are no vendor numbers to be compared against.

---

## 9. Prior work (deltas from v0.3 — verification pass 2026-07-16)

Verified this pass: **ByteRover** = arXiv 2604.01599 ✓ (LoCoMo SOTA 96.1%, 5-tier retrieval, zero infra — Baseline 2 anchor). **Is Grep All You Need** = arXiv 2605.15184 ✓ (grep ≳ vectors, but *harness dominates* — now also cited for the reader-model guardrail; note its LongMemEval subset is 116 questions, not the full 500). **Zep** = arXiv 2501.13956 ✓ (per-split numbers in §4.4). **LongMemEval** = arXiv 2410.10813, ICLR 2025 ✓. **LongMemEval-V2** = arXiv 2605.12493 ✓ — *web-agent trajectories; reclassified from §D primary to future work.* **DiffMem** = github.com/Growth-Kinetics/DiffMem ✓ (896★; facts in §4). Remaining v0.3 IDs (§9 B/C/D/E/F/H/I of the idea doc) carry over **unverified** — run the same double-check before formal citation.

---

## 10. Pointers
- Architecture walkthroughs, glossary, MCP/product section: idea doc v0.3 (unchanged, still authoritative for those sections).
- Implementation steps: **`PCP_IMPLEMENTATION_v1.md`** (same directory).

*v1.0 — finalized. Update as results land.*
