# Edge Cases — Potential Issues Found

## High risk (likely to break)

1. **Effort unsupported by model**
   - The engine silently downgrades effort if a model doesn't support the requested level (e.g., Haiku doesn't support `high`).
   - The ladder has no way to know this happened. It logs spend as if effort was honored.
   - **Test needed:** Send a request to Haiku with effort `high`, check if it's actually sent as `low` or `medium`.
   - **Impact:** Escalation decisions based on "deeper reasoning" might not get it.

2. **Model refusal mid-turn (content policy)**
   - A model can refuse mid-turn (stop_reason: refusal) if content triggered a policy filter.
   - The ladder detects this with `apply({ kind: 'refusal' })` and escalates once.
   - But if the content issue is structural (the task itself violates policy), escalation won't help; all tiers will refuse.
   - **Test needed:** Trigger a model refusal, then escalate and see if the oracle also refuses.
   - **Impact:** Escalation budget wasted; task stops anyway.

3. **Pinned tier + loop** (resolved by code-read and unit test; live check pending)
   - Earlier draft claimed a pinned tier burns escalation budget. That was wrong: `decide` returns `hold` when pinned and only `moveTier` increments `escalations`.
   - Covered by `policy.test.ts` ("decide when pinned"). The 3-strike breaker still applies when pinned.

## Medium risk (incorrect behavior, edge case mode)

4. **Zero or negative cooldown**
   - If `cooldownSteps: 0`, the step-down rule fires immediately after one clean step.
   - `normalizePolicy` clamps to `[1, 100]`, so this should be caught, but let me verify.
   - **Test:** Set cooldownSteps = -5 in stored policy, load it, check if it's clamped to 1.

5. **baseTier >= tiers.length**
   - If `baseTier: 5` but only 4 tiers exist, normalization should clamp to `tiers.length - 1`.
   - Saves from crashing but silently changes the policy.
   - **Test:** Check normalizePolicy handles invalid baseTier.

6. **Review mode with zero tool calls**
   - Review is triggered only if `toolCallsInTask >= minToolCalls` (frugal: 3).
   - If a task has 0 tool calls, the review is skipped.
   - A false answer with no tool calls is never reviewed.
   - **Implication:** For reasoning-only tasks, review is ineffective.

7. **Review on empty or thinking-only answer**
   - If the model only outputs thinking blocks (no text answer), the review generator sees an empty answer.
   - The reviewer might say "no answer provided, cannot assess."
   - **Impact:** Task escalates for fix, but the next run might be the same (empty answer), loop detected.

8. **De-escalation at base tier during error**
   - If at `baseTier` and an error occurs, `shouldStepDown` returns false (tier >= baseTier).
   - The error is handled by the main escalation logic, which might escalate upward.
   - But if the error is something low-level (Bash syntax), escalating doesn't help.
   - **Test needed:** Cause an error at base tier, verify it escalates upward, not sideways.

## Low risk (unlikely, but possible)

9. **Multiple escalation signals in one step**
   - A step could have stop_reason = 'max_tokens' AND be a model refusal AND have a tool error.
   - The code checks in order: maxTokens, refusal, step-budget, step-down.
   - First match wins. If max_tokens is hit, refusal is never seen.
   - **Impact:** Wrong signal attributed if multiple things go wrong.

10. **Cache miss after switching tiers**
    - After escalation, a model's cache from 5 minutes ago is expired (typical TTL ~5min).
    - Re-visiting a tier later in the same task means a fresh cache write, not a hit.
    - The log shows `cacheRead: 0` for the revisit, even if the same model was used earlier.
    - **Impact:** Cost measurement is accurate (each model visit is billed its cache write), but counter-intuitive if a tier is used, then skipped, then used again.

11. **Milestone review without checkpoint call**
    - Review mode is "milestone", but the model never calls `checkpoint()`.
    - Review is never triggered; task completes unreviewed.
    - **Mitigation:** Prompt the model to use checkpoint; or fall back to "task" mode review on completion.

12. **Escalation during review loop**
    - While a review-fail escalation is being handled (model corrects), another loop or error fires.
    - Multiple signals in one turn; first one wins (due to event ordering).
    - **Impact:** Some signals are missed if the turn is crowded.

## Test recommendations

**High priority (likely to surface bugs):**
- [ ] Effort downgrade silent failure
- [ ] Model refusal mid-turn + escalate (does oracle also refuse?)
- [x] Pinned tier + loop: unit-tested (holds, no budget use); live run pending

**Medium priority (edge case correctness):**
- [ ] Review with 0 tool calls
- [ ] De-escalation at base tier (should escalate up, not stay)
- [x] baseTier out of bounds: unit-tested (clamped)

**Low priority (nice to know):**
- [ ] Cache cold on revisit after other tiers used
- [ ] Multiple escalation signals in one step (which wins?)
