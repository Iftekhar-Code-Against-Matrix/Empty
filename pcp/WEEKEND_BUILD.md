# PCP — Full Weekend Implementation Spec (all 3 benchmarks)
> v1.0 · 2026-07-17 · companion to `PCP_RESEARCH_v1.md` (v1.2) and `PCP_IMPLEMENTATION_v1.md`
> **Read this as the build order.** Everything is concrete: files, schemas, prompts, budgets, cut lines.

---

## 0. The weekend contract

**Goal:** by Sunday night, PCP v0 (prompted, no training) and Baseline 1 (vector RAG) both produce scored numbers on **all three benchmarks** — LongMemEval (industry standard), PersonaMem-v2 (headline), LoCoMo (checkbox) — under ONE fixed harness.

**The design move that makes 3 benchmarks possible:** a benchmark is just `(ingest adapter, question loader, scorer)`. The store, writer, retriever, and reader are shared. You write the pipeline once; each benchmark is ~1 hour of adapter code.

**Honest scoping:** full runs of everything won't fit in a weekend of compute+budget. The contract is: **seeded stratified subsets first (dev sets), full runs launched overnight if the subsets look sane.** A number on a seeded 100-question subset with stated N is a real number; an unfinished full run is nothing.

**Priorities if time collapses (cut from the bottom):**
1. LongMemEval: Baseline 1 + PCP on 100-q subset ← never cut
2. PersonaMem-v2 MCQ: PCP on subset (MCQ = cheap scoring, no judge)
3. LoCoMo subset
4. Full overnight runs
5. Baseline 1 on PersonaMem/LoCoMo (PCP outranks the baseline on the non-industry benchmarks)

---

## 1. Repo scaffold (build this first, ~30 min)

```
pcp/
  pyproject.toml            # uv init; deps: openai, faiss-cpu, sentence-transformers,
                            #   rank_bm25, gitpython (or subprocess git), pyyaml, tqdm, datasets
  configs/
    harness.yaml            # THE pinned config — see §2
  src/pcp/
    store.py                # store schema + write/commit ops          (§3)
    writer.py               # session → wiki distillation              (§4)
    tools.py                # ls/cat/grep/git_log/git_diff, jailed     (§5)
    assists.py              # ANN + BM25 index over node summaries     (§5)
    agent.py                # the orchestrator loop                    (§6)
    baseline_rag.py         # Baseline 1                               (§7)
    reader.py               # fixed reader model answers from package  (§2)
  bench/
    common.py               # Benchmark dataclass: load(), ingest(), score()
    lme.py                  # LongMemEval adapter                      (§8)
    personamem.py           # PersonaMem-v2 adapter                    (§9)
    locomo.py               # LoCoMo adapter                           (§10)
  run.py                    # python run.py --bench lme --system pcp --subset 100
  results/                  # append-only JSON: {config_hash, bench, system, per_q...}
  stores/                   # one git repo per (bench, user/conversation) — gitignored
```

Rule: **`run.py --bench X --system Y` is the only entry point.** If a result didn't come from it, it doesn't exist.

---

## 2. The harness (pin once, never touch)

`configs/harness.yaml`:

```yaml
reader_model: gpt-4o-mini-2024-07-18   # DECIDE SATURDAY MORNING; cheap enough for full grids.
                                        # Alternative: claude-haiku-4-5. Whatever you pick: FROZEN.
judge_model: gpt-4o-mini-2024-07-18     # for LME/LoCoMo answer judging (PersonaMem MCQ needs none)
orchestrator_model: <api-small-model>   # weekend: cheap API 4B-class (e.g. qwen3-4b via openrouter,
                                        # or haiku). Local llama.cpp is a WEEKNIGHT task, not weekend.
embed_model: BAAI/bge-small-en-v1.5
seed: 42
subset_sizes: {lme: 100, personamem: 100, locomo: 100}
budgets: {max_steps: 15, max_tool_output_tokens: 2000, max_query_seconds: 120}
```

`reader.py` — one function, used by EVERY system on EVERY benchmark:

```
answer(question, memory_package: str) -> str
  "You are answering on behalf of the user, using ONLY the memory package below.
   If the package says no relevant memory was found, say the information is not available.
   Memory package: {package}\n Question: {question}"
```

Per-query logging (into results JSON): tokens_in/out per stage (write, retrieve, read), wall-clock, tool-call trace. **This is non-negotiable — it's the Pareto data.**

---

## 3. `store.py` — the git store (per-message commits)

