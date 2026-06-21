import type { MoveProposal, CalendarEvent } from '../../api/types'

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString('de-DE', { weekday: 'short', day: '2-digit', month: '2-digit' })
}

const FLEXIBILITY_COLORS: Record<string, string> = {
  fixed: 'text-red-600 dark:text-red-400',
  likely_fixed: 'text-orange-600 dark:text-orange-400',
  uncertain: 'text-yellow-600 dark:text-yellow-400',
  likely_flexible: 'text-green-600 dark:text-green-400',
  flexible: 'text-emerald-600 dark:text-emerald-400',
}

interface ProposalRowProps {
  proposal: MoveProposal
  event?: CalendarEvent
}

export function ProposalRow({ proposal, event }: ProposalRowProps) {
  const title = event?.title || proposal.event_id
  const oldTime = event
    ? `${formatDate(event.start)} ${formatTime(event.start)}–${formatTime(event.end)}`
    : '—'
  const newTime = `${formatDate(proposal.new_start)} ${formatTime(proposal.new_start)}–${formatTime(proposal.new_end)}`

  return (
    <tr className="border-t border-slate-100 dark:border-slate-700">
      <td className="py-2 px-3 text-sm font-medium text-slate-800 dark:text-slate-200">{title}</td>
      <td className="py-2 px-3 text-sm text-slate-600 dark:text-slate-400">{oldTime}</td>
      <td className="py-2 px-3 text-sm text-slate-600 dark:text-slate-400">{newTime}</td>
      <td className={`py-2 px-3 text-sm ${FLEXIBILITY_COLORS[proposal.flexibility] || ''}`}>
        {proposal.flexibility} ({Math.round(proposal.confidence * 100)}%)
      </td>
      <td className="py-2 px-3 text-sm text-slate-500 dark:text-slate-400">{proposal.reason}</td>
    </tr>
  )
}
