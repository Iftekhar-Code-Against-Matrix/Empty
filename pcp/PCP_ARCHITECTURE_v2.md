# PCP — Architecture v2 (corrected to owner's design)
> 2026-07-17 · supersedes the "small model greps git" framing in v1.x · owner: Iftekhar
> This is the authoritative system description. `PCP_RESEARCH_v1.md` (benchmarks/claims) and
> `PCP_IMPLEMENTATION_v1.md` (schedule) are re-aligned to THIS.

**One line:** PCP is an MCP memory server where a **Writer** places each memory into a self-describing
folder tree, and a **Retriever** finds it back using the *same descent logic*, fused with dense/BM25/grep,
then a **Gatekeeper** model curates what actually reaches the host — with raw-chat provenance drill-down,
and git/graph as pluggable substrates. Frontier models throughout.

---

## 1. The two MCP tools (the entire host-facing surface)

The host generator model (Gemini 3.5 Flash) sees only two tools. The whole system below is invisible behind them.

### `Save(special_instructions, payload)`
- Fired **mid-chat, by the host model's own judgment**, the moment something is worth remembering.
- `payload` = `chat_metadata` (unique message IDs, timestamps, session id) + `chat_context` (the relevant span).
- `special_instructions` = the host's hint ("remember this as a hard preference", "this supersedes the earlier budget number").
- Returns: the memory ID(s) written + where they landed (for the host's awareness/audit).

### `Recall(special_instructions, chat_context)`
- Returns a **curated memory package** (or verified abstention) for the current context.
- `special_instructions` = "only preferences", "include how this changed over time", etc.

### Drill-down (progressive disclosure, also MCP tools)
- `Recall_source(memory_id)` → the **raw chat message(s)** the memory was distilled from.
- `Recall_full(memory_id)` → the **entire chat** that message belonged to.
- So compression is always reversible on demand, host-driven.

> **Symmetry principle (the core design invariant):** *the path used to decide **where to Save** is the
> same path used to decide **where to Recall from**.* One descent algorithm, two callers. This is what keeps
> writes and reads consistent — a memory is retrievable because it was filed by the identical logic that looks for it.

---

## 2. The store = a self-describing folder tree

```
vault/                         # Obsidian-compatible; git repo; container volume
  memories/
    personal/                  # ← root branches (100s over time)
      _card.md                 #   node card: description + keywords + KV notes + child summary
      preferences/
        _card.md
        communication-style.md # ← leaf: an episodic memory node
      likes/ dislikes/ ...
    business/
      _card.md
      armor/checkouts/ ...
  chats/                       # raw layer, append-only (provenance targets)
    2026/07/session-*.md
  _root_card.md                # top-level index over all root branches
```

### Node cards (`_card.md`) — the index IS the tree
Every folder at every depth carries a card:
```markdown
---
path: memories/business/armor/checkouts
keywords: [razorpay, gokwik, AUD, settlement, checkout, payment-gateway]
kv:
  domain: business
  entity: Armor store
  topics: [payment gateways, checkout flows]
children:
  razorpay.md: "Razorpay integration, AUD settlement gotchas"
  gokwik.md: "GoKwik, active since Mar 2026, theme conflict"
updated: 2026-07-17
---
Description: Everything about checkout/payment-gateway setup for the Armor store.
```
- Cards are what the grader scores. They are BM25-friendly (keywords), ANN-friendly (description embeds),
  grep-friendly (plain text), and `ls`-friendly (they're just files).

### Upward propagation (write-time invariant)
When the Writer creates/edits a leaf or subfolder, it **updates that node's card AND every ancestor card up to
the root**, so each ancestor's `children`/description reflects its whole subtree. A parent always summarizes what
lives beneath it → the grader can prune correctly at every level.
- *Cost, stated honestly:* write amplification O(depth) per save. Fine at research scale; batched, and a periodic
  "card linting" pass keeps drift down. This is the price of making the tree self-describing.

### Seed tree (cold-start)
Ship a starter skeleton so the first Writer call has somewhere to reason from:
`personal/{preferences,likes,dislikes,people,facts}`, `work/`, `projects/`. The Writer grows it from there.

---

## 3. The grader descent (shared Save/Recall core)

The **grader combo** = ANN + BM25 + grep + `ls`, scoring node cards at one level.

```
descend(query_or_memory, node = root):
    cards = ls(node)/_card.md for each child
    scores = fuse( ANN(query, card.description),
                   BM25(query, card.keywords+kv),
                   grep(query terms, card) )      # reciprocal-rank fusion, not raw intersection
    best = argmax(scores); keep top-k as fallbacks
    if best is a leaf OR confidence gap small: return candidate leaf(s) + trace
    else: return descend(query, best)             # recurse into the chosen branch
```
- **Save:** descent returns the target folder. If the payload is **diff-compatible** with an existing leaf
  (same entity/topic) → update that leaf (old value stays in git history). If **genuinely new** → create a new
  leaf/subfolder there, write its card, propagate upward (§2).
- **Recall:** descent returns the most-probable leaf(s) → these enter the fusion pool (§4) and the agentic loop.
- The descent **trace** (levels visited, candidates, confidence gaps) is logged — it feeds abstention and debugging.

---

## 4. Retrieval = 4 retrievers in parallel → fusion → Gatekeeper

On `Recall`, run concurrently (don't serialize):
1. **Tree-index descent** (§3) — the "indexy" path; returns leaf candidate(s) with a location rationale.
2. **Dense/ANN** directly over *leaf memory* embeddings — fast, catches paraphrase the tree pruned away.
3. **BM25** over leaf memories — fast, exact-term.
4. **Agentic grep/`git grep`** — launched immediately, runs *while the tree descent computes* (your parallelism point).
5. **Graph** — DEFERRED experiment (§7), off by default.

**Fusion:**
- Candidates appearing across methods → **qualified candidates** (high confidence). (Implement as
  reciprocal-rank fusion with an agreement boost — pure set-intersection can be empty, so intersection *raises rank*,
  it doesn't gate.)
- The union minus qualified → **"maybe relevant"** pool.

**Gatekeeper / Curator model** (frontier, e.g. Gemini 3.5 Flash) gets a structured brief:
```
grep_returned: [...]
agreed_by_ANN+BM25+index: [...]        # qualified
also_maybe_relevant: [... up to 5 ...]
task: return JSON {pass:[memory_ids], drop:[...], reason:...}
```
Its jobs:
- **Filter stale/negative/contradictory** memories out (this is the anti-hallucination gate — it can consult
  `git diff`/`git log` on a candidate to see if it was superseded).
- Optionally **synthesize a curated memory sample** (a clean digest) instead of dumping raw notes.
- Emit the final package for the host. Nothing reaches the host that the Gatekeeper didn't pass.

> This replaces v1's naive "similarity threshold" abstention: abstention = Gatekeeper returns empty `pass` with the
> descent+grep trace as evidence of absence.

---

## 5. Model roles (frontier-first; no small embedders)

| Role | Model | Notes |
|---|---|---|
| **Host generator** | **Gemini 3.5 Flash** | The chatting model; calls Save/Recall. Also the default for Writer + Gatekeeper. |
| **Writer** | Gemini 3.5 Flash | Distills episodic memory, writes KV notes, decides placement, propagates cards. |
| **Gatekeeper/Curator** | Gemini 3.5 Flash | Fusion → curated JSON package; handles git/time reasoning on candidates. |
| **Ablation tier (subset only)** | **Qwen3-4B, Qwen3-27B(≈Gemma-3-27B?), Grok 4.5** | Swap in on the seeded subsets to plot quality-vs-model-size and prove PCP isn't model-locked. |
| **Embeddings** | Frontier (Gemini embeddings / text-embedding-3-large / Voyage-3 / Qwen-embed) | **Not** bge-small — we iterate on the frontier per owner. Pick one, pin it. |
| **Reranker (optional assist)** | A strong reranker (e.g. Cohere-rerank / Qwen-rerank) | Feeds the fusion stage. |

> Confirm exact API IDs before day 1 (esp. "Qwen 27B" — Qwen ships 32B/14B, Gemma ships 27B; pick the intended one).

---

## 6. Provenance & git (plumbing we prove, not the identity)
- Every memory node's frontmatter carries `provenance: [chats/<session>.md#msg-NNN]` + the source message IDs
  passed in `Save`.
- Git: per-message commits on the raw layer; per-write commits on memories. Enables `Recall`-time diff/log for
  "what changed / previous value", and free **temporal checkout** (answer as-of a past state) for eval.
- If the git ablation shows no benefit on a given split, PCP loses nothing — the tree index + fusion carry retrieval.

## 7. Graph (deferred experiment, not built by us)
- Don't hand-roll a graph. Two options to try **after** the core works: **Obsidian's native backlink graph**, or
  **Cognee** (github.com/topoteretes/cognee — LLM builds an entity/relation graph via its `cognify` pipeline, 14
  retrieval modes, `Remember/Recall/Improve/Forget` API). Plug Cognee in as a **5th retriever** into the same fusion
  stage; measure Δrecall/precision on multi-hop questions. Pure experiment; off by default.

## 8. Deployment & experiment capture
- **Containerizable from day 1:** the vault is a mounted volume; models are endpoint configs; the whole thing runs
  as a **local MCP server** (stdio now, streamable-HTTP later). Dev/test harness talks to the same MCP surface.
- **Save every run artifact** (traces, candidate pools, Gatekeeper JSON, packages, per-stage tokens/latency) to
  `runs/` so future experiments — **image/optical retrieval**, the **graph** layer, reranker swaps — reuse them
  without re-ingesting.

---

## 9. What changed from my earlier (wrong) writeups — so nothing regresses
| Earlier (drifted) | Corrected (this doc) |
|---|---|
| Session-end distillation | **Host-triggered `Save` mid-chat** via MCP |
| One 4B "navigator" greps git | **Writer + Retriever(4 parallel) + Gatekeeper**, frontier models |
| Router = tiny model picks subtree | **Grader descent over self-describing node cards**, same logic for save+read |
| Flat "assist signals" | **Fusion → qualified candidates + maybe-pool → Gatekeeper JSON** |
| bge-small embeddings | **Frontier embeddings/rerankers** |
| Abstention = similarity threshold | **Gatekeeper empty-pass with descent+grep trace** |
| Provenance = a link | **`Recall_source` / `Recall_full` drill-down MCP tools** |
| Graph unspecified | **Cognee/Obsidian as a pluggable 5th retriever, deferred** |

**Open decisions for you (I did not lock these):** (a) exact embedding + reranker models; (b) fusion weights /
whether the Gatekeeper also re-ranks; (c) how "Save-worthiness" is triggered on *static* benchmarks that have no
live host model — see `BENCHMARKS.md §0`; (d) confirm the Qwen-27B identity.
