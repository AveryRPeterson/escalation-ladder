# Review round 1: heavier models review the mod top to bottom

Two read-only Opus reviewers read the whole mod (register.tsx; lib/ and tests). Findings I
checked against the code before acting are marked **checked**; the rest are taken from the
reviewers' reading and were fixed or deferred as noted. Nothing here was exercised in a live
session yet except where stated.

## Fixed (each has a regression test in `hooks/lib/hardening.test.ts` unless noted)

| # | Finding | Fix |
|---|---|---|
| 1 | **checked** Hot reload re-ran `session.start`, which `freshRun`'d the task: pin, breaker, turnId, budgets lost (this is what cleared the pin during the breaker test) | `session.start` keeps the stored run and only re-fits the tier to the policy. Task reset stays on user `prompt.submit`. (No unit test: needs a live reload.) |
| 2 | **checked** `step-budget` with budget spent tripped the breaker; step-down/re-climb cycling could kill a healthy task | only `loop` trips when there is nowhere to go; stalls hold (`maxStepsPerTask` still caps) |
| 3 | **checked** one `max_tokens`/refusal at the oracle, or 3 failing test runs, tripped the breaker | same rule as #2 |
| 4 | `parseVerdict` greedy regex and case-sensitive verdict turned real FAILs into "unsure" | balanced-object scan, last candidate wins, case-insensitive; string/object `issues` kept |
| 5 | Ping-pong ignored results: polling a starting server counted as a loop | results must repeat too |
| 6 | Same-error key used a leading banner (pytest) and kept paths/hashes | key on the last 400 chars; strip paths and hex ids |
| 7 | Bash `description`/`timeout` were part of the call signature, so rewording hid real repeats | dropped from the signature |
| 8 | `pingPong` > 12 could never fit the ring | clamped to 12, ring 26 |
| 9 | `normalizePolicy` threw on tiers without a model; bad effort got the ladder turned off; fractional indices | tiers repaired/replaced, effort validated, indices rounded |
| 10 | Percent-style confidence (40) read as ≥ threshold and blocked escalation; `high-stakes` was held when confident | confidence normalised; high-stakes always escalates |
| 11 | Round-2 review judged against the ladder's own follow-up prompt, not the user's task | follow-up rows skipped when choosing TASK |
| 12 | Reviews re-ran on unchanged work; a FAIL on the last round was resubmitted but never re-reviewed | skip review if no new tool calls; final-round FAIL is reported, not resubmitted |

## New: review cascade
Work is reviewed by a heavier tier than the heaviest tier that produced it
(`pickReviewer(peakTier)`), never below the policy's `reviewerTier`. Oracle work is reviewed by
the oracle. `peakTier` is tracked in `moveTier`.

## Deferred (not fixed, with reason)
- `failOpen` may fire on a user Esc or transient 529 (reviewer #4): depends on the event shape
  for aborts, which the typings here do not show. Needs a live observation.
- Breaker does not cover subagents / ladder tools while broken (#5), parallel `tool.call` races
  (#9), `mirrorState` write coalescing (#10), pane stale-closure and counter reset on policy
  edit (#12), `consult_oracle` loading the whole session (#6), loop history not cleared on tier
  change, reviewer `maxTokens: 800` at effort max possibly truncating.
- `signature()` hashes the whole event object (#11): loops have fired live, so it does work;
  left as is.
