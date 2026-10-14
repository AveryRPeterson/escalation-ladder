# Evaluation run 1 (2026-10-13): the tasks do not separate the arms

Six tasks (T1-T6), four arms, one rep each, headless `claude -p` in fresh temp directories.
Every run passed every hidden unit. Cost is the CLI's `total_cost_usd`.

| Arm | Setup | Units | All-pass | Cost | $/run | s/run | Advisor calls |
|---|---|---|---|---|---|---|---|
| A | sonnet-5-5, effort low, advisor opus | 113/113 | 6/6 | $1.53 | 0.26 | 33 | 0 |
| B | haiku-4-5, advisor opus | 113/113 | 6/6 | $1.71 | 0.28 | 134 | 0 |
| C | opus-5-5, effort high, no advisor | 113/113 | 6/6 | $3.51 | 0.59 | 75 | - |
| D | A plus the ladder on `balanced` | 113/113 | 6/6 | $1.56 | 0.26 | 45 | 0 |

## What it shows

- **Quality does not separate the arms.** Even haiku with no effort setting solved all six. A decision
  between the ladder and a fixed model cannot be made from this run.
- **Cost does.** Fixed opus-high cost 2.3x sonnet-low for the same pass rate. Haiku cost about the same as
  sonnet-low in dollars but took 4x as long (36 turns against 9 on T1, 35 against 11 on T2).
- **The ladder added nothing and cost nothing.** D matched A on cost ($1.56 against $1.53) and on results.
  With every task passing at the base rung there was nothing for it to climb to, so this does not test
  escalation at all. It only shows the ladder, review and spend accounting are harmless when not needed.
- **The advisor was never called**, in any of the 18 runs that had one set. Arms A, B and D were therefore
  no-advisor runs. On tasks this easy the executor does not consult.

## Decision rule from the advisor review

D has to beat A on cost at equal pass rate, or beat A on pass rate within a cost bound. It did neither,
because A already passed everything. Not decided: the climbing is neither supported nor retired.

## Caveats

- One rep per cell. The cost gaps (C against A) are large enough to trust; differences under about 20%
  are not.
- T1's first prompt described a symptom backwards and left a boundary convention unstated; a smoke run of
  that version failed under arm D (5/9) and passed under A (9/9). The prompt was fixed before this run
  and the smoke runs are not in the table.
- `est_main_usd` in the result records is wrong (the iteration list carries no model id for main-model
  messages); use `total_cost_usd`.

## Next

Calibrate harder tasks against arm A alone first (about $0.25 each) until sonnet-low fails roughly half
of them, then rerun all four arms on those. Candidates: multi-file bugs with a misleading symptom, a spec
with an internal contradiction the model must flag, and long-horizon tasks (20+ steps) where loops and
stalls can occur.
