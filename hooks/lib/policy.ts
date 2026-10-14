import type { Effort, Policy, RunState, Tier } from '../../types'

const EFFORTS: Effort[] = ['low', 'medium', 'high', 'xhigh', 'max']

/**
 * Review cascade: work is judged by a heavier tier than the heaviest one that
 * produced it, and never lighter than the policy's reviewerTier. Work done on
 * the oracle can only be reviewed by the oracle.
 */
/** The heaviest rung a task has run a step on; `prev` may be missing in a run stored by an older version. */
export const peakAfter = (prev: number | undefined, ranOn: number): number => Math.max(prev ?? 0, ranOn)

export function pickReviewer(peakTier: number, p: Policy): number {
  const top = p.tiers.length - 1
  return Math.min(top, Math.max(p.review.reviewerTier, peakTier + 1))
}

/**
 * turn.step names the model verbatim; unlike $.model.complete it is not
 * documented to resolve aliases, so tiers hold full ids. Aliases typed in the
 * pane or found in an older stored policy are mapped here.
 */
export const ALIASES: Record<string, string> = {
  haiku: 'claude-haiku-4-5-20251001',
  sonnet: 'claude-sonnet-5-5',
  opus: 'claude-opus-5-5',
}

export const resolveModel = (m: string): string => ALIASES[m.trim().toLowerCase()] ?? m.trim()

// Rung ids are roles on the ladder; the model and effort say what runs there.
// claude-haiku-4-5 is sent no effort at all (session transcripts record perTurnEffort as
// null for it, and low/high for sonnet), so a haiku rung's effort is only a label and two
// haiku rungs would be the same request. Each real preset has at most one.
export const TIERS_FRUGAL: Tier[] = [
  { id: 'scout', model: ALIASES.haiku!, effort: 'max' },
  { id: 'worker', model: ALIASES.sonnet!, effort: 'low' },
  { id: 'senior', model: ALIASES.sonnet!, effort: 'high' },
  { id: 'oracle', model: ALIASES.opus!, effort: 'low' },
]

export const TIERS_BALANCED: Tier[] = [
  { id: 'scout', model: ALIASES.sonnet!, effort: 'low' },
  { id: 'worker', model: ALIASES.sonnet!, effort: 'high' },
  { id: 'senior', model: ALIASES.sonnet!, effort: 'max' },
  { id: 'oracle', model: ALIASES.opus!, effort: 'high' },
]

/** The original ladder, kept for `cautious`, which starts on its third rung. */
export const TIERS_CAUTIOUS: Tier[] = [
  { id: 'scout', model: ALIASES.haiku!, effort: 'low' },
  { id: 'worker', model: ALIASES.sonnet!, effort: 'medium' },
  { id: 'senior', model: ALIASES.sonnet!, effort: 'high' },
  { id: 'oracle', model: ALIASES.opus!, effort: 'max' },
]

/** Two haiku rungs on purpose, to measure what effort changes on a model. Not a ladder to run. */
export const TIERS_EFFORT_TEST: Tier[] = [
  { id: 'haiku-low', model: ALIASES.haiku!, effort: 'low' },
  { id: 'haiku-high', model: ALIASES.haiku!, effort: 'high' },
  { id: 'sonnet-low', model: ALIASES.sonnet!, effort: 'low' },
  { id: 'sonnet-high', model: ALIASES.sonnet!, effort: 'high' },
]

