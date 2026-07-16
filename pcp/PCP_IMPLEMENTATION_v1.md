# PCP v1 — Implementation Plan
> Companion to `PCP_RESEARCH_v1.md` · FINAL v1.0 · 2026-07-16
> Everything here is scoped to the 4-week research build. Product/hosted concerns end at "local MCP server."

---

## 0. Deliverables (definition of done)

| # | Deliverable | Done when |
|---|---|---|
| D1 | Eval harness (fixed reader model, per-split scoring, CI bootstrap) | Baselines 1–2 reproduce on LongMemEval_S with numbers we trust |
| D2 | PCP store + write path (wiki/, chats/, provenance, commit-on-write) | Mechanical benchmark→git ingestion runs end-to-end, one commit per session |
| D3 | Agentic retriever (4B orchestrator + tool layer) | Beats Baseline 1 on ≥1 hard split, prompted only |
| D4 | Router + assist signals (ANN, BM25, thermometer) | Ablation table row exists for each |
| D5 | Trace-based abstention | Calibration curve + abstention-split score vs naive threshold |
| D6 | Claim-1 measurement (± git tools; DiffMem-style Baseline 3) | Per-split table incl. temporal/update, tokens/query, latency |
| D7 | Real-archive testbed + labeling protocol | ≥100 self-authored QA pairs incl. temporal/update/abstention; contamination controls documented |
| D8 | MCP server (`recall`/`remember`, stdio) | Works from Claude Code/Desktop against the local store |
| D9 | Write-up + scaling curve (1×/10×/100×) | Plots + limitations section drafted |

---

## 1. Repo layout

```
pcp/
  pyproject.toml            # uv-managed; python 3.12
  src/pcp/
    store/                  # git+markdown store
      schema.py             # node frontmatter, provenance link format
      writer.py             # distill → episodic nodes → commit
      linter.py             # knowledge linting (edits > moves; never touches chats/)
      gitio.py              # commit queue (single-writer), log/diff/blame wrappers
    tools/                  # the agent's tool layer — whitelisted, arg-sanitized
      fs.py                 # ls, cat, grep (ripgrep), tree  — NO raw shell
      git.py                # git_log, git_diff, git_blame, git_follow
      assists.py            # ann_search (faiss + bge-small), bm25 (tantivy/rank_bm25), thermometer
    router/
      candidates.py         # ANN+BM25 candidate subtrees
      router.py             # prompted tiny model (≤1B) → subtree choice; later: distilled classifier
    orchestrator/
      loop.py               # agentic loop, budgets (max steps/tokens), trace logging
      abstention.py         # trace features → calibrated absence score
      prompts/
    mcp/
      server.py             # stdio MCP: recall(context), remember(note)
    eval/
      harness.py            # ONE harness: fixed reader model, fixed answer prompt, seeds
      ingest_longmemeval.py # mechanical chronological ingestion → commits
      ingest_locomo.py
      baselines/
        b1_vector_rag.py    # Mem0-OSS style
        b2_flatfs.py        # ByteRover-style: tree, no router, no git tools
        b3_diffmem.py       # big-model agent, git tools, no router
      score.py              # per-split accuracy, tokens/query, latency, bootstrap CIs
      ablate.py             # flag-driven: --no-router --no-git --no-ann --no-bm25 ...
  configs/                  # model endpoints, budgets, one YAML per experiment
  results/                  # committed JSON + tables per run (append-only)
  docs/                     # this file + research doc
```

**Store schema (D2):**
- `wiki/<topic-path>/<node>.md` — YAML frontmatter: `created`, `updated`, `provenance: [chats/2026/07/session-0714.md#msg-042, ...]`, `tags`.
- `chats/YYYY/MM/session-*.md` — append-only; one anchor per message (`#msg-NNN`).
- Every write = one commit; commit message = machine-readable (`memory(<path>): <one-line>`), because commit messages are themselves retrieval surface for `git log`.

**Models/serving:** orchestrator Qwen3-4B via llama.cpp/ollama (fallback Qwen3-8B); router Qwen3-0.6B class; embeddings bge-small-en-v1.5; reader model for eval = one pinned API model for ALL systems (pick once in week 1, write it in `configs/harness.yaml`, never change mid-project).

---

## 2. Week-by-week

