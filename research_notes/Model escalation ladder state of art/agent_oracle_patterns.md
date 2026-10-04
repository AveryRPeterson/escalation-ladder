# Tiered / planner-executor / "oracle" model use in shipped and open-source coding agents (as of Oct 2026)

Research scope note: ~25 tool calls. Primary sources (vendor docs) were fetched directly via a summarising fetch tool, so wording is paraphrase of the fetched pages, not verbatim. Model names/versions (Fable 5.1, Opus 5.5, GPT-5.6, etc.) are as they appear in the fetched 2026 docs; I did not independently verify them. Not covered / thin: Devin, Windsurf, LangGraph/AutoGen/CrewAI, Claude Agent SDK subagents (see Gaps).

## 1. Which products use multiple models in one session, and how?

### Takeaway
Three distinct mechanisms ship: (a) tool-call "consult" (Anthropic advisor tool / Claude Code `/advisor`, Amp oracle) where the cheap model keeps driving; (b) phase-boundary switching (Claude Code `opusplan`, Cline/Roo plan vs act models, Aider architect/editor); (c) per-request routers (Cursor Router, Gemini CLI classifier). The closest shipped match to the escalation-ladder "consult_oracle" is Anthropic's own advisor tool, which is first-party documented with numbers.

### Cited Findings

