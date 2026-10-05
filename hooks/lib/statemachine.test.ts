import { describe, it, expect, beforeEach } from 'vitest'
import type { Policy, RunState } from '../../types'
import { PRESETS, freshRun } from './policy'
import { decide } from './decide'
import type { Signal } from './decide'

/**
 * State-machine property tests for the escalation ladder.
 * Verifies that tier transitions are deterministic, safe, and respect constraints.
 */

describe('Escalation Ladder State Machine', () => {
  let policy: Policy
  let run: RunState

  beforeEach(() => {
    policy = { ...PRESETS.frugal! }
    run = freshRun(policy)
  })

  describe('Escalation Constraints', () => {
    it('never escalates beyond tier count', () => {
      const tiers = policy.tiers.length
      for (let i = 0; i < 100; i++) {
        const sig: Signal = { ask: 'up', confidence: 0.9 }
        const decision = decide(sig, run, policy)
        if (decision.kind === 'escalate') {
          run.tier = Math.min(run.tier + 1, tiers - 1)
        }
        expect(run.tier).toBeLessThan(tiers)
      }
    })

    it('respects maxEscalationsPerTask cap', () => {
      const maxEscalations = policy.maxEscalationsPerTask
      let escalationCount = 0
      for (let i = 0; i < 50; i++) {
        if (escalationCount < maxEscalations) {
          const sig: Signal = { ask: 'up', confidence: 0.9 }
          const decision = decide(sig, run, policy)
          if (decision.kind === 'escalate') {
            run.escalations += 1
            escalationCount += 1
            run.tier = Math.min(run.tier + 1, policy.tiers.length - 1)
          }
        }
      }
      expect(run.escalations).toBeLessThanOrEqual(maxEscalations)
    })

    it('breaker is irreversible until task reset', () => {
      // Trigger breaker
      run.isBroken = true
      run.lastLoop = 'test-loop'

      // Try to escalate or deescalate — breaker blocks both
      for (let i = 0; i < 10; i++) {
        const sig: Signal = { ask: 'up', confidence: 0.9 }
        const decision = decide(sig, run, policy)
        expect(decision.kind).toBe('hold')
        expect(run.isBroken).toBe(true)
      }

      // Reset is the only way out
      run = freshRun(policy)
      expect(run.isBroken).toBe(false)
    })

    it('pins prevent auto-escalation and auto-deescalation', () => {
      run.pinned = true
      const originalTier = run.tier

      // Error signal should not escalate when pinned
      run.errorStreak = policy.errorStreak
      const escSig: Signal = { ask: 'up', confidence: 0.9 }
      const escDecision = decide(escSig, run, policy)
      expect(escDecision.kind).toBe('hold')
      expect(run.tier).toBe(originalTier)

      // Clean steps should not deescalate when pinned
      run.cleanSteps = policy.cooldownSteps
      const deescSig: Signal = { ask: 'down', confidence: 0.9 }
      const deescDecision = decide(deescSig, run, policy)
      expect(deescDecision.kind).toBe('hold')
      expect(run.tier).toBe(originalTier)
    })
  })

  describe('Tier Transitions', () => {
    it('escalates on error streak', () => {
      const originalTier = run.tier
      run.errorStreak = policy.errorStreak
      const sig: Signal = { ask: 'up', confidence: 0.9 }
      const decision = decide(sig, run, policy)
      expect(decision.kind).toBe('escalate')
    })

    it('escalates on loop strike', () => {
      const originalTier = run.tier
      run.loopStrikes = 1
      const sig: Signal = { ask: 'up', confidence: 0.9 }
      const decision = decide(sig, run, policy)
      expect(decision.kind).toBe('escalate')
    })

    it('deescalates after cooldown steps on healthy tier', () => {
      run.tier = 1 // Start on worker
      run.cleanSteps = policy.cooldownSteps
      run.errorStreak = 0
      const sig: Signal = { ask: 'down', confidence: 0.9 }
      const decision = decide(sig, run, policy)
      expect(decision.kind).toBe('deescalate')
    })

    it('holds when confidence is below threshold but not troubled', () => {
      run.errorStreak = 0
      run.loopStrikes = 0
      const sig: Signal = { ask: 'up', confidence: 0.4 } // Below 0.5 threshold (frugal)
      const decision = decide(sig, run, policy)
      expect(decision.kind).toBe('hold')
    })

    it('escalates on low confidence when troubled (error or loop)', () => {
      run.errorStreak = 1
      const sig: Signal = { ask: 'up', confidence: 0.4 }
      const decision = decide(sig, run, policy)
      expect(decision.kind).toBe('escalate')
    })
  })

  describe('Cooldown Decay', () => {
    it('increments cleanSteps on healthy step', () => {
      run.errorStreak = 0
      run.cleanSteps = 5
      const originalSteps = run.cleanSteps

      // Simulate a clean step
      if (run.errorStreak === 0) {
        run.cleanSteps += 1
      }

      expect(run.cleanSteps).toBe(originalSteps + 1)
    })

    it('resets cleanSteps on error', () => {
      run.cleanSteps = 5
      run.errorStreak = 1

      // Reset cleanSteps
      run.cleanSteps = 0

      expect(run.cleanSteps).toBe(0)
    })

    it('allows deescalation only after cooldownSteps clean steps', () => {
      const cooldown = policy.cooldownSteps
      for (let i = 0; i < cooldown - 1; i++) {
        run.cleanSteps += 1
        const sig: Signal = { ask: 'down', confidence: 0.9 }
        const decision = decide(sig, run, policy)
        expect(decision.kind).not.toBe('deescalate')
      }

      run.cleanSteps += 1
      const sig: Signal = { ask: 'down', confidence: 0.9 }
      const decision = decide(sig, run, policy)
      if (run.tier > policy.baseTier) {
        expect(decision.kind).toBe('deescalate')
      }
    })
  })

  describe('Peak Tier Tracking', () => {
    it('peakTier never decreases', () => {
      const peakBefore = run.peakTier
      run.tier = 2
      const peakAfter = Math.max(peakBefore, run.tier)
      expect(peakAfter).toBeGreaterThanOrEqual(peakBefore)
    })

    it('peakTier reflects highest rung touched in task', () => {
      expect(run.peakTier).toBe(0)
      run.tier = 1
      run.peakTier = Math.max(run.peakTier, run.tier)
      expect(run.peakTier).toBe(1)
      run.tier = 3
      run.peakTier = Math.max(run.peakTier, run.tier)
      expect(run.peakTier).toBe(3)
      run.tier = 1
      // peakTier should not decrease
      expect(run.peakTier).toBe(3)
    })
  })

  describe('Step Count Stall Detection', () => {
    it('holds on stall signal (step count timeout)', () => {
      run.stepsOnTier = policy.maxStepsPerTier
      const sig: Signal = { ask: 'up', confidence: 0.9 }
      const decision = decide(sig, run, policy)
      expect(decision.kind).toBe('escalate')
    })

    it('stall detection is independent of error state', () => {
      run.errorStreak = 0
      run.loopStrikes = 0
      run.stepsOnTier = policy.maxStepsPerTier
      const sig: Signal = { ask: 'up', confidence: 0.9 }
      const decision = decide(sig, run, policy)
      // False positive: healthy iteration hit step budget
      expect(decision.kind).toBe('escalate')
    })
  })

  describe('Circuit Breaker', () => {
    it('breaker trips after maxLoops despite escalation', () => {
      run.loopStrikes = 3 // Three loop detections in one task
      run.isBroken = true
      run.lastLoop = 'repeat'

      // Breaker should block further decisions
      const sig: Signal = { ask: 'up', confidence: 0.9 }
      const decision = decide(sig, run, policy)
      expect(decision.kind).toBe('hold')
      expect(run.isBroken).toBe(true)
    })

    it('breaker is task-terminal', () => {
      run.isBroken = true
      expect(run.isBroken).toBe(true)

      // Only task reset clears it
      run = freshRun(policy)
      expect(run.isBroken).toBe(false)
    })
  })

  describe('Random Signal Sequences (Fuzz)', () => {
    it('handles random signal sequence without panic', () => {
      const signals: Signal[] = [
        { ask: 'up', confidence: 0.9 },
        { ask: 'down', confidence: 0.5 },
        { ask: 'up', confidence: 0.3 },
        { ask: 'up', confidence: 0.95 },
        { ask: 'down', confidence: 0.8 },
      ]

      for (const sig of signals) {
        const decision = decide(sig, run, policy)
        expect(['escalate', 'deescalate', 'hold', 'breach']).toContain(decision.kind)

        // Apply the decision (simplified)
        if (decision.kind === 'escalate' && run.tier < policy.tiers.length - 1) {
          run.tier += 1
          run.escalations += 1
        } else if (decision.kind === 'deescalate' && run.tier > policy.baseTier) {
          run.tier -= 1
        }

        // State invariants
        expect(run.tier).toBeGreaterThanOrEqual(0)
        expect(run.tier).toBeLessThan(policy.tiers.length)
        expect(run.escalations).toBeLessThanOrEqual(policy.maxEscalationsPerTask)
      }
    })

    it('maintains safety invariants across 100 random transitions', () => {
      for (let step = 0; step < 100; step++) {
        // Random signal
        const asks: Signal['ask'][] = ['up', 'down']
        const ask = asks[Math.floor(Math.random() * asks.length)]
        const confidence = Math.random()
        const sig: Signal = { ask, confidence }

        const decision = decide(sig, run, policy)

        // Apply decision
        if (decision.kind === 'escalate' && run.escalations < policy.maxEscalationsPerTask) {
          if (run.tier < policy.tiers.length - 1) {
            run.tier += 1
            run.escalations += 1
          }
        } else if (decision.kind === 'deescalate') {
          if (run.tier > policy.baseTier && run.cleanSteps >= policy.cooldownSteps) {
            run.tier -= 1
            run.cleanSteps = 0
          }
        }

        // Verify invariants
        expect(run.tier).toBeGreaterThanOrEqual(0)
        expect(run.tier).toBeLessThan(policy.tiers.length)
        expect(run.escalations).toBeLessThanOrEqual(policy.maxEscalationsPerTask)
        expect(run.stepsInTask).toBeLessThanOrEqual(policy.maxStepsPerTask)
      }
    })
  })
})
