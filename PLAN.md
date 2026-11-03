# Spike: tiered model escalation ladder (Claude Code mod)

**Status:** proof of concept written, statically verified (validate, 13 unit tests, strict `tsc`). **Not yet run in a live session.**
**Code:** this repository (mod name `escalation-ladder`). It was developed in a Claude Code dev-mods folder, the directory hot-reload watches; this file is the spike's home.

## Question the spike answers

Can a mod run a task on a cheap model/effort by default and move it up to an oracle tier only when needed, without the failure modes that make auto-escalation dangerous (spinning in a loop, runaway cost, an unreviewed wrong "done")?

## What the mods API gives us (verified in this build's typings)

| Need | Mechanism |
|---|---|
| Pick model and effort per request | `turn.step` hook: `next({ ...e, model, effort })`. This is the whole lever. |
| See what a step cost and why it stopped | `turn.step` result: `usage`, `stopReason`, `toolUses` |
| Detect loops / failures | `tool.call` hook sees every call and its result (`isError`, `text`) |
| Stop a runaway | `$.turn.abort({ turnId })`, plus `{ deny }` from `tool.call` |
| Model-initiated escalation | `$.tool.register` custom tools the model can call |
| Independent review | `$.model.complete({ model, effort, system, prompt })`, no history, any tier |
| Fix-up loop after a failed review | `$.prompt.submit` (queued turn, origin `plugin`) |
| Policy UI | `ui.render` on a `Pane`: Select/Input/Button, plus `/ladder` command and status line |
| Persistence | `$.state` (session, survives hot reload), `$.store` (policy, across sessions) |

## Design

**Ladder.** Ordered tiers, cheapest to strongest, last = oracle. Rungs by preset: `frugal` haiku/max, sonnet/low, sonnet/high, opus/low; `balanced` sonnet/low, sonnet/high, sonnet/max, opus/high; `cautious` haiku/low, sonnet/medium, sonnet/high, opus/max. Haiku is sent no effort (see Unproven 4), so a haiku rung's effort is only a label. Model aliases are editable per tier in the pane (a full model id works too). A task starts at `baseTier` and decays back to it.

**Task** = one user prompt plus any plugin-submitted review follow-ups. A new user prompt resets counters and the breaker.

**Escalation signals** (`lib/decide.ts`, one pure function, signal in, move out):
1. Model asks via `request_escalation({confidence, ask, reason})`. Below threshold climbs one rung; `deeper-reasoning` / `high-stakes` jump to oracle.
2. Loop detected (below).
3. N consecutive tool errors.
4. Stall: too many steps on one rung within a task.
5. `max_tokens` truncation or a refusal.
6. A failed review.

**Two ways to use the oracle.** *Switch*: main loop continues on the oracle (full context, expensive, cache cold). *Consult*: `consult_oracle({question})` returns one answer as a tool result and the cheap model keeps driving. The spike implements both so they can be compared.

**De-escalation.** After `cooldownSteps` clean steps above base, step down one rung. Without this the ladder only ratchets up and the cheap tier's savings vanish.

**Protections**
- *Loop detector* (`lib/loop.ts`): identical call **and identical result** N times (re-running a test after an edit is not a loop); A/B alternation; same normalised error N times. A hit escalates and tells the model via the next tool result. Three loop strikes in one task trips the breaker even with escalation.
- *Circuit breaker*: at the top tier, or with the escalation budget spent, a loop/stall aborts the turn and denies further tools until the user prompts again. Hard cap on steps per task. A model's own request at the top tier only holds; it never trips.
- *Budgets*: max escalations per task, steps per rung, steps per task.
- *Pinning*: `/ladder up|down|pin` fixes the rung; the ladder then only observes (decisions logged as `hold`), but the 3-strike breaker still applies.
- *Review*: `task` mode runs a reviewer (own tier, no history, sees task + tool trail + final answer) when a turn ends with at least `minToolCalls` calls; a fail escalates one rung and submits the issues back, up to `maxRounds`. `milestone` mode reviews inside the model's `checkpoint({summary})` call and returns the verdict as the tool result. Reviewer replies `pass|fail|unsure`; `unsure` is treated as pass-with-note, never as a block.

**Presets:** `frugal` (start on rung 0, task review only), `balanced` (start on rung 0, both reviews), `cautious` (start on rung 2, tight thresholds, 3 review rounds), and `efforttest` (two haiku and two sonnet rungs, for measuring what effort changes; not for real use).

## Using it

`/ladder` opens the pane (tier ladder with per-tier token spend, controls, policy editor, event log). Subcommands: `on|off|up|down|pin|unpin|reset|preset <name>`. Status line shows tier, pin, escalation count.

## What is verified so far

