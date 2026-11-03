# escalation-ladder

A Claude Code plugin that runs a task on a cheap model by default and moves it up a ladder of
stronger models only when it needs to, with guards against the usual auto-escalation failure modes:
loops, runaway cost, and an unreviewed wrong "done".

**Status: proof of concept (v0.1.0).** It validates, type-checks and passes its unit tests. The
first evaluation run did not show a benefit over a fixed model (see below), so treat it as an
experiment, not a finished tool.

## What it does

- **Tiered ladder** (cheapest to strongest, last tier is the oracle) with presets: `frugal`,
  `balanced`, `cautious`, plus `efforttest` for measurement only.
- **Escalates** when the model asks (`request_escalation`), a loop is detected, consecutive tool errors
  pile up, a rung stalls, output is truncated or refused, or a review fails. Steps back down after a
  cooldown so the cheap tier's savings are not lost.
- **Two oracle modes:** *switch* (the main loop continues on the oracle) and *consult*
  (`consult_oracle` returns one answer while the cheap model keeps driving).
- **Protections:** a loop detector (identical call and result, A/B alternation, repeated error), a
  circuit breaker that aborts a runaway turn, and per-task budgets for escalations and steps.
- **Independent review:** a reviewer tier with no shared history checks the task, tool trail and
  final answer, and can send issues back as a fix-up turn.
- **Pane and commands:** `/ladder` opens a status pane; subcommands `on|off|up|down|pin|unpin|reset|preset <name>`.

The design and the open questions are in [PLAN.md](PLAN.md); review notes are in
[REVIEW_ROUND_1.md](REVIEW_ROUND_1.md) and [EDGE_CASES.md](EDGE_CASES.md).

## Evaluation

`eval/` compares four arms (fixed sonnet-low with advisor, fixed haiku with advisor, fixed opus-high,
and sonnet-low plus the ladder) on six tasks with hidden unit tests. In run 1 every arm passed every
test, so quality did not separate them. Cost did: fixed opus-high cost about 2.3x sonnet-low. The
ladder matched the cheap arm on cost, but no task needed escalation, so run 1 neither supports nor
retires it. Details are in [eval/RESULTS.md](eval/RESULTS.md).

```
python eval/harness.py validate
python eval/harness.py run --arms A,B,C,D --tasks all --reps 1
```

The harness uses this repository as the plugin directory. Set `LADDER_PLUGIN_DIR` to point it elsewhere.

## Develop

```
npm install
npm test          # vitest
npm run validate  # tsc --noEmit
```

A copy of the plugin is also published through the
[claude-plugins](https://github.com/AveryRPeterson/claude-plugins) marketplace.
