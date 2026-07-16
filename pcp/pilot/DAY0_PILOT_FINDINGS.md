# Day-0 Pilot — Can LongMemEval detect the git mechanism?
> Status: sample classified (40/211) · 2026-07-16 · dataset: `xiaowu0162/longmemeval` oracle file
> ⚠️ Harness must pin **`longmemeval-cleaned`** (the original HF dataset is deprecated for noisy history sessions).

## What this pilot is
Claim 1 is measured by the ±git-tools ablation. If a question is answerable from the **current** state of the wiki files, the agent never needs `git log`/`diff`, and ±git shows no difference — *not because git is useless, but because the question never exercises it.* So every temporal-reasoning (133) and knowledge-update (78) question gets a bucket:

- **A** — answerable from latest file state alone (current value / current habit).
- **B** — needs **event dates**, which live in the notes/frontmatter/session dates — arithmetic over dates, not old values. (`git log` is a convenient date index but not strictly required.)
- **C** — needs an **old, since-overwritten value** ("previous X before current", "when I started vs now"). A now-view file has lost it; only git history (or expensive raw-chat digging) has it. **← Claim 1 lives here.**
- (12 of the 211 are `_abs` abstention variants — they score Claim 2, not Claim 1.)

## Sample results (seed 42, 20 per split)

**Temporal-reasoning (20): B ≈ 17, abstention 3, C = 0.**
The split is almost entirely *date arithmetic*: "how many days between X and Y", "which happened first", "how many weeks ago". Examples: days between starting with the realtor and finding a house (B); which show started first (B); wake-up time on Tuesdays (actually A — a current fact). **No sampled question requires an overwritten value.**

**Knowledge-update (20): A ≈ 9, aggregation/B ≈ 4, C = 4, abstention 1.**
The C questions are exactly the git showcase:
- "What was my **previous** frequent-flyer status **before** my current one?" (know-11 / 50635ada)
- "How many engineers did I lead **when I started** vs **now**?" (know-09 / 031748ae)
- "How often did I play tennis **previously** vs now?" (know-16 / f685340e)
- "Do I go to the gym **more than previously**?" (know-07 / c4ea545c)

Several others are **aggregation-over-time** ("how many MCU films in the last 3 months") — answerable by counting episodic notes/commits in a window; git commits-in-range is a natural tool but notes with dates also work.

## Implications (decisions this forces)

1. **Extrapolated, only ~15–20 questions of 500 (~3–4%) are genuinely history-required.** The ±git ablation will barely move the *overall* number. **Therefore: hand-label all 211 rows (sheet below) and report per-bucket results — "PCP vs baselines on the update-chain (C) subset" is the honest, visible Claim-1 result.** The re-annotation itself is a small publishable artifact (nobody has decomposed LongMemEval this way).
2. **On C-questions, measure tokens/query, not just accuracy.** Without git tools the old value is still recoverable by digging `chats/` — at a much higher token cost. Claim 1's realistic shape: *equal-or-better accuracy at a fraction of the tokens* on the update-chain subset.
3. **The temporal split is won by dates, not diffs.** The writer MUST record event dates in notes (frontmatter + inline), and commit timestamps give session dates for free. This is a write-path requirement, effective immediately.
4. **The real-archive protocol must over-sample update-chains** ("what did we use before X and why did we switch") — the regime public benchmarks under-test, and exactly what personal/business context is full of.
5. **Temporal-checkout replay** (as-of-session-k) remains the history-sensitive eval no baseline can run — it complements, not replaces, the C-subset result.

## Files
- `day0_labeling_sheet.csv` — all 211 temporal + knowledge-update questions (id, type, abstention flag, question, answer, empty bucket column). Finish labeling during Week 1 (~2–3h); the 40 sampled above are recorded here as ground truth to calibrate against.
