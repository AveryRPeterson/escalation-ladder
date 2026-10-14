# Native advisor tool vs the ladder's consult_oracle

Written for issue #9 (step 3). Read 2026-10-04. **How it was read:** the Claude Code page
(`code.claude.com/docs/en/advisor`) came back whole through a summarising fetch; the API page
(`platform.claude.com/.../advisor-tool`) was too large and only its first part was seen. Nothing
below was tested live. Items marked *inferred* are my reading of the docs, not documented behaviour.

## What exists (documented)

- Claude Code ships an **advisor**: a stronger model that the main model can consult mid-task.
  Set with `/advisor <model>`, the `advisorModel` setting, or `claude --advisor <model>`.
- It is a **server tool** on the Anthropic API only (not Bedrock, Vertex, Foundry). It needs
  feature-flag fetching on, so `DISABLE_TELEMETRY` and similar turn it off. `CLAUDE_CODE_DISABLE_ADVISOR_TOOL=1` removes it.
- **The main model decides when to call it.** There is no setting to cap or force calls; you steer it by saying so in the prompt.
- The advisor sees the **full conversation** including tool calls and results, and returns guidance. No cap parameter in Claude Code.
- **Works over Remote Control** (and desktop, `-p`, the Agent SDK): `/advisor` with no argument prints the current advisor, `/advisor <model>` sets it, `/advisor off` clears it. Needs Claude Code 2.1.260 or later.
- **Pairing rule:** the advisor must rank at or above the main model. From the docs table: Haiku 4.5 accepts Fable/Opus/Sonnet; Sonnet 5.5 accepts Fable, Opus 5 or later, Sonnet 5.5; Opus 5 / 5.5 accepts Fable or Opus 5 or later. Haiku can call an advisor but cannot be one. A below-rank advisor is simply not attached.
- If the **API refuses a pairing** Claude Code attached, it resends the request without the advisor, silently, and the advisor stays off until `/clear` or `/compact`, even after you switch models.
- **Cache:** toggling `/advisor` does not invalidate the main model's cache. The advisor's own read of the transcript is not cached; each call processes the full transcript anew.
- **Cost:** advisor tokens bill at the advisor model's rates and count in `/usage`.
- Subagents inherit the configured advisor and are checked against their own model.

## Overlap with consult_oracle

| | consult_oracle (ours) | native advisor |
|---|---|---|
| Who calls it | the main model, via our MCP tool | the main model, via a server tool |
| What the stronger model sees | last 80 rows of the session | the full conversation |
| Can it use tools | no | no (advice only) |
| Cap | none yet (issue 10) | none in Claude Code |
| Works on a phone / Remote Control | yes (it is a tool) | yes (`/advisor` is a command) |
| Visible to the mod | yes, we are the tool | not documented for mods |
| Cache | fresh prompt, no cache | cache not reused by the advisor |

It is the same idea, so the native one is the likely long-term replacement for the consult half.

## Interactions with the ladder (inferred, to test)

1. **The ladder changes the main model per request; the pairing rule is about the main model.** If Claude Code checks the pairing against the session model while the ladder rewrites the request model, the advisor may be attached to a request on a rung it does not pair with. If the API then refuses, the advisor is silently off for the rest of the conversation. *Safest setting to test first:* `/advisor opus` (Opus 5 or later), which the table pairs with every rung we use: Haiku 4.5, Sonnet 5.5, Opus 5.5. A Sonnet advisor would stop pairing the moment the ladder reaches the oracle rung.
2. **Double escalation.** The ladder can move to Opus while the advisor is also Opus. That is not wrong, but the two mechanisms are not coordinated: the ladder cannot tell that an advisor consult already happened.
3. **Spend accounting.** Advisor tokens show in `/usage` but not in the ladder's per-tier spend table or `/ladder status`.
4. **Visibility.** The mod typings available here do not mention the advisor at all. Whether it appears to `tool.call` or in a `turn.step` result's `toolUses` is unknown, so the ladder may not be able to count consults without help.
5. **Prompt steering.** Anthropic reports executors under-call the advisor on coding tasks and publishes a prompt block for it (vendor-reported). A mod can edit system-prompt sections (`prompt.section`, `prompt.compose`) but doing so changes the system prompt on every request, which costs one cache re-write when the ladder is toggled and needs tuned wording. Not done; needs a decision.

## Recommendation

Keep `consult_oracle`; do not replace it yet. Run these live checks, in order, then decide:

1. With the ladder on at a low rung, run `/advisor opus`, do a task, and read `/ladder status` and `/usage`. Does the advisor appear (an "Advising" line) and what does it cost?
2. Let the ladder escalate to the oracle rung with the advisor still set. Does consulting keep working, or does it silently stop (the refusal path)?
3. Check whether advisor calls are visible to the mod: add a temporary log of `tool.call` and `turn.step` `toolUses` names during step 1.

If 1-3 are clean, the plan is: advisor for planning/consult moments, the ladder for the move-up/move-down decisions, `consult_oracle` demoted to a fallback for non-Anthropic-API setups.

## Live results (2026-10-04)

**Check 1 — advisor attaches and answers on a rewritten rung.**
- **Passed:** `/advisor opus` + task run at rung 1 (worker: `claude-sonnet-5-5`/medium) attached the advisor and answered on a tool call.
- **Cost and "Advising" line:** visible only in `/usage` — ask the user for it.
- **Rung 0 (scout) untested:** the ladder started there, escalated to rung 1 on step 25 (stall heuristic). No advisor call at rung 0.

