import type { CalendarEvent } from '../../api/types'
import { EventBlock } from './EventBlock'

const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

interface DayColumnProps {
  date: string
  dayIndex: number
  events: CalendarEvent[]
  proposedEvents?: CalendarEvent[]
  dayStart: number
  dayEnd: number
  allDayEvents?: CalendarEvent[]
}

export function DayColumn({
  date,
  dayIndex,
  events,
  proposedEvents = [],
  dayStart,
  dayEnd,
  allDayEvents = [],
}: DayColumnProps) {
  const hours = []
  for (let h = dayStart; h <= dayEnd; h++) {
    hours.push(h)
  }

  const d = new Date(date + 'T00:00:00')
  const dayNum = d.getDate()
  const monthNum = d.getMonth() + 1

  return (
    <div className="flex-1 min-w-0">
      <div className="text-center py-2 border-b border-slate-200 dark:border-slate-700">
        <div className="text-xs font-medium text-slate-500 dark:text-slate-400">
          {DAY_NAMES[dayIndex]}
        </div>
        <div className="text-sm font-bold text-slate-800 dark:text-slate-200">
          {dayNum}.{monthNum}
        </div>
      </div>

      {allDayEvents.length > 0 && (
        <div className="px-1 py-1 border-b border-slate-200 dark:border-slate-700">
          {allDayEvents.map((e) => (
            <div
              key={e.id}
              className="text-xs px-2 py-0.5 rounded bg-amber-100 border border-amber-300 text-amber-900 dark:bg-amber-900/40 dark:border-amber-700 dark:text-amber-200 truncate mb-0.5"
              title={e.title}
            >
              {e.title}
            </div>
          ))}
        </div>
      )}

      <div className="relative" style={{ height: `${(dayEnd - dayStart) * 48}px` }}>
        {hours.map((h) => {
          const top = ((h - dayStart) / (dayEnd - dayStart)) * 100
          return (
            <div
              key={h}
              className="absolute left-0 right-0 border-t border-slate-100 dark:border-slate-800"
              style={{ top: `${top}%` }}
            />
          )
        })}

        {events
          .filter((e) => !e.all_day)
          .map((e) => (
            <EventBlock key={e.id} event={e} dayStart={dayStart} dayEnd={dayEnd} />
          ))}

        {proposedEvents.map((e) => (
          <EventBlock
            key={`proposed-${e.id}`}
            event={e}
            dayStart={dayStart}
            dayEnd={dayEnd}
            variant="proposed"
          />
        ))}
      </div>
    </div>
  )
}
