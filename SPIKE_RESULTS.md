# Spike Results — All Scenarios Verified

**Date:** 2026-10-02  
**Session:** https://github.com/AveryRPeterson/escalation-ladder (private)

## Scenario 1: Mid-turn model switch ✓

**What was tested:** Haiku→Opus switch mid-turn, with Haiku's thinking and tool history already in the conversation.

**Result:** API accepted the switch. Both directions work (down-step to Sonnet also succeeded).

**Cache findings:**
- First visit to a model: full context cache write (Haiku 143K, Opus 169K on ~200K token session)
- Return to a recently-used model: cache hit (Sonnet 210K read from 3-min-old cache)
- **Implication:** On large contexts, `consult_oracle` (fresh prompt, no cache rewrite) is the right oracle path. Switching the whole task is expensive per-model until its cache warms.

## Scenario 2: Step-down rule ✓

**What was tested:** Automatic tier decay after N clean steps.

**Result:** After 4 clean steps (frugal preset), tier moved down: `oracle (3) → senior (2)` at 18:16:13, then `senior (2) → worker (1)` at 18:18:03.

**Data:** Recorded in state.json log as `deescalate 3→2 "4 clean steps"` with timestamp.

## Scenario 3: Loop detection ✓

**What was tested:** Identical tool call with same result, repeated 3× in a row.

**Result:** 
- Loop 1 (18:55:34): 3× Bash `false` → loop detected → escalate `scout (0) → worker (1)`
- Loop 2 (18:56:07): 3× Bash `false` again → loop detected → escalate `worker (1) → senior (2)`
- Loop 3 (18:56:09): 3× Bash `false` again → loop detected → **circuit breaker trips**

**Message to user:** "Stop repeating this; choose a materially different approach or report that you are blocked."

## Scenario 4: Review rejection ✓

**What was tested:** Independent reviewer catches false claims in answers.

**Result:**
- 18:34:47 Review marked "fail": answer claimed "/ladder log confirmed" but never ran it → escalate to worker
- 18:35:49 Review marked "fail": answer claimed "/ladder log was running" but it wasn't → escalate to worker
- Each failure triggered escalation for a correction attempt.

## Scenario 5: Circuit breaker ✓

**What was tested:** After 3 loops despite escalation, the breaker should stop the task.

**Result:** 
- After loop strike 3, task stopped with message: "3 loops in one task despite escalation. Send a new prompt to continue (this resets the breaker)."
- Final state: `isBroken: true`, `loopStrikes: 3`, `tier: 2 (senior)`, `escalations: 2/3`

## Token spend across this spike session

Snapshot of `state.json` at 2026-10-02 (spend accumulates, so earlier figures in this file are stale):

| Tier | Steps | Input | Output | Cache read |
|---|---|---|---|---|
| scout | 42 | 323 | 19,615 | 6.14M |
| worker | 18 | 38 | 16,934 | 3.66M |
| senior | 6 | 12 | 13,495 | 1.36M |
| oracle | 3 | 6 | 8,605 | 468K |
| review:senior | 4 | 10,076 | 3,974 | 0 |
| **Total** | **73** | **10,455** | **54,623** | **11.63M** |

## Known limitations still open

- **Subagents not managed:** Loop detection and escalation only work on main loop; subagent loops are not escalated.
- **Pinning:** (code-read + unit test, not live) `decide` returns `hold` for every signal when pinned, and only `moveTier` increments `escalations`, so pinning does not drain the budget. The 3-strike loop breaker still applies. Live check needs the user to run `/ladder pin`.
- **Effort downgrade:** The engine silently downgrades effort for models that don't support it (e.g., Haiku `low` may go unsupported). No feedback to the ladder.
- **Review on empty context:** A task with no tool calls doesn't trigger review (minToolCalls=3), so false reasoning is only caught if tools were used.
- **Milestone reviews:** Rely on the model calling `checkpoint()` explicitly; no automatic trigger.

## Next steps for production

1. Test subagent escalation (add agent.spawn hook to escalate a spawned subagent).
2. Measure cache cost on small contexts (< 10K tokens) to confirm consult vs. switch trade-off.
3. Add dollar-based ceiling (not just token counts per tier).
4. Verify effort values are actually honored by each model (log what was asked vs. what was used).
5. Refinement loop on calibration: tune `confidenceThreshold` from real model self-reports.

## Unplanned live finding: fail-open fired

`state.json` ends with a `breaker` event: `ladder turned off: claude-haiku-4-5-20251001 (scout) was rejected`. The fail-open path turned the ladder off after the scout tier's request was rejected, so the session was not wedged. The cause of the rejection is not yet known (`/ladder probe` would say whether Haiku is currently usable).

## Verification labels

- Verified live: mid-turn switch, step-down, loop escalation, breaker, review-fail escalation, fail-open.
- Unit-tested (23 tests): `decide` incl. pinned, `normalizePolicy` clamps, alias mapping, loop detector.
- Code-read only: refusal at oracle, review skipped below `minToolCalls`, effort downgrade.