### Week 1 — Harness + baselines (the hard gate)
1. **Day 1–2:** eval harness (D1): LongMemEval_S loader, fixed reader model + answer-extraction prompt, per-split scorer, bootstrap CIs, token/latency accounting. Smoke-test on 20 questions.
2. **Day 2–3:** store schema + mechanical ingestion (`ingest_longmemeval.py`): sessions in chronological order → wiki nodes + chats/ + one commit per session. **No per-question hand-crafting — enforce in code review.**
3. **Day 3–5:** Baseline 1 (vector RAG) and Baseline 2 (flat filesystem agent) through the harness.
4. **Day 5–7:** prompted PCP loop v0 (no router yet, orchestrator gets whole tree): does a prompted 4B navigate at all? Log every trace.
5. **Gate:** numbers by day 7. If baseline reproduction slips, drop Baseline 2 to week 2 — never drop harness discipline.

### Week 2 — PCP v1 + the claims
1. Router (candidates.py + prompted tiny model) in front of the loop; measure router hit-rate (is the gold subtree in the routed set?) as its own metric.
2. Git tools into the loop; **Claim 1 run:** full PCP vs `--no-git` vs Baseline 3 (big-model, no router) on temporal/update splits.
3. Abstention (D5): trace features (candidate coverage, subtrees visited, greps issued, dead-end ratio) → logistic/calibrated score; compare vs naive "nothing retrieved" and vs similarity threshold on the abstention split.
4. Full ablation grid (`ablate.py`), one YAML per row; results committed to `results/`.
5. Validate router throughput on real hardware — record the measured tok/s; stop quoting 1000–1200 until this exists.

### Week 3 — Real archive + optional SFT
1. Labeling protocol (D7): export personal archive → ingest; self-author ~100+ QA pairs across splits (incl. update chains and true-absence questions); contamination rule: question author ≠ answer verifier session; document everything (this protocol is a mini-contribution).
2. Run PCP + Baselines 1/3 on the archive.
3. *Only if week-2 plateaued:* Phase-2 trace distillation (strong model traces → filter to successes → SFT 4B via LoRA; train on LoCoMo-derived traces, test LongMemEval zero-shot).

### Week 4 — Scaling, MCP polish, write-up
1. Scaling curve: synthetically grow the tree 1×/10×/100× nodes; plot navigation success / tokens / latency vs RAG's flat curve.
2. MCP server (D8) finalized: stdio, `uvx pcp-server`, config snippet for Claude Code/Desktop; loop stays internal (host never sees ls/grep).
3. Optional stretch: one BEAM or MemoryArena datapoint.
4. Write-up: per-split tables + CIs, ablations, limitations (incl. §4.3 drawbacks table from the research doc), harness released.

---

## 3. Engineering guardrails

- **Tool layer safety:** never `subprocess(shell=True)` with model-controlled strings. `fs.py`/`git.py` take structured args, whitelist flags, jail all paths inside the store root, cap output bytes per call.
- **Budgets:** hard caps per query (max loop steps, max tool-output tokens, wall-clock timeout) — enforced in `loop.py`, reported in results. An unbounded agent invalidates the latency claim.
- **Trace logging is not optional:** every run logs `(state, action, observation)` — it feeds abstention features (D5), Phase-2 SFT data, and debugging.
- **Single-writer git:** all commits through `gitio.py`'s queue; linting produces edits over moves where possible; linting never rewrites `chats/`; add a rename-survival test (`git log --follow` vs grep-over-history) to CI.
- **Results are append-only** in `results/` with the config hash — no silent re-runs replacing numbers (the exact failure mode we criticize in vendors).
- **Pin everything:** reader model, prompts, seeds, benchmark version/commit, in `configs/harness.yaml`.

---

## 4. Decision log (v1)

| Decision | Choice | Reason |
|---|---|---|
| Primary benchmark | LongMemEval (original), _S size | V2 is web-agent trajectories — wrong domain (research doc §3.1) |
| Comparison method | Self-reproduced baselines, one fixed harness | Vendor self-reports uncontrolled; harness dominates (research doc §4.4) |
| Zep comparison | Published per-split numbers as reference; reproduce Graphiti only if budget allows | Full reproduction is heavy infra; the honest caveat is acceptable |
| Orchestrator | Qwen3-4B first, prompted | Phase-1 de-risking before any training |
| Router speed | Measured, not promised | Hardware-dependent target |
| Optical substrate | Deferred (unchanged) | Prior art saturates the mechanism |
| Phase 3 (RL writer) | Parked (unchanged) | A project of its own |
