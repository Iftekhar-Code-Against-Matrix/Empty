# PCP — Benchmarks: contents, how we run PCP, how we judge, who we beat
> 2026-07-17 · companion to `PCP_ARCHITECTURE_v2.md`

## 0. The bridge problem (read first): static benchmarks have no live host model

PCP's design is **interactive** — a host model decides mid-chat when to `Save`. Benchmarks are **static transcripts**.
So we must define how `Save` is triggered during ingestion. Two modes, both reported:

- **Mode A — Save-all (default, fair to baselines):** every user/assistant turn (or session) is passed to the Writer,
  which decides placement + whether it's memory-worthy. No privileged foresight. This is what all memory systems do.
- **Mode B — Host-policy (our real product):** a host model reads the stream turn-by-turn and calls `Save` only when
  it judges something worth keeping. Report as an ablation — it tests the *Save trigger* itself.

**Recall** is uniform: for each benchmark question, call `Recall(question)` → curated package → the **fixed reader
model** answers using ONLY that package. Same reader for PCP and every baseline (this is the anti-cheating rule).

---

## 1. LongMemEval — the industry-standard rigor benchmark

**What it contains:** chat-assistant long-term memory. `longmemeval-cleaned` (pin this; original is deprecated).
500 questions over ~40-session user histories (~115k tokens, the `_S` size). **6 question types:**
single-session-user, single-session-assistant, single-session-preference, multi-session, **knowledge-update**,
**temporal-reasoning**, plus **abstention** variants (`_abs`, ~30) with deliberately false premises. Each question
ships labeled **evidence sessions** (gold provenance).

**How PCP runs it:** per question → ingest its haystack sessions **in chronological order** into a fresh vault
(Mode A) → per session the Writer files memories + propagates cards → at query, `Recall(question)` → package → reader.
Because evidence sessions are labeled, we can score **write-miss / route-miss / nav-miss** decomposition for free.

**How we judge:** the **official LongMemEval GPT-judge** (their repo ships the prompt) with our pinned `judge_model`.
Report **per-type accuracy + overall**, plus tokens/query and latency. Abstention scored on the `_abs` set (did it
correctly say "not enough info"). Bootstrap CIs (splits are small/noisy).
- **Temporal split is won by dates-in-notes; knowledge-update's genuine "previous value" cases are ~3–4% (Day-0 pilot)**
  → report the git contribution on that labeled C-subset with tokens/query, not on the overall number.

**Reference numbers (context, different harnesses — directional only):** full-context GPT-4o ~60; **Zep/Graphiti 71.2
(temporal 63.8)**; Mem0 ~93–94 self-reported; vendor leaderboard tops 94–95 (uncontrolled). Our number is judged
against **baselines we run ourselves** (§4).

## 2. PersonaMem-v2 — the HEADLINE (personal-context identity)

**What it contains:** implicit personalization. 1,000 personas, **20k+ preferences** (many *implicit* — revealed by
behavior, never stated) across **300+ everyday scenarios** (writing, translation, therapy, medical…), multi-session,
multimodal+multilingual, up to **128k tokens/context**. Two tracks: **MCQ** (4 options, all plausible, one is
personalized to *this* user) and **open-ended generation**.

**How PCP runs it:** per persona → ingest multi-session history (Mode A; the Writer must capture **implicit
preferences** — flag them `[implicit]` — this is where the benchmark is won) → `Recall(query)` → package → reader
chooses the option / generates. **Text-only English subset first**; MCQ track first (cheap scoring).

**How we judge:** **MCQ = exact-match** on the chosen letter (no judge cost). **Open-ended = the paper's LLM-judge
rubric** (personalization correctness) with our `judge_model`. Report accuracy per track.

**Reference numbers (why this is the hill):** frontier long-context LLMs (GPT-5-class) **37–48%**; the paper's *trained*
Qwen3-4B-with-agentic-memory **55.2 MCQ / 60.7 open** and it *beats GPT-5 long-context*. **No external memory system
(Mem0/Zep/Letta/Cognee) has any PersonaMem-v2 number.** Target: **beat 48% prompted (headline), approach/pass 55% (knockout).**

## 3. LoCoMo — the checkbox (near-saturated lingua franca)

**What it contains:** very-long-term conversation memory. ~10 conversations, up to 35 sessions / 300+ turns each,
**1,540 QA** over **4 types: single-hop, multi-hop, temporal, open-domain** (+adversarial). 9k–16k tokens/conv.

**How PCP runs it:** per conversation → ingest sessions → `Recall` per QA → reader. Small enough to run in full.

**How we judge:** the standard LoCoMo protocol — **F1 / judge accuracy per category** (Mem0's harness implements it;
reuse it for exact comparability). Report and move on — saturation (ByteRover 96.1, Mem0 91.6) means no glory here,
only the expectation of *not being embarrassed*.

## 4. Baselines & industry leaders we run ourselves (the real bar)

Vanilla vector-RAG is a strawman — beating it proves nothing. We run these **under our fixed reader + harness**:

| System | What it is | Why include | Runs on |
|---|---|---|---|
| **Vanilla vector RAG** | chunk+embed+top-k | floor / sanity | all 3 |
| **Mem0** (OSS, ~47K★) | vector+graph+KV, auto-extract | *the* default; the number reviewers expect | all 3 |
| **Zep / Graphiti** | temporal knowledge graph | temporal-reasoning leader (must-beat on that split) | LME + LoCoMo |
| **Letta / MemGPT** | OS-style stateful memory runtime | the "agent memory" incumbent | LME + LoCoMo |
| **Cognee** | LLM-built graph memory (14 retrieval modes) | graph SOTA-ish; **also our future graph layer** — one integration, two uses | LME + LoCoMo |
| **ByteRover-style** | hierarchical markdown filesystem, no git/router | isolates "just files" vs PCP's tree+fusion+gatekeeper | all 3 |
| **PCP (ours)** | architecture v2 | — | all 3 |

Where a system publishes a compatible harness (Mem0's benchmark repo already wraps Mem0/Zep/Letta), reuse it; where
not, use each system's official OSS package behind a thin adapter. **Every system gets the identical reader + judge.**

## 5. Harness (off-the-shelf, not hand-rolled)

There is **no single universal harness** (2026 sources agree systems are "cited under different harnesses"). The capable, real stack:
- **Backbone:** the **official LongMemEval eval repo** (rigorous judge prompts, per-type scoring).
- **Multi-system runner:** **Mem0's open benchmark scripts** — they already ingest→query→judge Mem0/Zep/Letta on
  LoCoMo+LongMemEval; we add PCP + Cognee + ByteRover adapters.
- **PersonaMem-v2:** its **official repo eval** (MCQ exact-match + open-ended rubric).
- **Metrics/CIs:** wrap with `deepeval`/`ragas` if convenient, else the official scorers + our bootstrap.
- **Integration seam:** **PCP is an MCP server**; every harness calls the *same* `Save`/`Recall` — so dev, test, and
  the eventual local product are byte-identical. This is the "capable off-the-shelf" answer: don't build a harness,
  adopt the official scorers and expose PCP through MCP.

## 6. Metrics reported everywhere
Accuracy (per split/type) · tokens/query · end-to-end latency · **failure decomposition** (write/route/nav-miss, free on
LongMemEval) · abstention calibration (risk–coverage, once the Gatekeeper's confidence is wired) · **cost/query**.
**Headline figure = accuracy-vs-cost Pareto**, quality first.
