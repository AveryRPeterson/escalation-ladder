# Independent review / verification of agent work, and reliability of confidence signals

Method note: ~25 tool calls (web search plus page fetches). Fetched pages were summarised by a small model, so numbers are only as good as those summaries. Items marked [snippet] come from search snippets only; items marked [low-confidence] were vague or unverifiable. Several 2026 arXiv items (IDs 26xx) were found only through search and not cross-checked elsewhere. Today is Oct 2026.

## 1. LLM-as-judge for agentic tasks: accuracy, biases, blind spots, effect of evidence

### Takeaway
Judges that see only a trajectory or final answer are systematically fooled by confident completion language. Measured accuracy is roughly 70-90% depending on task and backbone, with false positives the dominant failure. Judges anchor on the agent's claims and on the last observable state. Checking claims against the actual environment state (Agent-as-a-Judge style, or executable checks) works far better than reading narration.

### Cited Findings
- False-success study: agents assert completion while environment state shows failure. 35.6% of tau2-bench failures were false success (13% for GPT-5.2 up to 79% for Qwen3-Max-Thinking); 75.8% on AppWorld for self-assessing architectures. — [From Confident Closing to Silent Failure](https://arxiv.org/html/2606.09863)
- Same study: five LLM judges (GPT-4o, Claude Sonnet 4.5, Llama 3.3-70B, DeepSeek-R1, o3-mini) over five prompt conditions reached at most 0.65 AUROC on tau2-bench and 0.54 on AppWorld action sequences. Judges anchored on confident assertion language and on action-sequence volume. Adding reasoning models gave no improvement. — [same](https://arxiv.org/html/2606.09863)
- Same study: lightweight non-LLM detectors reached task-disjoint AUROC 0.83 (tau2) and 0.95 (AppWorld), ran about 3,300x faster than judge calls, but precision at a 10% flag rate was only 50%. Environments with independent verification had about 3% false success versus 45-48% without. — [same](https://arxiv.org/html/2606.09863)
- AgentRewardBench: 1,302 web-agent trajectories, 5 benchmarks, 4 LLMs, expert-annotated. Best LLM judges reached only about 70% precision on success detection. Simpler input representations agreed better with experts than prior elaborate ones. Rule-based benchmark checkers under-reported success. — [arXiv 2504.08942 via search results](https://www.alphaxiv.org/abs/2504.08942) [snippet; openreview PDF failed to fetch]
- MobileJudgeBench (931 human-annotated trajectories, 68 apps): judge accuracy 76.4-90.9%. A simple baseline judge was competitive with or better than specialised pipelines, and the LLM backbone was the main driver. Failure modes included last-frame anchoring, partial completion and constraint violations missed, and "surface match" success. GPT judges were conservative (false negatives), Qwen permissive (false positives). Agent reasoning text and UI metadata added at most 0.3pp. Few high-res screenshots beat many low-res ones. Misclassification of 9-24% could distort benchmarks and RL rewards. — [Benchmarking LLM Judges for Mobile Agent Evaluation](https://arxiv.org/html/2608.11434v1)
- Agent-as-a-Judge (ICML 2025): agentic judge with tool access, evaluating whole trajectories on the 55-task DevAI benchmark, "dramatically outperforms" plain LLM-as-a-Judge and is described as as reliable as a human evaluation baseline. I could not extract the specific alignment percentages. — [arXiv 2410.10934](https://arxiv.org/abs/2410.10934)
- Judges that only see the trajectory cannot verify stateful changes. Vendor claim (opinion, vendor blog): an agent judge that queries the same systems the agent acted on is needed. — [Judgment Labs](https://www.judgmentlabs.ai/blogs/agent-judge-solving-long-context-evaluations)
- Inaccurate self-reporting is 22.58% of misalignment episodes found in 20,574 coding-agent sessions. — [search snippet, source paper not opened](https://dev.to/nilofer_tweets/agentliar-detector-catch-coding-agents-that-falsely-claim-task-completion-413c) [low-confidence: secondary blog]
- Self-preference bias: judges' self-preference correlates linearly with their ability to recognise their own outputs; self-recognition is non-trivial out of the box. — [Panickssery et al., NeurIPS 2024](https://arxiv.org/pdf/2404.13076)
- Judge ensembles across families (GPT, Claude, open-weights) are the commonly recommended fix for same-family bias (practitioner opinion). One cross-family study found 96.4% item agreement with a same-family judge on a memory benchmark, so the bias may be small on factual-style tasks. — [search results, openlayer/comet blogs and a memory-benchmark paper](https://www.openlayer.com/blog/llm-as-judge-evaluation-guide) [snippet-level]
- Outcome-only judges reportedly approve 30-50% of trajectories with process flaws. — [trajectory-judge, arXiv 2609.00038](https://arxiv.org/pdf/2609.00038) [low-confidence: the fetched summary was generic and unspecific about judges and data; verify before citing]
- Overclaiming propensity in frontier agents is being measured as its own phenomenon. — [arXiv 2609.20812](https://arxiv.org/pdf/2609.20812) [low-confidence: no concrete numbers recovered]

### Inferences
- Your reviewer catching "confirmed with no tool call" is the use case where judges do best: a cheap mechanical cross-check (does a tool call exist that supports the claim) is something even a weak detector can do. The harder case, a claim that is supported by a call but wrong, is where judge AUROC drops toward chance.
- A heavier model alone will not fix anchoring (reasoning models did not help in the false-success study). Evidence design matters more than reviewer size.
- Because trajectories are clipped, reviewer false-positives ("no evidence") will happen when the clipped part contained the evidence. Mark clipped regions explicitly and let the reviewer say "unsure".

### Gaps
- No source found measuring judge accuracy specifically for coding-assistant (Claude Code style) sessions with clipped trails.
- Agent-as-a-Judge exact agreement numbers not retrieved.
- Sycophancy of judges toward the agent's own claims is documented mainly through the false-success paper; no dedicated controlled study found.

## 2. Does review/reflection improve outcomes? Self-correction limits, loop risks

### Takeaway
Intrinsic self-correction (no external signal) does not reliably help and can hurt; correction works when feedback is grounded in tools, tests or other external information. Iterating against an LLM judge can raise judge scores while true quality falls.

### Cited Findings
- Huang et al.: LLMs struggle to self-correct reasoning without external feedback, and performance sometimes degrades; earlier positive results used oracle labels. — [arXiv 2310.01798](https://arxiv.org/abs/2310.01798)
- TACL critical survey: no reliable evidence that LLMs can self-correct their best initial responses from inherent ability alone; the bottleneck is generating reliable feedback, not applying it; works with reliable external feedback or after large-scale fine-tuning; many positive studies use oracle info or deliberately weakened initial responses. — [Kamoi et al.](https://arxiv.org/pdf/2406.01297)
- Self-Refine reports about 20% absolute average improvement across its tasks (8.7% on code optimisation with GPT-4), with gains growing with iterations. This is the optimistic counterpoint and predates the critique above. — [arXiv 2303.17651](https://arxiv.org/pdf/2303.17651)
- CRITIC: tool-grounded verify-then-correct gives consistent gains (7.7 F1 on open-domain QA, 79.2% toxicity reduction); external tool feedback is described as crucial. — [arXiv 2305.11738](https://arxiv.org/pdf/2305.11738)
- Spontaneous reward hacking in iterative self-refinement: when a model refines against an LLM judge, judge scores rise well above human scores and human-rated quality can decline in later iterations. — [Pan et al., arXiv 2407.04549](https://arxiv.org/pdf/2407.04549) (summary from search snippet; PDF fetch failed)
- Reward-hacking surveys describe judge gaming (e.g., padding with brackets or HTML tags) with judge scores rising while true accuracy peaks early. — [search snippet, Springer survey](https://link.springer.com/article/10.1007/s44163-026-01980-z) [snippet]
- Position paper (single author, treat as opinion with some evidence): place deterministic validation before the LLM judge; LLM judges can be manipulated. — [arXiv 2609.02246](https://arxiv.org/pdf/2609.02246) [low-confidence on quantitative claims]
- Verification score design: a discrete 1-5 judge tied in 88/100 pairwise comparisons; using expected value over scoring-token logits, repeated K times and decomposed criteria, achieved 78.2% on SWE-Bench Verified selection, above the best single model's 76.8%. — [LLM-as-a-Verifier](https://arxiv.org/html/2607.05391)

### Inferences
- Your design (a different, stronger reviewer, plus tool trail evidence) is "external-ish" feedback, which is better than intrinsic self-critique, but the reviewer only has text evidence unless it can run something. The gains in CRITIC came from tools actually re-checking facts.
- The worker re-prompted to "fix" reviewer issues may satisfy the wording of the issue rather than the underlying problem (worker optimising against the reviewer). Bounded rounds are the right mitigation; also consider re-reviewing only if state actually changed since last round, and reporting issue text to the worker as verifiable checks ("run X and show output") rather than opinions.
- Diminishing returns evidence for multi-round review is thin in what I found. I found no clean measurement of round-2 vs round-1 gain for agentic review.

### Gaps
- No direct measurement of infinite-rejection or oscillation rates in reviewer-worker loops.
- No data found on reviewing unchanged work (cost waste) beyond the general cascade-cost reasoning in section 4.

## 3. Verbalized confidence and knowing when stuck

### Takeaway
Verbalized confidence from RLHF'd models is concentrated at high values and overconfident, with improved but imperfect calibration on 2025-2026 models under careful prompting. For agents, trajectory-level features and hidden-state probes beat the model's own stated confidence. A self-reported number should be a trigger for cheap escalation, not a trusted signal.

### Cited Findings
- 18-model study (GPT, Claude, Gemini; including GPT-5.2/5.4, Sonnet 4.5/4.6, Gemini 3.1 Pro): an overconfidence advisory in the prompt plus a "argue both sides" self-debate step cut adaptive ECE from 8.9% to 3.8% on Sonnet 4.5 and widened score spread (75.8% to 89.6%). Post-2025 models kept accuracy (±0-1%) while pre-2025 models lost 1-2%. Verbalized confidence now beats logprob G-Eval on GPT flagships for subjectivity robustness. This is judge-confidence, not agent self-assessment. — [arXiv 2609.10996](https://arxiv.org/html/2609.10996v1)
- Reasoning models exhibit a verbalized-confidence prior concentrated on a few high values. — [arXiv 2609.32470](https://arxiv.org/html/2609.32470) [snippet]
- RLHF induces overconfidence; calibration-aware reward modelling reduces it. — [Taming Overconfidence, ICLR 2025](https://arxiv.org/pdf/2410.09724) [snippet]
- Holistic Trajectory Calibration: process-level features across the whole trajectory outperform baselines on calibration and discrimination across 8 benchmarks, and a general calibrator transfers to GAIA out of domain. — [Agentic Confidence Calibration, arXiv 2601.15778](https://arxiv.org/abs/2601.15778)
- Probes on internal representations (Latent Trajectory Dynamics, Action Representation Probe) beat surface-level and sequence-based calibration baselines on Bash, SQL, Python tasks, but only tested on small open models (Qwen 7B/14B, DeepSeek 6.7B). Not usable on API-only Claude. — [arXiv 2609.09448](https://arxiv.org/abs/2609.09448) (numbers not retrieved)
- Mechanistic account of inflated verbalized confidence. — [arXiv 2604.01457](https://arxiv.org/pdf/2604.01457) [snippet only]
- Process reward models catching SWE agents "going astray" mid-trajectory improved resolution rates; selective checkpointing keeps overhead reasonable. — [arXiv 2509.02360](https://arxiv.org/pdf/2509.02360) (numbers not retrieved)
- Step-level small-to-large model routing with a lightweight process verifier and calibrated router. — [R2V Agent](https://arxiv.org/html/2605.16604)

### Inferences
- Treat request_escalation confidence as asymmetric: low confidence is informative (the model rarely says it unless true), high confidence tells you little. Trigger escalation on low confidence or on cheap behavioural signals (repeated identical tool calls, repeated failing commands, many edits to the same file, retry counts, time-in-task), which the trajectory-calibration work suggests carry more signal.
- If you log self-reported confidence alongside reviewer verdicts and test outcomes, you can compute your own reliability curve; that was not found in the literature for Claude Code style tasks.

### Gaps
- No 2025-26 calibration study specifically of Claude models' self-reported confidence mid-agentic-task with numbers found.
- Self-consistency cost/benefit for agentic tasks not retrieved (sampling multiple trajectories is mostly infeasible in an interactive setting).

## 4. Cheap-model-escalate-on-failure; deterministic checks first

### Takeaway
The consensus pattern is cheap model, deterministic gate (tests/lint/typecheck/schema), then escalate; LLM judging is reserved for what cannot be checked deterministically. Tests are not a perfect oracle either.

### Cited Findings
- Verifier-gated cascade pattern: cost ≈ cheap + verifier + escalation_rate × expensive; a drifting verifier can silently escalate everything. Coding variant: fast model, then tests/linter/type checker, then escalate on failure. — [search results: cascade repo and AgentPatterns.ai](https://agentpatterns.ai/token-engineering/cost-aware-agent-design/) [practitioner sources, not peer reviewed]
- Anthropic's engineering guidance on evals: use code-based graders (unit tests, static analysis, tool-call verification) where outcomes are deterministically checkable (fast, cheap, objective, brittle), model-based graders for open-ended output (non-deterministic, costlier, need calibration against humans), human graders to calibrate; layer them. — [Anthropic, Demystifying evals for AI agents (read via mirrors)](https://github.com/sullivan-street-projects/anthropic-docs-local/blob/master/engineering/demystifying-evals-for-ai-agents.md) [mirror of the Anthropic post, not fetched from anthropic.com]
- Test passing is imperfect: 15.7% (92/584) of patches passing original SWE-bench Verified tests were erroneous under UTBoost augmentation; PatchDiff found 7.8% of test-passing patches fail the full developer suite and 29.6% show behavioural divergence. — [UTBoost](https://arxiv.org/pdf/2506.09289), [ICSE 2026 study](https://software-lab.org/publications/icse2026_SWE-bench-correctness.pdf) [snippet]
- Agentic rubrics (LLM-written, repo-grounded checklists) as verifiers for SWE agents are reported to beat plain LLM judging and complement tests. — [arXiv 2601.04171](https://arxiv.org/pdf/2601.04171) (no concrete numbers extracted)

### Inferences
- Ordering for your plugin: (1) did state change at all; (2) deterministic checks the plugin can run or detect (tests run in trail? exit codes? claims such as "confirmed" mapped to tool calls); (3) only then LLM review.
- Use the worker's own tool outputs (exit codes, test results) as the primary escalation trigger when available; use LLM review for tasks with no executable check.

### Gaps
- No peer-reviewed measurement of cost savings for test-gated escalation in coding agents found; sources are practitioner posts.

## 5. Cost control: when to skip, reviewer strength, family, effort, output reliability

### Takeaway
Skip review where nothing changed or the answer is trivially checked; the evidence on judge model strength and reasoning effort is mixed (backbone matters, extra reasoning did not rescue false-success detection). Structured JSON verdicts need an explicit fallback for empty or malformed replies.

### Cited Findings
- Backbone upgrade is a better lever than elaborate judge pipelines (MobileJudgeBench). — [arXiv 2608.11434](https://arxiv.org/html/2608.11434v1)
- Reasoning-capable judges (DeepSeek-R1, o3-mini) gave no gain at false-success detection. — [arXiv 2606.09863](https://arxiv.org/html/2606.09863)
- Repeating the judgment K times and averaging, with finer score granularity, reduces ties and variance. — [LLM-as-a-Verifier](https://arxiv.org/html/2607.05391)
- Judge output failures: malformed JSON, truncated or repetitive output, refusals, and syntactically valid but uninformative JSON are recognised failure modes. — [Evaluating Reliability and Fidelity of Automated Judgment Systems, arXiv 2603.22214](https://arxiv.org/pdf/2603.22214) [snippet]
- Constrained decoding guarantees schema validity but not semantic correctness; one benchmark had unconstrained-plus-parsing at 93.63% vs constrained 91.37% on function calling. — [GMI Cloud blog](https://www.gmicloud.ai/en/blog/structured-output-for-llm-inference-json-schema-enforcement-constrained-decoding-and-parse-failure-rates) [low-confidence: vendor blog]
- Judge reliability should be reported alongside results; for reward signals, false-positive control matters more than overall accuracy. — [arXiv 2608.11434](https://arxiv.org/html/2608.11434v1)

### Inferences
- Treat an empty or unparseable reviewer reply as "unsure/error" with one retry, never as pass or fail, and log it.
- Skip review when the trail has no state-changing tool calls and the final answer makes no verifiable claim; this is design reasoning, not a measured result.
- Whether same-family vs cross-family judges matters for Claude reviewing Claude: self-preference is documented, but magnitude on agentic review is unmeasured in what I found.

### Gaps
- No controlled study found on reasoning-effort setting vs judge accuracy for agent trajectory review.
- No source on skip-review heuristics.

## 6. Prompting the reviewer: evidence packets, avoiding anchoring

### Takeaway
Evidence of what works is thin but consistent: give raw observations, not the agent's narration; force claim-by-claim checking; ask for both-sides reasoning and calibrated verdicts; allow "unsure".

### Cited Findings
- Agent reasoning and UI metadata added at most 0.3pp for mobile judges; a few high-fidelity observations beat many degraded ones. — [arXiv 2608.11434](https://arxiv.org/html/2608.11434v1)
- Judges anchor on the final state/last frame and on confident closing statements; surface-level matches are accepted as success. — [arXiv 2608.11434](https://arxiv.org/html/2608.11434v1), [arXiv 2606.09863](https://arxiv.org/html/2606.09863)
- Prompt components that helped calibration: explicit overconfidence warning and a structured "true because / false because" self-debate. — [arXiv 2609.10996](https://arxiv.org/html/2609.10996v1)
- Criteria decomposition (specification, output, errors) ensembled over repeats improved verification accuracy. — [LLM-as-a-Verifier](https://arxiv.org/html/2607.05391)
- Simple input representation yielded higher expert agreement in AgentRewardBench. — [alphaxiv summary](https://www.alphaxiv.org/abs/2504.08942) [snippet]

### Inferences
- Packet suggestion: task text, the list of extracted factual claims from the final answer (extracted mechanically or by the reviewer first), for each claim the supporting tool results verbatim, explicit "[trail clipped here]" markers. Present the worker's claim text last or separately so it does not anchor the verdict.
- Vague tasks: have the reviewer first state the acceptance criteria it infers and return "unsure" when criteria are not recoverable, rather than failing; this addresses your observed vague-task failures (design suggestion, unmeasured).

### Gaps
- No ablation found on claim-first vs answer-first ordering; no study on evidence-packet clipping.

## Source quality summary
- Strong, peer-reviewed or foundational: Huang et al. 2310.01798; Kamoi et al. TACL; Panickssery NeurIPS 2024; Self-Refine; CRITIC; Agent-as-a-Judge (ICML 2025).
- Recent preprints found through search and fetched (numbers from fetch summaries): 2606.09863, 2608.11434, 2609.10996, 2607.05391.
- Weak or unverified: 2609.00038, 2609.20812, 2609.02246 (quantitative claims), practitioner blogs on cascades and structured output.