export const PRESETS: Record<string, Policy> = {
  frugal: {
    tiers: TIERS_FRUGAL,
    baseTier: 0,
    confidenceThreshold: 0.5,
    maxStepsPerTier: 25,
    errorStreak: 4,
    cooldownSteps: 4,
    maxEscalationsPerTask: 3,
    maxStepsPerTask: 150,
    loop: { repeat: 3, pingPong: 3, sameError: 3 },
    review: { mode: 'task', reviewerTier: 2, minToolCalls: 3, maxRounds: 1 },
  },
  balanced: {
    tiers: TIERS_BALANCED,
    baseTier: 0,
    confidenceThreshold: 0.6,
    maxStepsPerTier: 20,
    errorStreak: 3,
    cooldownSteps: 5,
    maxEscalationsPerTask: 4,
    maxStepsPerTask: 200,
    loop: { repeat: 3, pingPong: 3, sameError: 3 },
    review: { mode: 'both', reviewerTier: 3, minToolCalls: 3, maxRounds: 2 },
  },
  cautious: {
    tiers: TIERS_CAUTIOUS,
    baseTier: 2,
    confidenceThreshold: 0.75,
    maxStepsPerTier: 15,
    errorStreak: 2,
    cooldownSteps: 8,
    maxEscalationsPerTask: 6,
    maxStepsPerTask: 250,
    loop: { repeat: 2, pingPong: 2, sameError: 2 },
    review: { mode: 'both', reviewerTier: 3, minToolCalls: 1, maxRounds: 3 },
  },
  // For measurement only: frugal's settings on the two-haiku, two-sonnet effort-test rungs.
  efforttest: {
    tiers: TIERS_EFFORT_TEST,
    baseTier: 0,
    confidenceThreshold: 0.5,
    maxStepsPerTier: 25,
    errorStreak: 4,
    cooldownSteps: 4,
    maxEscalationsPerTask: 3,
    maxStepsPerTask: 150,
    loop: { repeat: 3, pingPong: 3, sameError: 3 },
    review: { mode: 'task', reviewerTier: 2, minToolCalls: 3, maxRounds: 1 },
  },
}

export const DEFAULT_PRESET = 'balanced'

/** Keeps a stored policy usable: fills gaps from the preset, clamps indexes. */
export function normalizePolicy(raw: unknown): Policy {
  const base = PRESETS[DEFAULT_PRESET]!
  const p = (raw && typeof raw === 'object' ? raw : {}) as Partial<Policy>
  // Repair each tier: a stored policy with a missing model or a bad effort would
  // otherwise crash session.start or get every request rejected.
  const repaired = (Array.isArray(p.tiers) ? p.tiers : []).flatMap((t, i): Tier[] => {
    if (!t || typeof t !== 'object' || typeof t.model !== 'string' || !t.model.trim()) return []
    const effort = EFFORTS.includes(t.effort) ? t.effort : 'medium'
    return [{ id: typeof t.id === 'string' && t.id ? t.id : `tier${i}`, model: resolveModel(t.model), effort }]
  })
  const tiers = repaired.length >= 2 ? repaired : base.tiers.map(t => ({ ...t }))
  const top = tiers.length - 1
  const clamp = (n: unknown, lo: number, hi: number, d: number) =>
    typeof n === 'number' && Number.isFinite(n) ? Math.round(Math.min(hi, Math.max(lo, n))) : d
  const clampFrac = (n: unknown, lo: number, hi: number, d: number) =>
    typeof n === 'number' && Number.isFinite(n) ? Math.min(hi, Math.max(lo, n)) : d
  return {
    tiers,
    baseTier: clamp(p.baseTier, 0, top, base.baseTier),
    confidenceThreshold: clampFrac(p.confidenceThreshold, 0, 1, base.confidenceThreshold),
    maxStepsPerTier: clamp(p.maxStepsPerTier, 1, 1000, base.maxStepsPerTier),
    errorStreak: clamp(p.errorStreak, 1, 50, base.errorStreak),
    cooldownSteps: clamp(p.cooldownSteps, 1, 100, base.cooldownSteps),
    maxEscalationsPerTask: clamp(p.maxEscalationsPerTask, 0, 20, base.maxEscalationsPerTask),
    maxStepsPerTask: clamp(p.maxStepsPerTask, 5, 2000, base.maxStepsPerTask),
    loop: {
      repeat: clamp(p.loop?.repeat, 2, 20, base.loop.repeat),
      // the detector's ring holds 26 calls and ping-pong needs 2 per repeat
      pingPong: clamp(p.loop?.pingPong, 2, 12, base.loop.pingPong),
      sameError: clamp(p.loop?.sameError, 2, 20, base.loop.sameError),
    },
    review: {
      mode: (['off', 'task', 'milestone', 'both'] as const).includes(p.review?.mode as never)
        ? p.review!.mode
        : base.review.mode,
      reviewerTier: clamp(p.review?.reviewerTier, 0, top, base.review.reviewerTier),
      minToolCalls: clamp(p.review?.minToolCalls, 0, 100, base.review.minToolCalls),
      maxRounds: clamp(p.review?.maxRounds, 0, 10, base.review.maxRounds),
    },
  }
}