- `claude plugin validate`: passes (hooks, calls and state reads/writes as intended).
- `claude plugin test`: 13/13 on loop detection, the decision table, policy repair, verdict parsing.
- `tsc --strict` against the engine typings: clean. (It caught one real bug: `Input`/`Select` don't exist on the mobile surface; added a read-only fallback.)

## Live finding 1 (2026-10-02): first enable broke the session

With the ladder on, sending a normal prompt failed with "issue with the selected model (sonnet)". Direct `claude -p --model` probes show haiku, sonnet, opus and the full ids all work on this account (Fable 5.1 is out of credits, unrelated). So the account was fine; the likely cause is that `turn.step` sends the model string verbatim and does not resolve aliases the way `$.model.complete` does. **Not yet confirmed** by a live switch.

Changes made in response:
- Tiers now hold full model ids (`lib/policy.ts` `ALIASES`; aliases typed in the pane are mapped on save).
- **Fail open.** If a request on a model the ladder chose returns nothing or throws, the ladder turns itself off and the session falls back to its own model. A bad tier can no longer wedge the session.
- `/ladder on` first runs a one-token probe of every tier and refuses to enable if any is unusable; `/ladder probe` does the probe alone.

## Live finding 2 (2026-10-02): mid-turn model switch WORKS

Measured from the session transcript, one turn, frugal preset, ladder on:

| Step | Model | Cache read | Cache write | Note |
|---|---|---|---|---|
| prior turn | sonnet-5-5 | 208,139 | 2,032 | session's own model, warm |
| 1 | haiku-4-5 | 0 | 142,693 | switch at turn start; cold cache |
| 2 | opus-5-5 | 42,053 | 169,318 | **mid-turn**, after Haiku's thinking + tool_use + tool_result; request accepted |
| 3 | opus-5-5 | 211,371 | 3,179 | warm |
| 4 | opus-5-5 | 214,550 | 5,869 | warm |
| 5 | sonnet-5-5 | 210,379 | 3,638 | one rung down (step-down); Sonnet's cache from 3 min earlier was still warm |

Conclusions:
- Per-request model/effort rewriting is accepted by the API in both directions, including upward mid-turn with another model's thinking and tool history in the conversation. Full model ids are required.
- **Caches are per model.** The first visit to a model re-writes the whole context (here 143K and 169K tokens); returning to a recently used model hits its still-warm cache (Sonnet: 210K read). So switching cost scales with context size and is paid once per model per cache lifetime, and "start cheap" is not cheap on a long conversation until the cheap model's cache is warm. `consult_oracle` (a fresh clipped prompt, no cache re-write) is the right oracle path for large contexts.
- Not directly observed: the ladder's own event log. Step 5 is consistent with the designed step-down but could not be told apart from a fail-open from outside; the pane's Recent events will say which.
- Bug found and fixed: a tool that moves the rung (request_escalation, loop hit) runs before the step that issued it finishes its bookkeeping, so that step was credited to the new rung and the cooldown was one step short (3 Opus steps, not 4). Steps now count only against the rung they ran on.

## Unproven, to settle by running it (in priority order)

1. ~~Mid-turn model switch validity~~ settled, see Live finding 2.
2. **Cache cost of a switch.** Measured once on a ~200K context (Live finding 2). Still to do: the same on a small context, and switch vs. consult side by side, to set the oracle default.
3. **Self-reported confidence is weakly calibrated.** Treat the heuristic signals (loops, errors, stalls) as primary and the model's number as a hint. Needs a small eval set to tune `confidenceThreshold`.
4. ~~Effort support varies by model~~ **settled (2026-10-06): `claude-haiku-4-5` gets no effort at all; `claude-sonnet-5-5` does.** Read from the session transcripts, where each assistant message carries `perTurnEffort`: the haiku-low and haiku-high runs show `None` on every message, the sonnet-low and sonnet-high runs show `low` and `high`. A haiku-low rung and a haiku-high rung are therefore the same request, and escalating between them changes nothing while spending one of the task's escalations. Four runs of one data-analysis prompt (one sample each, so only suggestive on quality):

   | Rung | Output tok | Steps / tool calls | Time | Regional totals right (of 5) |
   |---|---|---|---|---|
   | haiku-low | 1,425 | 1 / 0 | 13s | 0 |
   | haiku-high | 1,457 | 1 / 0 | 14s | 3 |
   | sonnet-low | 2,222 | 1 / 0 | 16s | 5 |
   | sonnet-high | 2,331 | 3 / 2 | 22s | 5 (one rounding slip, West +46% for 45%) |

   The haiku-low/haiku-high difference in accuracy is sampling noise, since the requests are identical. Sonnet-high behaved differently from sonnet-low (it ran two shell commands to compute the figures), which is consistent with effort being honoured, but output tokens rose only 5%. Cache-read figures are not comparable across these runs: they track prefix size and cache warmth, not effort.
5. **Review quality.** The reviewer sees a clipped tool trail, not file diffs. Check it actually catches "claimed tests passed but none ran".
6. **Milestones depend on the model calling `checkpoint`.** `TodoWrite`/task tools are not in this build's typings, so there is no automatic todo-completion trigger yet.

## Known gaps / next steps

- Subagents are not managed (loops in a subagent only get a warning). Extension: an `agent.spawn` hook that sets the subagent's model from the ladder.
- Escalation notes ride on the next main-loop tool result; a final-answer step has no tool result to carry one.
- No cost ceiling in dollars yet, only token counts per tier.
- Scripted scenarios for the live test: (a) repeat a failing command to trigger the loop path; (b) a hard-reasoning prompt to trigger `request_escalation`; (c) a task whose claimed result is wrong, for the review-fail path; (d) a loop at oracle, for the breaker.
- Not exercised: how the pane looks and scrolls in a real terminal.
