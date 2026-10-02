import type { Policy, RunState } from '../../types'

export type Signal =
  | { kind: 'model-request'; confidence: number; ask: 'stuck' | 'deeper-reasoning' | 'high-stakes'; reason: string }
  | { kind: 'loop'; detail: string }
  | { kind: 'error-streak'; n: number }
  | { kind: 'step-budget'; steps: number }
  | { kind: 'truncated' }
  | { kind: 'refusal' }
  | { kind: 'review-failed'; issues: string }

export type Move =
  | { op: 'up'; to: number; reason: string }
  | { op: 'hold'; reason: string }
  | { op: 'trip'; reason: string }

const top = (p: Policy) => p.tiers.length - 1

/**
 * One signal in, one move out. Pure, so the whole escalation policy is a
 * table that can be unit-tested without a session.
 *
 * `trip` is the circuit breaker: at the top tier (or out of escalation
 * budget) a signal that would have escalated has nowhere to go, and the
 * caller must stop the run rather than spin.
 */
export function decide(sig: Signal, run: RunState, p: Policy): Move {
  if (run.pinned) return { op: 'hold', reason: 'tier pinned by the user' }

  const atTop = run.tier >= top(p)
  const outOfBudget = run.escalations >= p.maxEscalationsPerTask

  let want: number | null = null
  let why = ''

  switch (sig.kind) {
    case 'model-request':
      if (sig.ask !== 'deeper-reasoning' && sig.confidence >= p.confidenceThreshold) {
        return {
          op: 'hold',
          reason: `confidence ${sig.confidence.toFixed(2)} >= ${p.confidenceThreshold}`,
        }
      }
      // "deeper reasoning" and "high stakes" skip the rungs: the cheap
      // tiers were never going to supply it.
      want = sig.ask === 'stuck' ? run.tier + 1 : top(p)
      why = `model asked (${sig.ask}, confidence ${sig.confidence.toFixed(2)}): ${sig.reason}`
      break
    case 'loop':
      want = run.tier + 1
      why = `loop: ${sig.detail}`
      break
    case 'error-streak':
      want = run.tier + 1
      why = `${sig.n} tool errors in a row`
      break
    case 'step-budget':
      want = run.tier + 1
      why = `${sig.steps} steps on this tier without finishing`
      break
    case 'truncated':
      want = run.tier + 1
      why = 'response hit max_tokens'
      break
    case 'refusal':
      want = run.tier + 1
      why = 'model refused'
      break
    case 'review-failed':
      want = run.tier + 1
      why = `review failed: ${sig.issues.slice(0, 120)}`
      break
  }

  if (want === null) return { op: 'hold', reason: 'no rule matched' }
  const to = Math.min(want, top(p))

  if (to <= run.tier || outOfBudget) {
    // Nowhere to go. A model's own request or a failed review at the top is
    // just information; a loop/stall at the top is a reason to stop.
    if (sig.kind === 'model-request' || sig.kind === 'review-failed') {
      return { op: 'hold', reason: atTop ? 'already at oracle' : 'escalation budget spent' }
    }
    return {
      op: 'trip',
      reason: atTop
        ? `${why}; already at the top tier`
        : `${why}; escalation budget (${p.maxEscalationsPerTask}) spent`,
    }
  }
  return { op: 'up', to, reason: why }
}

/** After a clean step: has the escalated tier earned its way back down? */
export function shouldStepDown(run: RunState, p: Policy): boolean {
  return !run.pinned && run.tier > p.baseTier && run.cleanSteps >= p.cooldownSteps
}
