export type Verdict = { verdict: 'pass' | 'fail' | 'unsure'; issues: string[] }

export const REVIEW_SYSTEM = [
  'You are an independent reviewer of work done by another AI coding agent.',
  'You did not do the work and have no stake in it. Be skeptical but fair.',
  'Judge ONLY from the evidence given: the task, the tool calls with their outcomes, and the final answer.',
  'Fail the work if: the task was not actually completed; the answer claims something no tool call supports;',
  'a test/build/check was never run or was run and failed; errors were ignored; or the answer silently narrowed the task.',
  'Reply with ONE JSON object and nothing else:',
  '{"verdict":"pass"|"fail"|"unsure","issues":["short, concrete, actionable"]}',
].join(' ')

type Row = {
  role: 'user' | 'assistant'
  text: string
  toolUses: { tool: string; input: Record<string, unknown>; text?: string; isError?: boolean }[]
}

const clip = (s: string, n: number) => (s.length > n ? `${s.slice(0, n)}…[+${s.length - n}]` : s)

/** A bounded evidence packet: the task, the tool trail, the final answer. */
export function buildEvidence(rows: readonly Row[], scope: 'task' | 'milestone', note?: string): string {
  // The task is the last user row that is not a tool_result carrier.
  let start = 0
  for (let i = rows.length - 1; i >= 0; i--) {
    if (rows[i]!.role === 'user' && rows[i]!.text.trim()) {
      start = i
      break
    }
  }
  const slice = rows.slice(start)
  const task = slice[0]?.text ?? '(unknown)'
  const trail: string[] = []
  let answer = ''
  for (const r of slice) {
    if (r.role !== 'assistant') continue
    if (r.text.trim()) answer = r.text
    for (const t of r.toolUses) {
      const arg = clip(JSON.stringify(t.input), 160)
      const out = t.text ? clip(t.text.replace(/\s+/g, ' '), 200) : '(no result)'
      trail.push(`- ${t.tool} ${arg} -> ${t.isError ? 'ERROR ' : ''}${out}`)
    }
  }
  return [
    `SCOPE: ${scope}${note ? ` (${note})` : ''}`,
    `TASK:\n${clip(task, 1500)}`,
    `TOOL TRAIL (${trail.length} calls${trail.length > 40 ? ', last 40 shown' : ''}):\n${trail.slice(-40).join('\n')}`,
    `FINAL ANSWER:\n${clip(answer, 2500) || '(none)'}`,
  ].join('\n\n')
}

export function parseVerdict(text: string): Verdict {
  const m = text.match(/\{[\s\S]*\}/)
  if (m) {
    try {
      const j = JSON.parse(m[0]) as Partial<Verdict>
      const v = j.verdict === 'pass' || j.verdict === 'fail' ? j.verdict : 'unsure'
      return { verdict: v, issues: Array.isArray(j.issues) ? j.issues.map(String).slice(0, 8) : [] }
    } catch {
      /* fall through */
    }
  }
  return { verdict: 'unsure', issues: ['reviewer reply was not valid JSON'] }
}