**Check 2 — advisor survives escalation to oracle.**
- *Correction (2026-10-13): the pin-reset explanation below is wrong. A new prompt keeps the pin and its rung; see the status section at the end.*
- **Inconclusive:** pinned oracle (tier 3) but each new user prompt triggers `startsNewTask()`, which resets the task state including the pin. The oracle rung was not maintained through a request. Workaround: a non-user-prompt request (peer/task-notification origin) would preserve the pin, but those are rare in testing.

**Check 3 — advisor visibility to the mod.**
- **Inconclusive:** oracle rung not reached due to check #2 issue. Temporary logging code is in place (`register.tsx` line ~343). Will activate once check #2 methodology is fixed.

**Ladder note:** scout → worker escalation on step-count stall (25 steps, healthy metrics: error streak 0, no loops) = false positive of the maxStepsPerTier heuristic on clean iteration. Worth tracking for the spike.

**Test infrastructure gap:** The ladder's `startsNewTask()` logic treats `bridge` origin (user prompts) as task-resetting events. This blocks long-running state checks (like pinning to a specific rung and making multiple requests on it). Testing checks #2 and #3 properly requires either:
- *Correction (2026-10-13): the pin-reset explanation below is wrong. A new prompt keeps the pin and its rung; see the status section at the end.*
1. Mocking `startsNewTask` in a test harness, or
2. Using non-bridge origins (e.g., peer/subagent hand-offs), or
3. Running checks in a single integrated test that doesn't cross user-prompt boundaries.

## Testing improvements needed for robust mod validation

The escalation-ladder mod's decision logic is a state machine with complex interactions. Current testing (69 unit tests + manual live checks) misses cross-tier transition coverage. Recommended improvements:

**High priority:**
- **State-machine property tests:** Generate random sequences of signals (errorStreak, loopStrikes, stepsPerTier, manual pin/unpin) and verify the ladder's response is deterministic and safe (never escalates past breaker, always respects pins, handles cooldown correctly).
- **Complete checks #2 and #3 with automated assertions:** Fix the `startsNewTask()` boundary issue (either mock it or use non-bridge origins) so oracle rung and advisor visibility can be tested end-to-end in CI, not manually.

**Medium priority:**
- **Loop detector ring-buffer edge cases:** Verify behavior at ring wraparound (call 27 when cap is 26), mixed trip modes, and state reset during a loop strike.
- **Step-count stall false-positive measurement:** Property test: run known-healthy task sequences (no errors, no loops, real progress) and measure false-escalation rate to inform threshold tuning.

**Low priority:**
- **Mock advisor tool for test harness:** Simulate advisor pairing failures and cost overruns without depending on real API calls.

**Root cause of checks #2 and #3 block:** The ladder's `startsNewTask()` resets task state on every user prompt (bridge origin), including tier pins. This is by design for user-facing sessions but breaks multi-request state tests. Solution: either (1) add a test mode where `startsNewTask()` can be mocked, or (2) run checks #2 and #3 in an isolated session that doesn't cross prompt boundaries.

## Issue #9 status (2026-10-06): checks 1 and 2 passed; check 3 is negative

- **Point 5 (prompt steering): removed (2026-10-13).** A headless session with `advisorModel` set and the ladder off already carries the harness's own "# Advisor Tool" section ("You have access to an `advisor` tool backed by a stronger reviewer model..."), which tells the model when to consult. The mod's `prompt.compose` section duplicated it, so the hook and its guard are gone. Whether that built-in wording gets consults on coding tasks is the open question, not the mod's.
- **Check 1 (advisor attaches on a rewritten rung):** passed at rung 1.
- **Check 2 (advisor survives the oracle rung):** passed. The crypto-design prompt ran one step on the oracle rung (spend: oracle +1 step, other rungs unchanged) and the advisor fired in that step. The pin survived the new-prompt reset. Not exercised: the oracle rung here was `claude-sonnet-5-5`, so the case where the main model outranks the advisor (refused pairing) is untested.
- **Check 3 (advisor visible to the mod):** **negative.** My temporary `turn.step` log of `toolUses` named `advisor` recorded nothing during the crypto run, although the advisor fired (the transcript holds `server_tool_use` and `advisor_tool_result` blocks for it). The engine typings explain why: `tool.call` never fires for a server tool (the step showed 0 tool calls), `TurnStepResult.toolUses` is the response's client tool calls, and `TurnUsage` is four token counts plus the model, with no advisor breakdown. The earlier "PASS" in this file rested on the on-screen banner, which shows the user the advisor ran, not that the mod can see it.
- **Untested route for check 3:** `$.session.messages({ as: "api" })` returns transcript blocks intact, so a `turn.complete` hook could count `server_tool_use` blocks named `advisor`. Not tried.
- **`LADDER_TEST_MODE`: removed.** It was never needed. The new-prompt reset has always kept `pinned` and the pinned rung (`register.tsx`, the reset in `prompt.submit`), and check 2 passed without it.
- **Review:** catches real problems (leftover type errors, off-task work) and escalates on fail.

**Still open:** advisor token cost (the transcript's `usage.iterations` has an `advisor_message` entry the mod never sees), and the check 3 route above.

