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

| Tier | Steps | Input | Output | Cache read |
|---|---|---|---|---|
| scout | 20 | 140 | 6,789 | 2.75M |
| worker | 12 | 24 | 9,085 | 2.23M |
| senior | 5 | 10 | 13,330 | 1.10M |
| oracle | 3 | 6 | 8,605 | 468K |
| review:senior | 3 | 7,878 | 3,002 | 0 |
| **Total** | **43** | **8,058** | **40,811** | **6.64M** |

## Known limitations still open

- **Subagents not managed:** Loop detection and escalation only work on main loop; subagent loops are not escalated.
- **Pinning edge case:** A pinned tier still counts toward escalation budget; if pinned at a high tier and a loop fires, the budget drains even though the tier doesn't move.
- **Effort downgrade:** The engine silently downgrades effort for models that don't support it (e.g., Haiku `low` may go unsupported). No feedback to the ladder.
- **Review on empty context:** A task with no tool calls doesn't trigger review (minToolCalls=3), so false reasoning is only caught if tools were used.
- **Milestone reviews:** Rely on the model calling `checkpoint()` explicitly; no automatic trigger.

## Next steps for production

1. Test subagent escalation (add agent.spawn hook to escalate a spawned subagent).
2. Measure cache cost on small contexts (< 10K tokens) to confirm consult vs. switch trade-off.
3. Add dollar-based ceiling (not just token counts per tier).
4. Verify effort values are actually honored by each model (log what was asked vs. what was used).
5. Refinement loop on calibration: tune `confidenceThreshold` from real model self-reports.
