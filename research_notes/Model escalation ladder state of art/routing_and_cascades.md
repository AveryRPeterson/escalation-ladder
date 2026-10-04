# LLM model routing and cascading: state of the art (as of Oct 2026)

Method note: ~25 tool calls (search + fetch). Several 2026 arXiv items were read via abstract-page summaries only, not full text; flagged "abstract-level". Sources on blogs/GitHub issues are labelled as non-primary. Vendor numbers are labelled as vendor-reported. Figures from the Anthropic "optimizing for cost and intelligence" page were obtained through a summarising fetch tool and the model names in it (e.g. "Fable 5.1", "Opus 5.5") should be re-checked against the live page before quoting.

## 1. Main approaches and reported cost/quality results

### Takeaway
Four families exist: (a) cascades (try cheap, verify, escalate: FrugalGPT, AutoMix), (b) pre-generation learned routers (RouteLLM, Hybrid LLM, Not Diamond-style), (c) market/vendor routers (OpenRouter Auto, GPT-5 router, Azure router), (d) "ask for help" schemes where the cheap model stays in charge and consults a strong one (Anthropic advisor tool). Measured savings are large (35-98%) on single-prompt benchmarks, but a 2026 decision-theoretic result says a cheap pre-generation router often beats cascades because cascades pay the cheap model's generation cost before deciding.

