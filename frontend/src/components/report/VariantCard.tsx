import type { OptimizationVariant, CalendarEvent } from '../../api/types'
import { ProposalRow } from './ProposalRow'

interface VariantCardProps {
  variant: OptimizationVariant
  events: CalendarEvent[]
  isRecommended?: boolean
}

export function VariantCard({ variant, events, isRecommended = false }: VariantCardProps) {
  const findEvent = (id: string) => events.find((e) => e.id === id)

  return (
    <div
      className={`rounded-lg border p-4 ${
        isRecommended
          ? 'border-blue-300 dark:border-blue-700 bg-blue-50/50 dark:bg-blue-900/10'
          : 'border-slate-200 dark:border-slate-700'
      }`}
    >
      <div className="flex items-center gap-2 mb-2">
        <h3 className="text-base font-semibold text-slate-900 dark:text-white">
          {variant.name}
        </h3>
        {isRecommended && (
          <span className="px-2 py-0.5 text-xs font-medium bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded-full">
            Recommended
          </span>
        )}
      </div>
      <p className="text-sm text-slate-600 dark:text-slate-400 mb-3">{variant.summary}</p>

      {variant.proposals.length === 0 ? (
        <p className="text-sm text-slate-400 italic">No move proposals.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="text-xs text-slate-500 dark:text-slate-400 uppercase">
                <th className="py-2 px-3 font-medium">Event</th>
                <th className="py-2 px-3 font-medium">Current</th>
                <th className="py-2 px-3 font-medium">Proposed</th>
                <th className="py-2 px-3 font-medium">Flexibility</th>
                <th className="py-2 px-3 font-medium">Reason</th>
              </tr>
            </thead>
            <tbody>
              {variant.proposals.map((p) => (
                <ProposalRow key={p.event_id} proposal={p} event={findEvent(p.event_id)} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