**Anthropic advisor tool / Claude Code `/advisor` (closest analogue to consult_oracle)**
- Server-side tool; a faster executor model calls a stronger advisor model mid-generation; advisor reads the full transcript, returns a plan/correction, executor continues, all inside one `/v1/messages` request. Executor emits `server_tool_use` name "advisor" with empty input: "executor signals timing, server supplies context". — [API docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool)
- Advisor gets the executor's full transcript (system prompt, tool defs, prior turns, tool results, text so far) as quoted context under its own Anthropic-supplied system prompt; runs with no tools and no context management; its thinking is dropped, only advice text returns. — [API docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool)
- Who decides: the executor model ("Claude decides when to call it"); timing is "model-driven rather than rule-based"; there is no setting to cap or force calls in Claude Code, only prompt instructions. API has `max_uses` (per-request cap, not per-conversation). — [Claude Code advisor docs](https://code.claude.com/docs/en/advisor), [API docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool)
- Pairing rules: advisor must rank at/above main model (e.g. Haiku 4.5 / Sonnet 4.6 main -> Fable, Opus, or Sonnet advisor; Haiku can call but cannot be an advisor). Anthropic API only (not Bedrock/Vertex/Foundry). Experimental, beta header `advisor-tool-2026-03-01`, type `advisor_20260301`. Subagents inherit the configured advisor. — [Claude Code advisor docs](https://code.claude.com/docs/en/advisor)
- Claude generally follows the advice but "adapts when its own evidence contradicts a specific claim" and surfaces the conflict; suggested prompt says to do a reconcile advisor call rather than silently switching. — [Claude Code advisor docs](https://code.claude.com/docs/en/advisor), [API docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool)
- Typical advisor output 400-700 text tokens (1,400-1,800 incl. thinking) on light workloads; tool-level `max_tokens` (min 1024) caps it; at 2048 on a hard reasoning benchmark mean advisor output fell ~7x with near-zero truncation, at 1024 ~10% of calls truncated (n=40 per config, differences within noise). — [API docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool)
- Launch blog numbers: Sonnet + Opus advisor on SWE-bench Multilingual +2.7 pts and -11.9% cost/task vs Sonnet alone; Haiku + Opus advisor on BrowseComp 41.2% vs 19.7% solo, ~85% cheaper per task than Sonnet solo (but trailing Sonnet solo by 29%). — [Anthropic blog](https://claude.com/blog/the-advisor-strategy) (a secondary source gives the launch date as 9 Apr 2026: [buildfastwithai](https://www.buildfastwithai.com/blogs/anthropic-advisor-strategy-claude-api), unverified)
- Anthropic's own "Optimizing for cost and intelligence" page (fetched summary): benefit shrinks as executor approaches advisor capability. Opus 5.5 executor + Fable 5.1 advisor on an internal agentic coding benchmark: 90.1% at $2.92/attempt vs Opus 5.5 alone at high 88.4% at $1.38 (+1.7 pts, "edge of noise", ~2.1x cost); on a "chartography" benchmark the pairing consulted in 1 of 300 tasks and scored 7 pts below Opus 5.5 alone at about the same cost; DeepSWE: low-effort Sonnet 5 kept consulting and gained 23 pts, but on SWE-bench Pro the same executor stopped consulting and lost the benefit. Advice: price the stronger model alone at low effort first as the baseline to beat; measure consult rate; if the executor consults on most tasks just run the advisor model itself. — [Optimizing for cost and intelligence](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence) (fetched via summariser; numbers should be re-checked against the page before quoting)

**Claude Code other multi-model features**
- `opusplan`: Opus in plan mode, Sonnet in execution; each plan-mode toggle is a model switch. — [Model config](https://code.claude.com/docs/en/model-config)
- Subagents inherit the main model by default; per-subagent `model` field; `CLAUDE_CODE_SUBAGENT_MODEL` env sets default for subagents/teammates/workflow agents. — [Model config](https://code.claude.com/docs/en/model-config)
- Automatic model fallback (Fable/Opus 5.5/Sonnet 5.5/Opus 5): when a safety classifier flags a request, Claude Code re-runs it on a fallback model and the session continues there (a forced "switch"). — [Model config](https://code.claude.com/docs/en/model-config)
- Docs' own comparison table: advisor = "at decision points mid-task, Claude calls it"; opusplan = plan mode only; subagent with `model` = whole delegated subtask; `/model` = from next request onward. — [Advisor docs](https://code.claude.com/docs/en/advisor)
- Skills/commands whose frontmatter names a different `model` make that turn a model switch (cache miss). — [Prompt caching in Claude Code](https://code.claude.com/docs/en/prompt-caching)

**Amp (Sourcegraph)**
- Each mode (low/medium/high/ultra) fixes main agent model, reasoning effort, system prompt, tools and an oracle; three roles: main agent, oracle ("second opinion"), subagents (search, review, media). Users may pin per-role models. — [Amp Dial docs](https://ampcode.com/docs/the-dial)
- Mode is fixed at thread start; docs say changing mid-thread "confuses models and invalidates prompt caching". Cost advice: starting too low means multiple attempts, too high wastes credits. — [Amp Dial docs](https://ampcode.com/docs/the-dial)
- Oracle is an optional tool the main agent may call autonomously; Amp "intentionally does not force" it because of cost and slower inference; recommended for debugging across files, architecture, review; not for simple edits/searches. In high mode (per a secondary summary) main = GPT-6 Astra medium, oracle = Claude Fable 5.1 high. — secondary summary of [Amp oracle docs](https://ampcode.com/news/oracle) (direct fetch failed; relayed via search snippet, medium confidence)
- Oracle tool params (from a community-captured system prompt dated 2025-10-25, not official): `task` (required), `context` (optional: background, previous attempts), `files` (optional paths); oracle itself has Read/Grep/glob/web_search/read_web_page. So the consulted model gets a curated brief plus file access, not the full transcript. — [community gist](https://gist.github.com/gregce/9ae20efc085d45b36f1ce7a6a2b48845)
- Original oracle was GPT-5 high reasoning while main agent was Claude. — [Amp GPT-5 post](https://ampcode.com/news/gpt-5) (via search snippet)

**Aider architect/editor (phase-boundary, two-call pipeline)**
- Architect describes the solution in free text, editor converts it to edits. o1-preview+o1-mini and o1-preview+DeepSeek: 85.0%; o1-preview+Sonnet: 82.7%; o1-preview solo 79.7%; Sonnet+Sonnet 80.5% vs 77.4% solo. Aider itself calls the o1+DeepSeek combo "quite slow, so probably not practical for interactive use". — [Aider blog](https://aider.chat/2024/09/26/architect.html) (2024; older generation of models)
- Aider also has a third "weak model" for summarisation/commit messages. — [Inside the Scaffold taxonomy](https://arxiv.org/pdf/2604.03515) (via search snippet; PDF not parsed)

**Cline / Roo / Kilo**
- Cline: setting "Use different models for Plan and Act"; switching modes switches models automatically. — [Cline docs](https://docs.cline.bot/core-workflows/plan-and-act). User-driven. Several bug reports show per-mode model settings leaking across modes with OpenAI-compatible providers (e.g. [#11357](https://github.com/cline/cline/issues/11357), [#8126](https://github.com/cline/cline/issues/8126)) - implementation fragility.
- Roo Code: per-mode model assignment and "sticky models" (each mode remembers its last model); Orchestrator/Boomerang mode delegates subtasks to modes and has no direct file/command tools. — [Roo Code on X](https://x.com/roo_code/status/1913388225844122032), [Roo docs](https://docs.roocode.com/features/custom-modes)

**Routers (per-request, user does not decide)**
- Cursor Router: with Auto + Balance/Intelligence, a classifier runs on each agent request and routes by task type/complexity; routes across GPT-5.5, Claude Opus 5, Grok 4.6, Claude Fable 5; docs say nothing on caching/mid-conversation switch costs. — [Cursor Router docs](https://cursor.com/docs/cursor-router). A secondary source claims the classifier was trained on 600k+ live requests - [therundown summary](https://www.therundown.ai/tools/cursor-router) (unverified, not on primary page I fetched).
- Gemini CLI: Flash-Lite classifier decides Flash vs Pro on complexity; experimental numerical-routing variant exists. — [Gemini CLI discussion #8649](https://github.com/google-gemini/gemini-cli/discussions/8649), [issue #17496](https://github.com/google-gemini/gemini-cli/issues/17496) (via search snippets)
- OpenHands SDK: pluggable `Router`; only built-in is `MultimodalRouter` (image present -> multimodal model, else secondary LLM); docs say under active development. — [OpenHands routing docs](https://docs.openhands.dev/sdk/guides/llm-routing)
- mini-SWE-agent: single model throughout (per source taxonomy summary). — [Inside the Scaffold](https://arxiv.org/pdf/2604.03515) (snippet only)
- Codex CLI: subagents can be given a different model/effort (gpt-5.4-mini recommended for exploration workers); a bug report says `spawn_agent` ignored a requested mini model. — [codex.danielvaughan.com guide](https://codex.danielvaughan.com/2026/03/26/codex-cli-model-selection/) (third-party blog), [openai/codex #16548](https://github.com/openai/codex/issues/16548)

### Inferences
- Anthropic's advisor tool is essentially an official implementation of "consult_oracle": model-initiated, empty-argument call, full transcript forwarded, advice-only return, executor keeps the loop. Its documented limits (under-calling, consult-rate sensitivity, shrinking benefit as gap closes) are directly applicable to our design.
- Amp's design differs in context passing: curated task/context/files brief plus oracle's own read tools versus Anthropic's full-transcript forwarding.
- Switch-style mechanisms in shipped products are almost all user/phase-driven (opusplan, Cline, Roo) or classifier-per-request (Cursor, Gemini CLI); a mid-turn heuristic escalation (our "switch on trouble signals") has no first-party shipped analogue found, except Claude Code's safety-fallback re-run.

### Gaps
- Devin, Windsurf (SWE-1.x/planning agent), Sourcegraph Cody beyond Amp, LangGraph/AutoGen/CrewAI supervisor patterns, Claude Agent SDK subagent model selection, Kilo-specific behaviour: not researched in depth in this pass; no sourced claims included.
- Amp oracle official page fetch failed (header overflow); Amp oracle details rely on search snippets and a community gist.
- "Inside the Scaffold" PDF (arXiv 2604.03515) was binary-only; a saved copy is in the tool-results dir but I did not extract its taxonomy table. It likely has a systematic cross-agent table of multi-model use worth reading directly.

## 2. Consult vs switch: what is used in practice, evidence, context passing

### Takeaway
Consult (stronger model advises, cheap model drives) is what both vendors that built an "oracle" ship (Anthropic advisor, Amp oracle) and has first-party cost/quality numbers; whole-loop switching exists as user-driven (`/model`, opusplan) or safety-fallback, and carries a cache-miss penalty. Empirically the consult advantage is large when the capability gap is large and near zero when it is small.

### Cited Findings
- Anthropic positions advisor for "long, multi-step tasks where most turns are routine but plan quality determines the outcome", and says for short tasks or work needing the strongest model every turn, switch the main model instead. — [Claude Code advisor docs](https://code.claude.com/docs/en/advisor)
- Context passed: full conversation including every tool call/result (Anthropic) — [advisor docs](https://code.claude.com/docs/en/advisor); versus task+context+files brief (Amp, community-sourced) — [gist](https://gist.github.com/gregce/9ae20efc085d45b36f1ce7a6a2b48845).
- Advisor's own read of the transcript is NOT cached by default in Claude Code ("each advisor call processes the full transcript anew"); the API offers opt-in `caching` on the advisor tool (5m or 1h) and says it breaks even at roughly 3 advisor calls per conversation; toggling it mid-conversation causes misses. — [Claude Code advisor docs](https://code.claude.com/docs/en/advisor), [API docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool)
- Two timings Anthropic found drive coding gains: an early call after a few exploratory reads, and (for hard tasks) a final call after writes/tests; recommended ~2-3 calls per task; advice to make deliverable durable (write/commit) before the final call because it takes time. — [API docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool)
- Research analogues: LivePlan (arXiv 2608.06701) uses a deterministic rule-based monitor on trajectory signals (drift, repetition, premature termination) and only then queries an LLM advisor for a next-step correction: up to +15.2% (avg +9.9%) resolve over SWE-agent baseline, ~$0.08 extra per instance, five LLMs, SWE-bench Verified/Pro. — [arXiv 2608.06701](https://arxiv.org/abs/2608.06701). A search snippet reports GPT-5.2 advisor + DeepSeek executor 38.2% -> 49.4% on SWE-bench Verified (same paper family; unverified in the fetched abstract).
- Forced delegation experiment (blog, single task, n=1 per variant): Opus solo 97/100 ~$4 in 18 min; Opus orchestrating cheaper workers cost up to 3x more (planner overhead ~$11 over 14 dispatches) with equal or lower quality; GPT-5.4 xHigh + medium workers was ~80% cheaper than solo GPT-5.4 at 94/100. — [akitaonrails](https://akitaonrails.com/en/2026/04/25/llm-benchmarks-vale-a-pena-misturar-2-modelos/) (non-peer-reviewed, small n; treat as anecdote)
- Harness study (176 configs, 4 models, SWE-bench Verified + Terminal-Bench 2.1): planning is an accuracy scaffold for weaker models and mostly a cost saver for stronger ones. — [arXiv 2609.20804](https://arxiv.org/abs/2609.20804)

### Inferences
- A consult is cheap in tokens (hundreds to ~1-2k output) but not in input: the advisor re-reads the whole transcript uncached each time, so cost scales with context length x number of consults. A curated brief (Amp style) bounds this but risks missing evidence; Anthropic chose full transcript.
- Full switch should be reserved for sustained difficulty or when consult rate would be high; Anthropic's own guidance ("if executor consults on most tasks, run the advisor model itself") supports a consult-then-switch ladder.

### Gaps
- No head-to-head published comparison of consult vs full-switch on the same tasks found.
- What the advisor's Anthropic-supplied system prompt says is not published.

## 3. Who decides to escalate; evidence on under/over-calling

### Takeaway
Models deciding via tool call is the shipped norm for consult, and the best evidence says they under-call by default (especially on coding and for small/low-effort executors), so vendors steer with system prompts; for switching, decisions are by user, phase, classifier router, or (research) learned/heuristic monitors on trajectory signals.

### Cited Findings
- Anthropic: "Without system-prompt steering, the executor tends to under-call the advisor in some domains, particularly coding tasks"; Haiku 4.5 applies default guidance conservatively; a tuned prompt block raised Haiku pass rate by ~7.5 pts on an internal coding benchmark. — [API docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool)
- Consult rate varies by task and effort: Opus 5.5 + Fable advisor consulted 1/300 on one benchmark and lost 7 pts; at "very low efforts" executors may stop detecting they are stuck; same executor consulted heavily on DeepSWE but stopped on SWE-bench Pro. — [Optimizing for cost and intelligence](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence) (summariser-relayed)
- Amp does not force oracle use, to limit cost/latency; docs warn against calling it for trivial agreement. — [Amp oracle summary](https://ampcode.com/news/oracle) (secondary)
- Over-calling concern: Claude Code docs note advisor "may use more tokens" and no cap setting exists. Systematic over-calling evidence: none found. — [advisor docs](https://code.claude.com/docs/en/advisor)
- Blog experiment: with subagents merely available (voluntary delegation), zero delegations occurred across seven variants. — [akitaonrails](https://akitaonrails.com/en/2026/04/25/llm-benchmarks-vale-a-pena-misturar-2-modelos/) (anecdote)
- Router/learned approaches: SWE-Router (arXiv 2607.00053) routes per-step after a few cheap exploratory turns; claims a Bayes-optimality result that conditioning on the partial trajectory never hurts; abstract claims large cost-efficiency gains while keeping most of stronger-model performance (numbers not in the fetched abstract). — [arXiv 2607.00053](https://arxiv.org/abs/2607.00053). TACIT-Switch (arXiv 2608.27911) learns handoff thresholds from censored teacher interventions; +7.4-11.1 pts over baseline routers at comparable cost, but on ALFWorld/DABench (not coding). — [arXiv 2608.27911](https://arxiv.org/abs/2608.27911)
- Gemini CLI/Cursor use a classifier on the prompt/request (pre-execution), not on trajectory signals. — see section 1 sources.

### Inferences
- A hybrid is supported by evidence: deterministic trouble-signal monitor (LivePlan style) as a backstop, plus system-prompt steering to make the model call consult at the two known high-value moments (post-orientation, pre-completion). Relying on the cheap model's self-assessment alone is the documented failure mode.
- Trajectory-conditioned decisions beat task-only routing in the one theoretical/empirical source found (SWE-Router), supporting mid-turn escalation versus pre-turn classification.

### Gaps
- No quantified over-calling study. No evidence found on how often models call such tools "appropriately" beyond Anthropic's consult-rate anecdotes.
- SWE-Router/TACIT-Switch only read at abstract level.

## 4. Published cost-savings vs resolve-rate numbers

### Takeaway
Best-sourced numbers are Anthropic's (modest savings with small gain for Sonnet+Opus; big relative gain for Haiku+Opus; near-nothing for near-frontier pairs) and Aider's older architect results; independent evidence is mixed and small-n.

### Cited Findings
- Sonnet+Opus advisor: +2.7 pts, -11.9% cost (SWE-bench Multilingual). Haiku+Opus: 19.7% -> 41.2% (BrowseComp), ~85% cheaper than Sonnet solo. — [Anthropic blog](https://claude.com/blog/the-advisor-strategy)
- Opus 5.5 + Fable 5.1: +1.7 pts for ~2.1x cost (internal coding). — [Optimizing page](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence)
- Aider architect: +3-5 pts for self-pairing, SOTA 85% with o1-preview+o1-mini/DeepSeek; slow/expensive. — [Aider](https://aider.chat/2024/09/26/architect.html)
- LivePlan: +9.9% avg resolve for $0.08/instance. — [arXiv 2608.06701](https://arxiv.org/abs/2608.06701)
- Planning in harness: accuracy for weak, cost saving for strong models. — [arXiv 2609.20804](https://arxiv.org/abs/2609.20804)
- Forced multi-agent cost 3x in one blog trial; subscription users have zero marginal cost so cheap tiering gives no economic benefit there (author's argument). — [akitaonrails](https://akitaonrails.com/en/2026/04/25/llm-benchmarks-vale-a-pena-misturar-2-modelos/)
- Cursor claims cost reductions from routing (a third-party headline says 60%) but no primary figures on the docs page I fetched. — [Cursor Router docs](https://cursor.com/docs/cursor-router); [explainx headline](https://www.explainx.ai/blog/cursor-router-auto-model-selection-july-2026) (unverified)

### Inferences
- Escalation ladder value depends on gap between tiers; also compare against "stronger model at low effort" baseline (Anthropic's explicit recommendation) and against effort-sweep on the cheap model.

### Gaps
- No published resolve-rate-vs-cost curve for cheap-first with mid-session escalation on SWE-bench Verified by a shipped product. SWE-Router's dataset may allow it; numbers not extracted.

## 5. Prompt-caching economics of mid-session model switching

### Takeaway
All three vendors treat caches as model-specific and prefix-exact; Anthropic and Claude Code docs explicitly say a model switch re-reads the whole history uncached (and a cache-write premium applies on the new model); a consult via the server-side advisor avoids this for the main model but the advisor reads uncached unless opted in.

### Cited Findings
**Anthropic**
- "Each model has its own cache. Switching models means the next request reads the entire conversation history with no cache hits." Changing effort also invalidates on most models (kept on Opus 5.5, Sonnet 5.5, Fable 5.1 via API key/subscription); fast mode header is part of the cache key. — [Claude Code prompt caching](https://code.claude.com/docs/en/prompt-caching)
- Claude Code asks for confirmation on `/model` only while the cache is still warm; supports a `PreModelSwitch` hook for decision control. — same source
- Toggling `/advisor` keeps the main cache (tool definition sits after the breakpoint); advisor guidance gets cached as part of transcript. — [Claude Code prompt caching](https://code.claude.com/docs/en/prompt-caching), [advisor docs](https://code.claude.com/docs/en/advisor)
- Subagents start their own conversation with its own prefix: first request does not read the parent's cache; get 5-minute TTL even on subscription unless configured; forks inherit parent's prefix and read its cache. — same source
- Pricing multipliers: 5-minute write 1.25x base input, 1-hour write 2x, read 0.1x (0.05x on Opus 5.5, 0.025x on Fable 5.1/Mythos 5.1); TTL refreshed at no extra cost on reuse; TTL measured from the request start; cache entries available only after first response begins; isolation per workspace on Claude API. Min cacheable prefix is model-specific (512 to 4,096 tokens). — [Anthropic prompt caching docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- Claude Code TTL defaults: main conversation 1h only on a subscription within plan usage, otherwise 5m; everything else (subagents, compaction) 5m. — [Claude Code prompt caching](https://code.claude.com/docs/en/prompt-caching)
- Anthropic's own note: Claude Code design rationale post "Prompt caching is everything" (not fetched). — [link](https://claude.com/blog/lessons-from-building-claude-code-prompt-caching-is-everything)

**OpenAI**
- Caching is model-specific; when switching models re-check minimum cacheable length, retention and breakpoints. GPT-5.6+: 30-minute retention after last use, cache write 1.25x input, read 0.1x (0.05x on one model); earlier models: no write charge, in-memory (5-10 min) or 24h retention. `prompt_cache_key` for routing; cached state lives on individual machines; above ~15 req/min per prefix can overflow and reduce hits. — [OpenAI prompt caching guide](https://developers.openai.com/api/docs/guides/prompt-caching)

**Google**
- Implicit caching on by default for Gemini 2.5+ models; explicit caching opt-in via generateContent; min-token thresholds differ by model (2,048 for 2.5; 4,096 for 3.x per the page). Doc page did not state TTL defaults or per-model scoping explicitly. — [Gemini caching docs](https://ai.google.dev/gemini-api/docs/caching). Explicit-cache storage fees (e.g. ~$1.00-4.50 per 1M tokens/hour) and ~10% read price come only from aggregator pages - [costgoat summary](https://costgoat.com/pricing/gemini-api) (unverified; check ai.google.dev pricing).

**Amp**
- Explicitly forbids mid-thread mode change because it invalidates prompt caching. — [Amp Dial](https://ampcode.com/docs/the-dial)

### Inferences
- Break-even for a full switch: cost of re-reading N context tokens at the new model's uncached input rate plus the 1.25x write premium (vs 0.1x read had you stayed) - roughly a 12x per-token penalty on the first request relative to a warm cache read, plus any latency. Minimising number of switches and switching early (small context) or after cache expiry (Claude Code itself skips the warning once TTL lapsed) are consistent with the docs.
- Consult via a separate call to a different model forces the oracle to pay full uncached input on the transcript each time (unless using the advisor `caching` option, breakeven ~3 calls) but leaves the cheap model's cache untouched - this favours consult over switch for brief, infrequent escalation, and favours curated briefs when context is large.
- Escalating effort tier within the same model is cheaper than a model switch only on models where effort changes keep the cache (Opus 5.5, Sonnet 5.5, Fable 5.1 per docs).

### Gaps
- No vendor guidance beyond "switching costs a cache miss"; no document found recommending a specific policy for mid-conversation switching.
- Gemini TTL defaults, per-model cache scoping and pricing not verified from primary pages; OpenAI 5.6+ figures from one fetched guide page only.
