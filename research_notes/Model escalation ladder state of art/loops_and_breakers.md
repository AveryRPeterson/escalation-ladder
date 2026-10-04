# Loop / stuck detection, circuit breakers and budget guards for autonomous LLM agents

Research date: 2026-10-03. Scope note: roughly 20 tool calls; source files were read directly from GitHub raw `main` where possible (so thresholds reflect current main, not a pinned release). Items marked UNVERIFIED rest on search snippets or memory-free inference only.

## 1. Exact heuristics and thresholds in existing systems (OpenHands, SWE-agent, Cline/Roo, Claude Code, Codex, Aider, LangGraph, AutoGen, CrewAI, Devin)

### Takeaway
Everyone ships cheap, deterministic, syntactic detectors (identical call / identical call+result / A-B alternation / same error) with small integer thresholds (3-6), plus hard step/cost caps as the real backstop. OpenHands' SDK detector is the most complete and the only one found that also nudges before stopping. No mainstream framework detects semantic loops with varied arguments.

### Cited Findings

**OpenHands (software-agent-sdk, current main)**
- Five patterns, defaults in `StuckDetectionThresholds`: `action_observation=4`, `action_error=3`, `monologue=3`, `alternating_pattern=6`. — [types.py](https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/types.py); documented in [Stuck Detector docs](https://docs.openhands.dev/sdk/guides/agent-stuck-detector)
- Pattern 1: last N actions all equal AND last N observations all equal (N=4). Pattern 2: same action erroring; stuck declared when the trailing streak is greater than 3 (i.e. needs 4), because 3 triggers a nudge first. Pattern 3: 3 consecutive agent-sourced MessageEvents with no user message and no non-message event between. Pattern 4: actions at even indices equal and observations at even indices equal across the last 6 events (A,B,A,B,A,B). Pattern 5 (context-window error loop, needs >=10 events) is a stub that unconditionally returns False ("TODO: blocked"). — [stuck_detector.py](https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/stuck_detector.py)
- Equality is semantic via `_event_eq()`: ActionEvent compares source, thought, action, tool_name; Observation compares source, observation, tool_name; ids and timestamps ignored. Note: `thought` is part of the comparison, so rewording the reasoning defeats the detector (supports your "signature sensitivity to rewording" weak spot). — same file
- Window: all checks run only on events since the last user message, capped at `MAX_EVENTS_TO_SCAN_FOR_STUCK_DETECTION = 20`. So a new user prompt implicitly resets all detector state (same property as your breaker-reset weak spot, but there it is by design). — same file
- Response: for action-error the conversation injects a one-time "nudge" user-role message when the streak first reaches 3 ("You've called X with the same arguments 3 times in a row and gotten the same error... Repeating the exact same call again will not work"), de-duplicated by `_last_nudged_error_event_id`; only if the loop continues does `is_stuck()` set `execution_status = STUCK` and stop the run loop. Other patterns go straight to STUCK. — [local_conversation.py `_check_stuck_or_nudge`](https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py)
- Enabled by default (`stuck_detection=True`). Legacy `openhands/controller/stuck.py` on the old repo path now 404s (moved/removed); I could not verify the legacy "condensation / LoopRecovery" UI behaviour (UNVERIFIED).

**SWE-agent / mini-swe-agent**
- SWE-agent `max_requeries: int = 3` for format/blocked-action errors; exit statuses include `exit_format`, `exit_cost`, `exit_context`, `exit_total_execution_time`, `exit_command_timeout`, `exit_api`, `exit_environment_error`. Model config has `per_instance_cost_limit`, `total_cost_limit`, `per_instance_call_limit`; default 0.0 / 0 in the file I read means disabled at model-config level (the default.yaml-level values were not shown to me). — [agents.py](https://github.com/SWE-agent/SWE-agent/blob/main/sweagent/agent/agents.py), [models.py](https://github.com/SWE-agent/SWE-agent/blob/main/sweagent/agent/models.py)
- mini-swe-agent: `step_limit: 0` (unlimited) and `cost_limit: 3.` (USD) in `mini.yaml`; `default.yaml` has both 0. No repeat detection found in the config. — [mini.yaml](https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/config/mini.yaml), [default.yaml](https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/config/default.yaml)

**Roo Code**
- `ToolRepetitionDetector(limit = 3)`: serialises the tool call with `safe-stable-stringify` (canonical JSON, so key order does not matter), counts consecutive identical calls (counter resets to 0 on any different call), limit 0 = unlimited. On reaching the limit it returns `allowExecution:false` with an ask-user "mistake_limit_reached" message, and **resets its own counters** ("to allow recovery if user guides the AI past this point"). It compares calls only, never results, so legitimate polling/re-running tests trips it. Roo constructs it with `consecutiveMistakeLimit` (default constant `DEFAULT_CONSECUTIVE_MISTAKE_LIMIT`, value not read). — [ToolRepetitionDetector.ts](https://github.com/RooCodeInc/Roo-Code/blob/main/src/core/tools/ToolRepetitionDetector.ts), [Task.ts](https://github.com/RooCodeInc/Roo-Code/blob/main/src/core/task/Task.ts); off-by-one bug fix in [PR 6836](https://github.com/RooCodeInc/Roo-Code/pull/6836)
- Roo "allowedMaxRequests" auto-approve cap ported from Cline: [PR 3631](https://github.com/RooCodeInc/Roo-Code/pull/3631)

**Cline**
- A search-result snippet describes a two-stage design in Cline: 3 identical calls inject a warning message, 5 identical calls escalate through `consecutiveMistakeCount` (state `lastToolParams`, `consecutiveIdenticalToolCount` in TaskState, logic in ToolExecutor `handleCompleteBlock`). I could not open the PR/source to confirm it merged or the exact numbers. UNVERIFIED. (The search tool returned this under a Cline query, but the link list did not include the Cline PR.)
- CLI: consecutive-mistake cap default 3, flag `--retries` (npm package description). — [npm cline](https://www.npmjs.com/package/cline)
- Auto-approve "max requests" setting existed in v3 ([announcement](https://x.com/sdrzn/status/1869470308442452478)); a v3.35 blog says it was removed ([Cline v3.35](https://cline.bot/blog/cline-v3-35)). Reported lockout bug when the limit is hit with no recovery path: [issue 3480](https://github.com/cline/cline/issues/3480). Useful anti-pattern: hard cap with no human "continue" affordance.

**Claude Code**
- `--max-turns` (print mode only; "Exits with an error when the limit is reached. No limit by default") and `--max-budget-usd` (print mode only; subagent spend counts; once reached, spawning a subagent fails with `Budget limit reached` and background subagents are stopped; restored totals from `--continue/--resume` do NOT count against the cap). — [CLI reference](https://code.claude.com/docs/en/cli-reference)
- Agent SDK: `maxBudgetUsd` counts only the call's own spend, a `/clear` restarts the budget; result subtype `error_max_budget_usd` omits the final crossing response from `usage` but includes it in `total_cost_usd`; `total_cost_usd` is a client-side estimate "Do not ... trigger financial decisions from these fields". Totals persist to transcript on normal exit and are restored on resume; a crash can yield zeroed totals. — [Cost tracking](https://code.claude.com/docs/en/agent-sdk/cost-tracking). Direct implication: budget state lives in the transcript and is not authoritative; budget resets on `/clear` by design.
- I did not find a built-in same-call loop detector in Claude Code docs; I did not open the hooks reference for Stop-hook re-entry guards (`stop_hook_active`) in this pass. UNVERIFIED / gap.

**Codex CLI**
- No built-in repeated-call breaker found. User issues document runaway behaviour: same `gh issue view` run 78 times / 6.2M tokens (the reporter notes a breaker exists only for the Claude adapter in their orchestrator and proposes a shared layer tripping on "N identical successful calls") — [hive-mind #2316](https://github.com/link-assistant/hive-mind/issues/2316); repeated resubmission of the same tool result — [openai/codex #27757](https://github.com/openai/codex/issues/27757); wait/status polling re-entering the model for hours — [openai/codex #35259](https://github.com/openai/codex/issues/35259); repeated context-compaction loops — [openai/codex #37090](https://github.com/openai/codex/issues/37090); repetitive loop in GPT-5.5 inside Xcode — [openai/codex #49053](https://github.com/openai/codex/issues/49053). These are user reports, not measured rates.

**Aider**
- `max_reflections = 3`; on the 4th would-be reflection prints "Only 3 reflections allowed, stopping."; counter reset per user message (`num_reflections = 0`). Reflection = auto-feeding lint/test/edit-error output back to the model. — [base_coder.py](https://github.com/Aider-AI/aider/blob/main/aider/coders/base_coder.py)

**LangGraph**
- `recursion_limit` is a per-invocation config; loop sets `stop = step + recursion_limit + 1`; raises `GraphRecursionError` (error code GRAPH_RECURSION_LIMIT) "This prevents infinite loops". Counts supersteps, not tool calls. Config validated `>= 1`. Official remedy text: raise the limit or fix the cycle. — [errors.py](https://github.com/langchain-ai/langgraph/blob/main/libs/langgraph/langgraph/errors.py), [_loop.py](https://github.com/langchain-ai/langgraph/blob/main/libs/langgraph/langgraph/pregel/_loop.py), [troubleshooting](https://docs.langchain.com/oss/python/langgraph/GRAPH_RECURSION_LIMIT). The numeric default constant could not be read (my grep failed); I believe it is 25 historically, newer versions may differ. UNVERIFIED.

**AutoGen (AgentChat)**
- Composable termination conditions: `MaxMessageTermination(max_messages)`, `TokenUsageTermination`, `TimeoutTermination(timeout_seconds)`, `TextMentionTermination`, `HandoffTermination`, `ExternalTermination`, `FunctionalTermination`, combinable with `|` / `&`. Hard caps only; no repeat detection. — [_terminations.py](https://github.com/microsoft/autogen/blob/main/python/packages/autogen-agentchat/src/autogen_agentchat/conditions/_terminations.py). (AutoGen is in maintenance mode in favour of Microsoft Agent Framework - from memory, UNVERIFIED.)

**CrewAI**
- `max_iter` default **25**; `max_execution_time` default None; `max_retry_limit` (retry on error) ; `max_rpm`. On hitting `max_iter`, `handle_max_iterations_exceeded` makes **one more LLM call with a forced-final-answer instruction appended** (graceful wrap-up, not a hard abort). — [base_agent.py](https://github.com/crewAIInc/crewAI/blob/main/lib/crewai/src/crewai/agents/agent_builder/base_agent.py), [agent_utils.py](https://github.com/crewAIInc/crewAI/blob/main/lib/crewai/src/crewai/utilities/agent_utils.py), [agent/core.py](https://github.com/crewAIInc/crewAI/blob/main/lib/crewai/src/crewai/agent/core.py)

**Devin**
- Not researched; no primary source consulted. Gap.

**Other open-source guards seen (secondary, unvetted)**: opencode "doom loop detection" PR ([anomalyco/opencode #3445](https://github.com/anomalyco/opencode/pull/3445)); Hermes tool-loop guardrail with `hard_stop_enabled` defaulting False, one report of ~500 identical calls ([hermes-agent #112535](https://github.com/NousResearch/hermes-agent/issues/112535)); openclaw loop detection disabled by default, agent looped ~50 times across context overflow plus auto-compaction ([openclaw #77474](https://github.com/openclaw/openclaw/issues/77474)); a loop guard that warns once then never re-detects ([oh-my-pi #12564](https://github.com/can1357/oh-my-pi/issues/12564)); detection that fires on 2nd identical call and never compares results ([finch #440](https://github.com/darwin-finch/finch/issues/440)); warnings masking hard stops in multi-tool batches ([deer-flow #5243](https://github.com/bytedance/deer-flow/issues/5243)); loop guards that ignore calls rejected by argument validation ([openclaw PR 158709](https://github.com/openclaw/openclaw/pull/158709)). These are bug reports that map onto your listed weak spots.

### Inferences
- Defaults converge: identical-call limit 3-4, same-error 3, ping-pong 6 events (3 cycles), agent-initiated message-only turns 3. Your "three strikes" matches the field.
- Only OpenHands compares results (action AND observation), which is what separates legitimate polling (changing observation) from a loop; Roo compares calls only and therefore false-positives. Result-aware matching is the main published false-positive fix.
- Bug-report pattern across tools: "warn once then never re-detect", "warning masks hard stop", "detection disabled by default", "counter resets on breaker trip". These are failure modes to test your own breaker against.

### Gaps
- Devin, Codex CLI internals, Claude Code hook-level protections, LangGraph numeric default, Cline source confirmation of 3/5 thresholds, Roo's numeric `DEFAULT_CONSECUTIVE_MISTAKE_LIMIT`.

## 2. Published failure taxonomies and how common loops/repetition are; stall modes a repeat/ping-pong/same-error detector misses

### Takeaway
Repetition is a real but minority failure mode in multi-agent traces (MAST: step repetition 15.7%), strongly model-dependent in coding agents (a 32B open model had >25% trajectories with a >=10-length repeat; Claude 3.7 Sonnet <4%), and strictly syntactic detectors miss the most common coding-agent stalls: long read-only exploration, re-reading, edit/revert oscillation.

### Cited Findings
- MAST: 14 failure modes in 3 categories over 1,642 annotated traces (LLM-annotated, public data `mcemri/MAST-Data`); reported system-design issues 44.2%, inter-agent misalignment 32.3%, task verification 23.5%; within system design: step repetition (FM-1.3) 15.7%, disobey task spec 11.8%, loss of conversation history 2.8%, disobey role spec 1.5%. Overall MAS failure rates 41%-86.7% across studied frameworks. — [paper](https://arxiv.org/pdf/2503.13657), [NeurIPS 2025 version](https://proceedings.neurips.cc/paper_files/paper/2025/file/b1041e52d3be19f0a9bc491657488e4a-Paper-Datasets_and_Benchmarks_Track.pdf). The percentages come via a search-engine summary of the paper, and my direct fetch of the PDF gave only the category list; numbers should be re-checked against the PDF before quoting. FM-1.5 (unaware of termination conditions) is also in the taxonomy.
- TraceProbe (2,500 SWE-bench Verified trajectories) defines structural anti-patterns: **Search Loop** = at least 10 consecutive SEARCH/FILE_READ actions with no FILE_WRITE and no validation command (56.1% of failed vs 41.1% of resolved runs; 67.6% on hard tasks vs 34.2% on easy), **Re-read Churn** (44.7% failed vs 34.0% resolved), **Tool Oscillation** (read-write-read on one file where the write fails or is reverted), **Redundant Search** (identical query within a 10-action window), **Phase Oscillation** (switching between two phases within 6 actions). Authors note prevalence tracks difficulty, i.e. weak failure discrimination. — [What Resolve Rate Hides](https://arxiv.org/html/2607.06184v1)
- Failed trajectories are longer: OpenHands Lite 79.90 vs 61.01 steps (31% longer), Prometheus 136.47 vs 87.16 (56.6%), SWE-agent about 12.6%; failures show wider variance ("two kinds of failures"); 72-81% of failed patches touched the right files; authors recommend early stopping and stronger abandon-path signals. — [Understanding Code Agent Behaviour](https://arxiv.org/html/2511.00197v1)
- Per a search summary of SWE-smith: SWE-agent-LM-32B had >25% of trajectories containing a repetitive sequence of length >=10 versus <4% for Claude 3.7 Sonnet, and length-10 repeats corresponded to 89% failure probability. — [SWE-smith](https://arxiv.org/pdf/2504.21798). My fetch of the PDF could not extract that passage; UNVERIFIED against the source text.
- Failure taxonomies elsewhere list "Stuck in Loop" and "Gave Up Prematurely" as categories; for GPT-5 family, >60% of failures are instruction following, older models show more looping/early termination (search summary, original not opened; see [Inside the Scaffold](https://arxiv.org/html/2604.03515v1), [Coherence Collapse](https://arxiv.org/abs/2603.24631)). UNVERIFIED.
- Production signal: polling loops, empty/invalid tool-arg loops, resubmitted stale tool results and compaction loops appear in Codex issues (links in section 1).

### Inferences
- Stall modes a repeat / A-B ping-pong / same-error detector will miss: (1) semantic loops with varied arguments (different grep patterns, different file paths); (2) progress-less exploration (search loop, 10+ read-only calls); (3) edit-undo oscillation where each edit differs textually; (4) test-fix thrash where each cycle has a different error message; (5) context-window/compaction thrash where state is lost and the agent redoes work; (6) polling-style loops that are legitimate individually; (7) long-period cycles (A-B-C-D) beyond the period-2 check; (8) monologue/no-tool turns.
- Because loop-like patterns also occur in 41% of resolved runs (search loop), any progress-based detector must be tuned as an escalation signal rather than a kill switch.

### Gaps
- No peer-reviewed measurement of precision/recall for OpenHands-style heuristics found; no taxonomy that quantifies "edit-undo" or "test-fix thrash" separately beyond TraceProbe's patterns.

## 3. Better detectors: progress metrics, semantic similarity, LLM-judge; reported precision/recall and cost

### Takeaway
I found definitions and cheap structural heuristics (TraceProbe) but no rigorous published precision/recall for embedding-based or LLM-judge stuck detection in coding agents. Vendor/blog material describes three tiers: hash match (O(1)), embedding cosine, and frequency analysis, without validated numbers.

### Cited Findings
- A catalogue-style source lists string-match detection (call hashing, O(1)), semantic similarity (cosine distance of embeddings catches near-identical loops), and frequency analysis (behavioural loops regardless of content). — [supra-wall](https://www.supra-wall.com/learn/ai-agent-infinite-loop-detection) (vendor page, low reliability, no measured accuracy)
- `ai-loopguard` / `AgentCircuit` are small OSS projects advertising loop detection with escalation to a stronger model: [AgentCircuit](https://github.com/simranmultani197/AgentCircuit). No benchmarks seen.
- TraceProbe detectors are window-based on action types (10 consecutive read-only actions; 10-action window for redundant search; 6-action window for phase oscillation); discriminative power modest (56.1% vs 41.1% prevalence). — [arXiv 2607.06184](https://arxiv.org/html/2607.06184v1)
- Trajectory-length early-stopping is recommended by the OpenHands/SWE-agent/Prometheus study because failed runs run 12-57% longer. — [arXiv 2511.00197](https://arxiv.org/html/2511.00197v1)

### Inferences
- Practical stack that the evidence supports: (a) result-aware exact/normalised-signature match as the hard trigger; (b) cheap progress counters (file-diff hash unchanged, tests-pass count not improved, novelty of observation hash/new file paths touched) as soft triggers over windows of ~10 actions; (c) optional embedding or LLM-judge only as a tie-breaker invoked rarely, since no accuracy data justifies auto-abort on it.
- Normalisation fixes for rewording sensitivity should exclude free-text `thought`/description fields from the signature (OpenHands includes `thought`; Roo canonicalises JSON keys), hash only tool name + normalised args (paths resolved, whitespace/number noise stripped) and compare observation hashes after stripping timestamps/durations/PIDs.

### Gaps
- No peer-reviewed false-positive rates for any detector; no cost numbers for LLM-judge stuck detection; I did not find arXiv papers specifically evaluating embedding-based loop detectors for coding agents.

## 4. Recommended response when stuck: nudge, reflect, escalate, restart, hand off

### Takeaway
Evidence for which response works is thin. Implementations show a graduated pattern: nudge (OpenHands, Cline per snippet), then stop and ask the human (Roo, Cline, OpenHands STUCK status). Model escalation on stuck is advertised by OSS tools but not benchmarked.

### Cited Findings
- OpenHands: one-time nudge at 3 repeated errors, then STUCK stop at the next repeat; nudge de-duplicated per error event. — [local_conversation.py](https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py)
- Roo: on trip, ask the user, then reset counters so a user-guided continuation can proceed. — [ToolRepetitionDetector.ts](https://github.com/RooCodeInc/Roo-Code/blob/main/src/core/tools/ToolRepetitionDetector.ts)
- Aider: auto-reflection bounded at 3, then stop. — [base_coder.py](https://github.com/Aider-AI/aider/blob/main/aider/coders/base_coder.py)
- CrewAI: at iteration cap force one final-answer call. — [agent_utils.py](https://github.com/crewAIInc/crewAI/blob/main/lib/crewai/src/crewai/utilities/agent_utils.py)
- Study recommendation: stronger signals for abandoning unproductive exploration; early stopping. — [arXiv 2511.00197](https://arxiv.org/html/2511.00197v1)

### Inferences
- A defensible ladder: soft nudge (state the repeated action and the fact the result was identical, ask for a different approach) -> forced reflection/plan turn or context compaction -> model escalation -> stop with a handoff summary. Order and effectiveness are unproven by measurement; treat as design hypothesis.
- OpenHands' "nudge once per streak" plus "stop on continuation" is the one concretely implemented 2-tier pattern.

### Gaps
- No controlled study comparing nudge vs reflection vs restart vs escalation. Reflexion-style results were not retrieved. No evidence on restart-with-fresh-context efficacy for coding agents found.

## 5. Budget guards: token/cost/time/step caps, scope, soft vs hard, wrap-up, persistence

### Takeaway
Frameworks mostly offer hard per-run caps (steps, turns, USD, wall-clock), scoped to a single invocation, with resumption semantics varying. Graceful wrap-up exists in CrewAI (forced final answer). Claude Code explicitly excludes restored spend from `--max-budget-usd` and restarts budget on `/clear`.

### Cited Findings
- Claude Code CLI/SDK: see section 1 (`--max-turns`, `--max-budget-usd`, `error_max_budget_usd`, subagent spend counted, cap enforced on subagent spawn). — [CLI reference](https://code.claude.com/docs/en/cli-reference), [cost tracking](https://code.claude.com/docs/en/agent-sdk/cost-tracking)
- SWE-agent: per-instance cost and call limits, total cost limit, `exit_cost`, `exit_total_execution_time`. mini-swe-agent: `cost_limit: 3.` in `mini.yaml`. (links in section 1)
- AutoGen: `TokenUsageTermination`, `TimeoutTermination`, `MaxMessageTermination` composable. CrewAI: `max_iter=25`, `max_execution_time`, `max_rpm`, `max_retry_limit`. LangGraph: `recursion_limit` per invoke. (links in section 1)
- Cline's max-requests setting caused lockout with no way to continue ([issue 3480](https://github.com/cline/cline/issues/3480)) and was later removed ([v3.35 blog](https://cline.bot/blog/cline-v3-35)).
- Practitioner posts about runaway cost ("agent ran 6 hours on a 2-minute task and cost $200") advocate circuit breakers: [DEV post](https://dev.to/debashish_ghosal/preventing-the-agent-death-spiral-why-your-ai-agents-need-a-circuit-breaker-9h7), [DEV post 2](https://dev.to/gabrielanhaia/tool-calling-loops-the-bug-that-burns-4000-overnight-and-the-7-line-fix-pp1) (anecdotal).

### Inferences
- State persistence: the only vendor doc describing persistence (Claude Agent SDK) persists totals in the session transcript and restores on resume but deliberately does not apply the cap to restored totals. For a plugin: persist breaker/budget state keyed by session id in a file outside the hot-reloadable module (so reload and prompt boundary do not reset it), store counters and trip timestamp, and define explicitly which events clear it (user prompt = half-open probe, not full reset).
- Costs are client estimates, so enforce budget on tokens/steps as primary, USD as advisory (consistent with Anthropic's warning).

### Gaps
- No source on token-based soft thresholds (e.g. warn at 80%) in frameworks was found; wall-clock budgets per task vs per session scoping not documented comparably across tools.

## 6. Circuit breaker pattern (closed / open / half-open) in agent frameworks and safety literature

### Takeaway
The pattern is being borrowed by blog posts and small libraries; the mainstream frameworks surveyed implement only the "open" state (stop and ask) with counters reset manually, not half-open probing. Half-open is acknowledged as hard to translate for stochastic agents.

### Cited Findings
- Translation of closed/open/half-open to agents; half-open is "the hardest translation": one successful agent run doesn't confirm reasoning quality has recovered because quality is stochastic. — [Hannecke, Resilience Circuit Breakers for Agentic AI](https://medium.com/@michael.hannecke/resilience-circuit-breakers-for-agentic-ai-cc7075101486) (seen only via search snippet; page returned 403)
- Real implementation bugs in half-open handling: breaker stuck forever after trial call ended with an ignored error ([vernLLM PR 169](https://github.com/LakBud/vernLLM/pull/169)); breaker ending the parent agent turn instead of waiting for its half-open probe ([harn #9273](https://github.com/burin-labs/harn/issues/9273)).
- Roo's detector resets counters at trip, effectively an immediate "half-open/closed" with the human as the probe. OpenHands' STUCK is terminal for that run; the detector re-evaluates only on events since the last user message (see section 1).
- The circuit-breaker pattern for AI agents write-up: [Brenn Hill, DEV](https://dev.to/brennhill/the-circuit-breaker-pattern-for-ai-agents-11pl) (blog, not opened in full).

### Inferences
- A workable agent-level half-open: after a trip, permit a limited probe (one or two tool calls, or a nudged retry) and judge by a progress signal (observation changes, diff changes, test count improves) rather than just "call succeeded"; re-trip faster (lower threshold) on probe failure. Guard against the stuck-half-open bug class by giving the probe a timeout/budget.
- Classical sources (Nygard "Release It!", Fowler CircuitBreaker bliki) were not fetched in this pass; they define the standard states and failure-threshold/timeout semantics.

### Gaps
- No peer-reviewed safety/control literature on runaway-agent breakers retrieved; no framework evidence of half-open probing for agent loops; classic references not opened.