/**
 * Only a person's (or a schedule's) new request starts a new task. Notifications,
 * peer/subagent hand-backs, relays and the ladder's own follow-ups continue the
 * task in flight, so they must not clear loop strikes, the breaker or review rounds.
 *
 * A new task keeps the pin and the pinned rung (see the reset in register.tsx), so a test
 * that pins a rung and sends several prompts needs no special mode.
 */
const NEW_TASK_ORIGINS = ['composer', 'bridge', 'sdk', 'channel', 'slack-ping', 'auto-continuation', 'scheduled-trigger']

export const startsNewTask = (originKind: string): boolean => NEW_TASK_ORIGINS.includes(originKind)

/**
 * US dollars per million tokens. Sources: the claude-api reference's model table (2026-10-06 cache)
 * for input, output and sonnet/opus cache reads. Verified against a real `claude -p` bill
 * (sonnet-5-5, 2026-10-13, matched to $0.0001): input $2, output $10, 1-hour cache write 2x input,
 * which is what Claude Code uses. Not verified: haiku-4-5's cache read (assumed 0.1x input) and
 * the 1-hour write multiplier on haiku and opus (assumed 2x, as on sonnet).
 * Effort has no price of its own: it only changes how many tokens the model generates.
 * Unknown models cost 0 and are reported as such rather than guessed.
 */
export type Price = { input: number; output: number; cacheRead: number; cacheWrite: number }
const price = (input: number, output: number, cacheRead: number, writeMult = 2): Price => ({ input, output, cacheRead, cacheWrite: input * writeMult })
export const PRICES: Record<string, Price> = {
  'claude-haiku-4-5': price(1, 5, 0.1),
  'claude-sonnet-5-5': price(2, 10, 0.2),
  'claude-opus-5-5': price(4, 20, 0.2),
}

/** Price for a model id, matching a dated id (claude-haiku-4-5-20251001) to its family entry. */
export function priceFor(model: string): Price | undefined {
  return PRICES[model] ?? PRICES[model.replace(/-\d{8}$/, '')]
}

export type TokenCounts = { input: number; output: number; cacheRead: number; cacheWrite?: number }

/** Estimated dollars for token counts on a model; undefined when the model has no price entry. */
export function estimateCost(model: string, t: TokenCounts): number | undefined {
  const p = priceFor(model)
  if (!p) return undefined
  return (t.input * p.input + t.output * p.output + t.cacheRead * p.cacheRead + (t.cacheWrite ?? 0) * p.cacheWrite) / 1_000_000
}

export function freshRun(policy: Policy, enabled = true): RunState {
  return {
    enabled,
    tier: policy.baseTier,
    peakTier: policy.baseTier,
    reviewedToolCalls: 0,
    escalationRequests: 0,
    consults: 0,
    pinned: false,
    turnId: null,
    stepsOnTier: 0,
    stepsInTask: 0,
    toolCallsInTask: 0,
    escalations: 0,
    cleanSteps: 0,
    errorStreak: 0,
    loopStrikes: 0,
    reviewRounds: 0,
    isBroken: false,
    spend: {},
    lastLoop: null,
  }
}
