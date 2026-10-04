import { expect, mock, test } from 'claude-code/testing'

test('/ladder log reports an empty log, then the events a manual move records', async ($, on) => {
  mock.clock(on, { now: Date.UTC(2026, 9, 2, 18, 30, 5) })
  on('ui.status', () => undefined as never)

  const empty = await $.command.run({ command: 'ladder', args: 'log', origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 80 } })
  expect(empty.text).toBe('No events yet.')

  await $.command.run({ command: 'ladder', args: 'up', origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 80 } })
  const out = await $.command.run({ command: 'ladder', args: 'log', origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 80 } })
  expect(out.text).toContain('Recent events:')
  expect(out.text).toMatch(/2026-10-02 18:30:05 manual\s+\d→\d manual/)
  expect(out.text).toContain('Task status:')
})