One git repo per benchmark-user (LME: per question's user history; LoCoMo: per conversation; PersonaMem: per persona). Layout:

```
stores/lme/<question_or_user_id>/
  wiki/<topic>/<subtopic>.md
  chats/<session_id>.md
```

- **Raw path (no LLM):** for each message in chronological order → append to `chats/<session_id>.md` as
  `#### msg-NNN · {role} · {timestamp}\n{content}` → `git commit -m "raw(<session>): msg-NNN"`.
  Batch mode for ingestion speed: it's OK to commit **per session** for the raw layer during bulk
  benchmark ingestion IF the message timestamps are in the file — but commit **per session-distillation**
  for the wiki layer always. (Real-time per-message commits are the product behavior; for bulk
  ingestion of 40 sessions × 500 users, per-session raw commits keep ingestion under an hour.
  Record which mode a store was built in.)
- **Wiki node format:**
  ```markdown
  ---
  created: 2023-04-10
  updated: 2023-05-01
  provenance: [chats/answer_4be1b6b4_2.md#msg-003]
  ---
  # Car — maintenance
  - First service: 2023-04-10. Issue after: GPS not functioning. [chats/...#msg-003]
  ```
  **Every fact gets an explicit date** (Day-0 pilot: the temporal split is won by dates in notes).
- Commit convention: `memory(<path>): <one-line summary>` — commit messages are retrieval surface.

---

## 4. `writer.py` — distillation (where PersonaMem is won/lost)

After each session's raw commit, one LLM call (orchestrator_model):

```
Input: session transcript + current `tree -L 3` of wiki/
Prompt (draft — iterate Sunday):
 "You maintain the user's personal wiki. Given this session and the current wiki tree:
  1. List facts about the user worth remembering (include DATES for every event;
     include PREFERENCES even if implied rather than stated — infer them and mark 'implicit').
  2. For each: the wiki file path it belongs in (reuse existing paths; create sparingly).
  3. Output as: file path → markdown bullet(s) to append/update, with provenance msg refs."
Apply the edits, commit per file touched.
```

Notes:
- **Implicit preferences are first-class** ("user rewrote my formal draft casually → prefers casual tone [implicit]"). This is the PersonaMem-v2 game.
- Updates REPLACE the stale bullet (now-view) — the old value lives in git history. That's Claim 1's substrate.
- Keep a `wiki/_index.md` the writer maintains: one line per file. The router/assists index this.

---

## 5. `tools.py` + `assists.py`

Tools exposed to the agent (all jailed to the store root, output truncated to budget):
`list_dir(path)` · `read_file(path)` · `grep(pattern, path?)` (ripgrep) · `git_log(path?, grep?)` · `git_diff(commit)` · `read_provenance(link)`.
Implementation: structured args → subprocess with fixed argv (never shell=True), path-checked.

Assists (built at ingestion time over wiki files + `_index.md`):
- BM25 (rank_bm25) and ANN (faiss + bge-small) over (path, summary line).
- Exposed as one tool: `search(query) -> top-8 (path, snippet)` — hybrid, interleaved. This doubles as the router for the weekend (see §6).

---

## 6. `agent.py` — PCP retrieval loop (prompted, v0)

**Weekend simplification:** no separate router model. `search()` results are injected as the starting
candidates ("you may want to start here"), and the agent navigates from the tree root. The router as a
distinct fast model is a WEEK-2 item; candidates-as-hint captures most of its value with zero new moving parts.

```
System prompt (draft):
 "You retrieve the user's memories to help answer a question. You have tools:
  list_dir, read_file, grep, search, git_log, git_diff, read_provenance.
  Navigate the wiki. Files show current state; git history shows how facts changed —
  use git_log/git_diff for 'previous value' or 'before X' questions.
  Dates matter: prefer exact dates from notes.
  STOP when you can output a MEMORY PACKAGE: the minimal set of facts (with dates
  and quotes if needed) that answers the question.
  If after searching the likely locations and grepping key terms you find nothing,
  output: NO_MEMORY_FOUND + list of (paths visited, patterns grepped)."
Loop: while steps < max_steps: model → tool call → observation → ... → final package.
```

Abstention v0 = the NO_MEMORY_FOUND path with its evidence list (trace-feature calibration is week 2).
The package (or abstention) goes to `reader.answer()`.

---

## 7. `baseline_rag.py` — Baseline 1

Chunk raw sessions (512 tokens, 64 overlap) → bge-small embeddings → faiss. At query: top-8 chunks
→ same reader. That's it — deliberately vanilla Mem0-style. Same logging.

---

## 8. LongMemEval adapter (`bench/lme.py`) — Saturday

- **Data:** HF `xiaowu0162/longmemeval-cleaned` (the deprecated original is NOT used). LongMemEval_S.
- **Ingest:** per question: its haystack sessions in date order → store (§3) → writer (§4) per session.
  ~40 sessions/question × 100-q subset = ~4k writer calls — batch/parallelize (async, 8 workers).
- **Question loader:** stratified 100-q subset over the 6 types, seed 42 (keep all `_abs` in-subset — they're only 30 in 500; force-include the ~12 temporal/update `_abs`).
- **Scorer:** the official LME judge prompt (in their repo) with judge_model; report per-split + overall.
- **Reference points:** full-context gpt-4o 60.2 / Zep 71.2 (paper, different reader — directional only).

## 9. PersonaMem-v2 adapter (`bench/personamem.py`) — Sunday

- **Data:** HF `bowen-upenn/PersonaMem-v2`. **Text-only English subset, MCQ track only** for the weekend
  (MCQ = string-match scoring, zero judge cost). Open-ended track = next week.
- **Ingest:** per persona: multi-session history → store → writer. Sample 100 MCQs across personas/topics, seed 42.
- **Scorer:** exact-match on the chosen option. Reader prompt gains: "Choose the option best personalized
  to this user. Answer with the letter only."
- **Reference points:** frontier long-context 37–48%; their trained Qwen3-4B 55.2. **Beating 48% prompted is the headline.**

## 10. LoCoMo adapter (`bench/locomo.py`) — Sunday, checkbox

- **Data:** official LoCoMo release (10 conversations, ~200 QA each; categories incl. temporal, multi-hop, adversarial).
- **Ingest:** per conversation → store → writer per session.
- **Subset:** 100 QA stratified over categories, seed 42. Scorer: their F1/judge protocol (judge_model).
- Report the number, move on. Saturation means no glory here — absence would look weird, that's all.

---

## 11. The schedule

**Saturday**
| Block | Work |
|---|---|
| AM-1 (2h) | Scaffold (§1) + harness.yaml decisions (§2) + `reader.py` + results logging |
| AM-2 (2h) | `store.py` + `tools.py` (+ smoke: build a toy store by hand, run each tool) |
| PM-1 (2h) | `writer.py` + `assists.py`; distill 3 LME sessions, eyeball the wiki quality — **iterate the writer prompt here, it's the highest-leverage hour of the weekend** |
| PM-2 (2h) | `bench/lme.py` ingest → build stores for the 100-q subset (parallel); meanwhile write `baseline_rag.py` |
| Eve (1h) | Baseline 1 on 20 LME questions end-to-end incl. judge. **Gate: sane numbers or stop and debug.** |

**Sunday**
| Block | Work |
|---|---|
| AM-1 (2h) | `agent.py` loop; run PCP on the same 20 questions; read every trace |
| AM-2 (2h) | Full 100-q subset: Baseline 1 + PCP → **first per-split table** |
| PM-1 (2h) | `bench/personamem.py`: ingest + PCP on 100 MCQs → **headline number v0** |
| PM-2 (2h) | `bench/locomo.py`: ingest + PCP on 100 QA → checkbox number |
| Eve | Launch overnight full runs (LME 500 both systems; PersonaMem as budget allows). Commit results/, push |

**Budget estimate (sanity):** ~500 writer calls + ~600 agent runs (≤15 small-model steps) + ~600 reader/judge
calls on mini-class models ≈ low tens of $ at 4B/mini pricing. Set a hard spend cap in the provider dashboard Saturday morning.

---

## 12. Definition of done (Sunday night)

- [ ] One results table: rows = {Baseline-1, PCP-v0} × {LME(100), PersonaMem-MCQ(100), LoCoMo(100)};
      columns = accuracy (per-split for LME), tokens/query, latency. Committed to `results/`, pushed.
- [ ] Every number reproducible via `run.py` + config hash.
- [ ] 10 PCP traces read by a human (you), with notes on failure buckets (write/route/nav — even informal).
- [ ] Overnight full runs launched.
- **Deferred on purpose:** router model, trace-calibrated abstention, temporal-checkout replay, C-subset
      labeling, provenance drill-down eval, MCP server, local serving, open-ended PersonaMem, real archive.

## 13. Known weekend shortcuts (so nobody mistakes them for the design)

1. Bulk-ingestion raw commits may be per-session (product behavior stays per-message) — recorded per store.
2. No router model — hybrid `search()` hint instead. Router is week 2, measured against this.
3. Abstention is naive NO_MEMORY_FOUND — trace calibration is week 2 (Claim 2 is NOT measured this weekend).
4. Orchestrator is an API small model — local llama.cpp swap is a weeknight task; latency claims wait for it.
5. Subsets are dev sets — headline reporting uses full runs only.