### Cited Findings
- FrugalGPT (Stanford, 2023): LLM cascade that matches best single LLM (GPT-4) with up to 98% cost reduction, or +4% accuracy at same cost; 98% was on HEADLINES dataset. Measured, dataset-specific. — [arXiv 2305.05176](https://arxiv.org/pdf/2305.05176)
- Hybrid LLM (ICLR 2024): router predicts query difficulty, up to 40% fewer calls to large model with no drop in response quality; quality threshold tunable at runtime. — [arXiv 2404.14618](https://arxiv.org/abs/2404.14618)
- AutoMix (NeurIPS 2024): small model generates, same model self-verifies (entailment/few-shot), a POMDP router treats verification as a noisy observation of difficulty; >50% compute cost reduction at comparable performance across 5 models/5 datasets. — [arXiv 2310.12963](https://arxiv.org/pdf/2310.12963)
- RouteLLM (LMSYS/Anyscale, ICLR 2025): routers trained on Chatbot Arena preference data; >85% cost reduction on MT-Bench, 45% on MMLU, 35% on GSM8K at 95% of GPT-4 quality; matrix-factorization router needed 26% GPT-4 calls on Arena data alone, ~14% with augmented data. — [LMSYS blog](https://www.lmsys.org/blog/2024-07-01-routellm/), [arXiv 2406.18665](https://arxiv.org/pdf/2406.18665)
- RouterArena (ICLR 2026): 8,400 queries; leaderboard top is academic MIRT-BERT (67.3) then Azure-Router (66.4), CARROT (63.9), vLLM-SR (63.8), GPT-5 as a single model (62.7). Commercial routers up to 87% accuracy but high cost; open-source ones 2-5% lower accuracy at a fraction of cost; most academic routers add <100 ms, API-dependent ones >200 ms. Secondary summary (the "235% cost reduction" phrase in the snippet is garbled; do not quote). — [arXiv 2510.00202](https://www.arxiv.org/pdf/2510.00202v1), [ICLR PDF](https://proceedings.iclr.cc/paper_files/paper/2026/file/4987bb24bc53c198785922d1bd9e18cf-Paper-Conference.pdf), [summary](https://www.emergentmind.com/topics/routerarena)
- Survey of dynamic routing/cascading (Moslem & Kelleher, 2026): useful taxonomy; I could not parse the PDF content, so no specifics extracted. — [arXiv 2603.04445](https://arxiv.org/pdf/2603.04445)
- "Is Escalation Worth It?" (2026, abstract-level): cascades must always pay the cheap model's generation first; across MATH, MMLU, TriviaQA, SimpleQA, LiveCodeBench a lightweight pre-generation router beat the best cascade policy on 4 of 5 datasets; simple deterministic cascades match complex multi-stage ones. — [arXiv 2605.06350](https://arxiv.org/abs/2605.06350)
- OpenRouter new Auto Router: evaluated on MMLU-Pro, tau3-bench Banking, WideSearch, DSQA, SWE-Atlas QnA; claims same performance as old router at lower cost "in most domains" with exceptions (vendor-reported, no independent replication found). Routing by trailing-7-day community spend means non-reproducible routing (third-party opinion). — [OpenRouter blog](https://openrouter.ai/blog/announcements/introducing-the-new-auto-router/), [buyer's guide opinion](https://www.beri.net/article/model-router-buyers-guide-failover-not-judgment-2026)
- Martian: an academic evaluation (RouterBench-line work, as cited by search summary) found the Martian router ignored the user-provided model list and was excluded (Nov 2024); Martian's homepage no longer leads with routing (secondary). Not independently verified here. — [Rerouting LLM Routers](https://arxiv.org/html/2501.01818v1), [comparison page](https://www.respan.ai/market-map/compare/martian-vs-openrouter)
- Not Diamond: I did not retrieve a primary source or independent evaluation. Gap.
- GPT-5 router: OpenAI shipped a real-time router between a fast model and a thinking model; at launch the "autoswitcher" was out of commission for part of a day and Altman said that made GPT-5 seem "way dumber"; he later said decision-boundary interventions were being made. — [TechCrunch](https://techcrunch.com/2025/08/08/sam-altman-addresses-bumpy-gpt-5-rollout-bringing-4o-back-and-the-chart-crime/), [Axios](https://axios.com/2025/08/12/gpt-5-bumpy-launch-openai). I did not find a published router accuracy/cost figure from OpenAI. Gap.
- Anthropic advisor tool (vendor-reported): cheaper executor (Haiku/Sonnet) consults a stronger advisor mid-generation in one /v1/messages request; advisor sees the full transcript and returns guidance; `max_uses` is the primary cost cap; advisor-side caching breaks even at ~3 calls. — [Advisor tool docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool), [Claude Code advisor docs](https://code.claude.com/docs/en/advisor)
- Anthropic-reported advisor measurements (vendor, internal benchmarks, via summarising fetch): strong executor + strongest advisor gained +1.7 pts for ~2.1x cost vs executor alone ("lands about on the executor's own effort curve"); mid/low executors recover at least half the gap when they actually consult; weak/low-effort executors may stop consulting. — [Optimizing for cost and intelligence](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence)
- Anthropic effort data (vendor): on long-horizon coding (SWE-bench Pro) effort buys accuracy steeply (medium: -2.5 pts at 70% cost; low: -8 pts at 33% cost vs high); on research/knowledge tasks the curve is nearly flat (medium matches default at 70-87% of cost). Same page as above.

### Inferences
- Effort-as-rung (not just model-as-rung) is supported by vendor data, but the benefit is task-dependent: for coding the effort curve is steep, so de-escalating effort is riskiest exactly in the user's domain.
- The advisor tool is a close sibling of the user's `request_escalation`/`consult_oracle` tool; the main difference is that advisor keeps the cheap model as the executor and only imports guidance, whereas the ladder swaps the executor itself.

### Gaps
- No primary performance data found for Not Diamond, Unify, or Google's equivalent (Gemini auto/"flash vs pro" routing). No OpenAI-published router quality/cost numbers.

## 2. Per-request vs per-session/trajectory routing; switching mid-trajectory

### Takeaway
2026 has a real, growing literature on routing inside agent trajectories, and its most important findings cut against naive per-step switching: switching is not free (cache loss, "handoff tax", off-policy continuation), escalation with full history recovers less than half the gap, and replay-based offline evaluation is invalid for routers.

### Cited Findings
- The Handoff Tax (2026, coding agents, abstract-level): full-trajectory escalation from low-cost to high-cost model "recovers less than half of the LC-to-HC quality gap while incurring a substantial cost premium"; trimming inherited trajectory info improves quality. Downshift (HC to LC) has a favourable trade-off and benefits from keeping the HC model's trajectory; the best interface (full / compacted / dropped history, repo state kept) reverses with direction. — [arXiv 2608.24358](https://arxiv.org/abs/2608.24358)
- The Replay Gap (2026): swapping a model mid-trajectory rewrote 61-94% of post-fork actions; 74-77% of early swaps diverged at the very first action after the switch (6-35% for controls); only 3% of replayed states stayed valid; replay evaluation mispredicted success outcomes; all 5 outcome reversals occurred in swap conditions, 0 in 359 control forks. Conclusion: static/replay evaluation of mid-trajectory routers "scores the wrong world"; evaluate live. — [arXiv 2608.08239](https://arxiv.org/abs/2608.08239)
- TwinRouterBench (2026, abstract-level): 970 router-visible prefixes from 520 instances (SWE-bench, BFCL, mtRAG, QMSum, PinchBench) plus a live 500-case SWE-bench Verified track; designed to expose the static-vs-live discrepancy. — [arXiv 2605.18859](https://arxiv.org/abs/2605.18859)
- TACIT-Switch (2026, abstract-level): learns when to do a one-way "permanent handoff" from cheap to expensive model using censored teacher-intervention times and cumulative trajectory risk (mixture-cure threshold model); +7.4 to +11.1 pts success over baseline routing at comparable cost on ALFWorld/DABench-style tasks; task features and cumulative trajectory risk are complementary signals. — [arXiv 2608.27911](https://arxiv.org/abs/2608.27911)
- AgentRouter (ICML 2026 AgenticUQ workshop, abstract-level): step-level 12M-parameter classifier trained on 50k annotated trajectory steps; 72% cost reduction at 97.3% of frontier quality; claims RouteLLM and FrugalGPT only get 31% and 44% savings when applied per step; routing accuracy 91% on easy steps falling to 76-82% on harder tiers. Workshop paper, self-reported. — [arXiv 2609.22951](https://arxiv.org/abs/2609.22951)
- MTRouter (ACL 2026, abstract-level): history-model joint embeddings for multi-turn routing; beats GPT-5 on ScienceWorld at 58.7% lower cost, 43.4% lower cost on HLE at comparable accuracy; credits fewer model switches and tolerance to transient errors. — [arXiv 2604.23530](https://arxiv.org/abs/2604.23530)
- DialRouter (2026): argues per-turn routing is myopic given delayed rewards and cost depends on the sequence of choices; MCTS-derived routing policy beats single LLMs and baselines (dialogue, not coding). — [arXiv 2604.12385](https://arxiv.org/abs/2604.12385)
- Switchcraft (2026, tool-calling): DistilBERT router, 82.9% accuracy, 84% inference cost reduction; also found larger models do not consistently win at tool use and cheaper models sometimes cost more total through token-heavy reasoning. — [arXiv 2605.07112](https://arxiv.org/abs/2605.07112)
- ORACLE (2026): adaptive-verifier routing for agentic tasks improves the accuracy-cost frontier up to 7 pts over routing baselines on SWE-bench, tau2-bench, Terminal-Bench 2.0. (Note: a search hit labelled "TRACE-ROUTER" 2607.22465 resolved to this ORACLE paper; I could not verify TRACE-ROUTER.) — [arXiv 2607.22465](https://arxiv.org/abs/2607.22465)
- Practitioner report (blog, non-primary): switching to a 5x cheaper-per-token model raised total cost because it looped (~0.5M tokens on one failed review), had behavioural API incompatibilities, and provider switches mid-session cold-started prompt caches. — [Sonar blog](https://www.sonarsource.com/blog/we-switched-to-a-5x-cheaper-llm-our-costs-went-up/)
- Prompt-cache switching cost: DialRouter and practitioner threads note switching models invalidates cached context so full dialogue history is re-billed at uncached input rates; caches are per model (and provider). Practitioner claim of "up to 10x" is from a GitHub issue, unverified. — [arXiv 2604.12385](https://arxiv.org/abs/2604.12385), [cuttle issue #177](https://github.com/saman-mb/cuttle/issues/177)

### Inferences
- The Handoff Tax result is the most directly relevant to the ladder: "escalate with the full cheap-model trajectory" is likely suboptimal; consider handing the stronger rung a compacted summary or fresh start with repo state, particularly when the cheap model was looping.
- Rewriting model per API request mid-turn means every rung change is a cold prompt cache for the new model; escalation costs should be modeled as (re-ingest full context at uncached price) rather than just the price delta.

### Gaps
- No full-text read of any 2026 agent-routing paper; effect sizes above are abstract-level. No source found that tests Claude-family Haiku/Sonnet/Opus rung ladders specifically.

## 3. Escalation signals: which work, which are poorly calibrated

### Takeaway
Self-reported/verbalized confidence is systematically overconfident, especially in agents; deterministic, grounded signals (tests, compiler/tool errors, execution verifiers) calibrate best; cheap same-family verifiers share the generator's blind spots.

### Cited Findings
- Agentic overconfidence: some agents succeed 22% of the time but predict 77%; pre-execution estimates sometimes discriminated better than post-execution; adversarial "find the bug" framing calibrated best. — [arXiv 2602.06948](https://arxiv.org/abs/2602.06948)
- Confidence Dichotomy: tool-using agents with evidence tools (web search) are severely overconfident; verification tools (code interpreter, deterministic feedback) ground reasoning and reduce miscalibration. — [arXiv 2601.07264](https://arxiv.org/abs/2601.07264)
- LLMs systematically produce inflated verbalized confidence across models/domains/elicitation methods; mechanistic work localises inflation to mid-late layers (abstract-level search summary). — [arXiv 2608.18106](https://arxiv.org/pdf/2608.18106), [overview](https://tianpan.co/blog/2026-04-20-llm-calibration-production-overconfidence) (blog)
- Cheap Verifiers, Large Blind Spots (2026): student-error blind-spot rate of the verifier rose from 12% to 55% as the student grew 0.5B to 32B; a frontier verifier escalated on 46% of hard-MATH queries vs 39% true error rate; in-loop cascade metrics showed flat ~3% error while delivered error reached 32%; fine-tuning on rejected examples degraded. Same-family verifiers: ~64.5% of self-generated errors survive self-check (secondary snippet from a related 2026 paper). — [arXiv 2609.01345](https://arxiv.org/abs/2609.01345), [arXiv 2607.13918](https://arxiv.org/pdf/2607.13918)
- AutoMix explicitly models self-verification as a noisy observation (POMDP) instead of trusting it, because self-verification is unreliable. — [arXiv 2310.12963](https://arxiv.org/pdf/2310.12963)
- Confidence-threshold deferral has a known calibration problem; conformal approaches replace thresholds (snippet-level). — [arXiv 2607.25018](https://arxiv.org/pdf/2607.25018)
- Under black-box API access logprobs are usually unavailable, so sampling frequency (self-consistency) is the standard substitute (snippet-level). — [arXiv 2607.25018](https://arxiv.org/pdf/2607.25018)
- Advisor measurements (vendor): the consult rate of the executor collapsed to near zero on some tasks at low effort or on tasks where it did not recognise being stuck (e.g. 1 of 300 on a chart task; SWE-bench Pro Sonnet pairing scored below executor alone), i.e. a model-initiated escalation tool under-fires exactly when the model is least capable. — [Optimizing for cost and intelligence](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence)
- TACIT-Switch: cumulative trajectory risk plus task features outperform single-step signals (abstract-level). — [arXiv 2608.27911](https://arxiv.org/abs/2608.27911)

### Inferences
- The ladder's mix is well-aligned: loops, repeated tool errors, truncation, refusal and independent review are grounded/behavioural signals; `request_escalation` self-confidence is the weakest and should be treated as a recall-limited hint (it will under-fire), not as a gate.
- "Independent review" by the same model family/tier carries blind-spot risk; review by a different-tier or execution-based check (tests) is stronger.

### Gaps
- No study found comparing logprob entropy vs self-consistency vs tool-error signals specifically for coding-agent escalation. Thresholds for "loop detected" or "N repeated errors" have no published tuning data that I found.

## 4. De-escalation, hysteresis, oscillation, switching cost

### Takeaway
Little peer-reviewed work directly on stepping back down; the evidence is indirect: the Handoff Tax says downshift is favourable (cheap model can continue a strong model's trajectory), MTRouter credits fewer switches, and practitioners recommend asymmetric thresholds. No formal hysteresis study for LLM routers found.

### Cited Findings
- Downshift (HC to LC) mid-run has a favourable cost-quality trade-off and benefits from preserving HC's trajectory. — [arXiv 2608.24358](https://arxiv.org/abs/2608.24358)
- MTRouter attributes gains partly to fewer switches and tolerance to transient errors. — [arXiv 2604.23530](https://arxiv.org/abs/2604.23530)
- Design recommendation (GitHub feature issue, non-primary): escalate fast on strong evidence, require more evidence or stable transition to downgrade; use minimum turns before downgrade, separate escalation/de-escalation thresholds, cooldowns, sticky intent. — [SwitchYard #100](https://github.com/Fledgewing/SwitchYard/issues/100)
- TACIT-Switch frames handoff as one-way and permanent per episode (no de-escalation), which sidesteps oscillation. — [arXiv 2608.27911](https://arxiv.org/abs/2608.27911)
- Switching cost: cache loss on every model change (see section 2). Anthropic advisor docs also warn that toggling caching on/off mid-conversation causes misses. — [Advisor tool docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool)

### Inferences
- "Step down after N clean steps" is consistent with the (thin) guidance; what is missing in published work is the choice of N, and an explicit cost-of-switch term (cache re-ingest) in that decision. Cooldown after an escalation and a cap on switches per session are cheap safeguards against thrash.
- Because each down-switch also incurs a cold cache, stepping down is only profitable if remaining expected steps are enough to amortise it.

### Gaps
- No empirical oscillation/thrash measurements in LLM routing literature found.

## 5. Production failure modes

### Takeaway
Reported failures: router outage silently degrading quality (GPT-5), cost blowups from cheap-model loops and cache loss, adversarial/ambiguous prompts steering routers, verifier blind spots hidden from in-loop metrics, and evaluation that does not transfer to live agents.

### Cited Findings
- GPT-5 launch: broken autoswitcher defaulted users to the cheaper model with no warning; perceived "dumber" model. — [TechCrunch](https://techcrunch.com/2025/08/08/sam-altman-addresses-bumpy-gpt-5-rollout-bringing-4o-back-and-the-chart-crime/), [Axios](https://axios.com/2025/08/12/gpt-5-bumpy-launch-openai)
- Rerouting attack: query-independent "confounder gadget" strings force routers to the strong model, working white- and black-box against open-source and commercial routers; threats include cost escalation, quality hijacking, safety bypass. — [arXiv 2501.01818](https://arxiv.org/abs/2501.01818)
- Cascade-specific adversarial attack degrades both cost-efficiency and accuracy by exploiting front-end model and routing logic. — [arXiv 2605.17288](https://arxiv.org/abs/2605.17288); related: [Route to Rome](https://arxiv.org/pdf/2604.15022)
- Router robustness: embedding-based routers >90% consistency under perturbations; feature/KNN routers less reliable. — [RouterArena](https://www.arxiv.org/pdf/2510.00202v1)
- Cheaper-model cost blowups and cache loss: see Sonar blog above (non-primary).
- Silent metric blindness in cascades: see Cheap Verifiers paper above. — [arXiv 2609.01345](https://arxiv.org/abs/2609.01345)
- Evaluation validity: replay-based router eval invalid for agents; temperature-0 not deterministic (FP8 controls diverged on 90%+ of forks). — [arXiv 2608.08239](https://arxiv.org/abs/2608.08239)
- Router quality cliffs: AgentRouter's routing accuracy drops from 91% to 76-82% on harder steps. — [arXiv 2609.22951](https://arxiv.org/abs/2609.22951)

### Inferences
- Fail-safe direction matters: a failed/absent router signal should default to the higher rung (or at least be visible), not silently the cheap one.
- Tool-output or file content can carry text that triggers model-called escalation or manipulates signals; escalation triggers driven by model text are an attack surface for cost escalation.

### Gaps
- Few public post-mortems besides GPT-5; most "production" claims here come from blogs or issues.

## 6. Mapping lessons to the escalation ladder design

Sound / supported by literature
- Cheap-by-default with escalation on grounded behavioural signals (loops, tool errors, truncation, refusal, step stall, external review) matches the finding that deterministic signals calibrate better than verbalized confidence ([2601.07264](https://arxiv.org/abs/2601.07264), [2602.06948](https://arxiv.org/abs/2602.06948)).
- Within-trajectory, cumulative-risk escalation is exactly what TACIT-Switch, AgentRouter and MTRouter pursue; those report cost cuts of roughly 44-72% at ~97% quality (self-reported, abstract-level).
- Treating `request_escalation` as one signal among many is right; the vendor advisor data shows model-initiated consults under-fire at low effort.
- Stepping down after clean steps is supported in direction (downshift is favourable per [2608.24358](https://arxiv.org/abs/2608.24358)).
- Modulating effort as well as model is supported by Anthropic's effort-curve data ([doc](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence)).

Possibly reinventing
- Advisor pattern: Anthropic ships `advisor_20260301` where the cheap executor consults a strong model with the full transcript and a `max_uses` cap; the ladder's `consult_oracle` tool overlaps with it ([docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool)). Consider whether guidance-only (advisor) is a cheaper first response to some signals than swapping executor.
- Threshold/hysteresis logic is generic and appears in practitioner guidance only.

Overlooked or at risk
1. Handoff tax: escalating with full cheap-model history recovers under half the gap; test compacted/fresh-context handoff on escalation, and keep full history on down-shift ([2608.24358](https://arxiv.org/abs/2608.24358)).
2. Cache economics: every rung change cold-starts the new model's prompt cache; add a switching-cost term and min-dwell time; avoid mid-turn flips when avoidable.
3. One-rung-at-a-time escalation: no literature supports it as optimal; it adds latency and cost when the problem needs a jump (TACIT-Switch uses a direct one-way handoff). Consider skip-level escalation on strong signals (e.g., refusal or failed independent review) and measure.
4. Independent review should not share the cheap model's blind spots; prefer execution-based checks or a different tier ([2609.01345](https://arxiv.org/abs/2609.01345)).
5. In-loop metrics can look healthy while delivered quality degrades; log outcomes against an external check (tests passing) rather than the ladder's own signals.
6. Evaluate live, not by replay: any offline replay of logged sessions will mispredict ([2608.08239](https://arxiv.org/abs/2608.08239)); use a live benchmark like the SWE-bench track in [TwinRouterBench](https://arxiv.org/abs/2605.18859).
7. Cheap-model loops can cost more than a strong model's one-pass; keep hard token/step caps per rung ([Sonar blog](https://www.sonarsource.com/blog/we-switched-to-a-5x-cheaper-llm-our-costs-went-up/)).
8. Cascade overhead: the cheap model's attempt is sunk cost; a pre-generation difficulty classifier at session start could beat purely reactive escalation ([2605.06350](https://arxiv.org/abs/2605.06350)); a hybrid (initial tier chosen from task features, then trajectory risk) is what the agent-routing papers do.
9. Fail-safe and adversarial: define behaviour when signal sources fail (default up), and cap total escalations/session against manipulated tool output.
10. Task dependence: effort de-escalation is cheap for research tasks, costly for long-horizon coding (-8 pts at low); the start tier may warrant being task-type dependent.
