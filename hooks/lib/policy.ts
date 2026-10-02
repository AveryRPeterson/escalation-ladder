import type { Policy, RunState, Tier } from '../../types'

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

export const TIERS_BALANCED: Tier[] = [
  { id: 'scout', model: ALIASES.haiku!, effort: 'low' },
  { id: 'worker', model: ALIASES.sonnet!, effort: 'medium' },
  { id: 'senior', model: ALIASES.sonnet!, effort: 'high' },
  { id: 'oracle', model: ALIASES.opus!, effort: 'max' },
]

export const PRESETS: Record<string, Policy> = {
  frugal: {
    tiers: TIERS_BALANCED,
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
    baseTier: 1,
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
    tiers: TIERS_BALANCED,
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
}

export const DEFAULT_PRESET = 'balanced'

/** Keeps a stored policy usable: fills gaps from the preset, clamps indexes. */
export function normalizePolicy(raw: unknown): Policy {
  const base = PRESETS[DEFAULT_PRESET]!
  const p = (raw && typeof raw === 'object' ? raw : {}) as Partial<Policy>
  const tiers = (Array.isArray(p.tiers) && p.tiers.length >= 2 ? p.tiers : base.tiers).map(t => ({
    ...t,
    model: resolveModel(t.model),
  }))
  const top = tiers.length - 1
  const clamp = (n: unknown, lo: number, hi: number, d: number) =>
    typeof n === 'number' && Number.isFinite(n) ? Math.min(hi, Math.max(lo, n)) : d
  return {
    tiers,
    baseTier: clamp(p.baseTier, 0, top, base.baseTier),
    confidenceThreshold: clamp(p.confidenceThreshold, 0, 1, base.confidenceThreshold),
    maxStepsPerTier: clamp(p.maxStepsPerTier, 1, 1000, base.maxStepsPerTier),
    errorStreak: clamp(p.errorStreak, 1, 50, base.errorStreak),
    cooldownSteps: clamp(p.cooldownSteps, 1, 100, base.cooldownSteps),
    maxEscalationsPerTask: clamp(p.maxEscalationsPerTask, 0, 20, base.maxEscalationsPerTask),
    maxStepsPerTask: clamp(p.maxStepsPerTask, 5, 2000, base.maxStepsPerTask),
    loop: {
      repeat: clamp(p.loop?.repeat, 2, 20, base.loop.repeat),
      pingPong: clamp(p.loop?.pingPong, 2, 20, base.loop.pingPong),
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

export function freshRun(policy: Policy, enabled = true): RunState {
  return {
    enabled,
    tier: policy.baseTier,
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
