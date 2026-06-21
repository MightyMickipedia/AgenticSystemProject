import { useMemo } from 'react'
import type { WeeklyCalendar, OptimizationVariant, CalendarEvent } from '../../api/types'
import { DayColumn } from './DayColumn'
import { TimeAxis } from './TimeAxis'

function parseTimeToHour(t: string): number {
  const [h] = t.split(':').map(Number)
  return h
}

function addDays(dateStr: string, days: number): string {
  const d = new Date(dateStr + 'T00:00:00')
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

interface WeekTimelineProps {
  calendar: WeeklyCalendar
  variant?: OptimizationVariant | null
}

export function WeekTimeline({ calendar, variant }: WeekTimelineProps) {
  const dayStart = parseTimeToHour(calendar.day_start)
  const dayEnd = parseTimeToHour(calendar.day_end)

  const days = useMemo(() => {
    return Array.from({ length: 7 }, (_, i) => addDays(calendar.week_start, i))
  }, [calendar.week_start])

  const eventsByDay = useMemo(() => {
    const map: Record<string, CalendarEvent[]> = {}
    for (const d of days) map[d] = []
    for (const e of calendar.events) {
      for (const d of days) {
        const dayStart = d + 'T00:00:00'
        const dayEnd = addDays(d, 1) + 'T00:00:00'
        if (e.start < dayEnd && e.end > dayStart) {
          map[d].push(e)
        }
      }
    }
    return map
  }, [calendar.events, days])

  const proposedByDay = useMemo(() => {
    const map: Record<string, CalendarEvent[]> = {}
    for (const d of days) map[d] = []
    if (!variant) return map

    for (const p of variant.proposals) {
      const original = calendar.events.find((e) => e.id === p.event_id)
      if (!original) continue
      const proposed: CalendarEvent = {
        ...original,
        start: p.new_start,
        end: p.new_end,
      }
      for (const d of days) {
        const dayStartStr = d + 'T00:00:00'
        const dayEndStr = addDays(d, 1) + 'T00:00:00'
        if (proposed.start < dayEndStr && proposed.end > dayStartStr) {
          map[d].push(proposed)
        }
      }
    }
    return map
  }, [variant, calendar.events, days])

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden">
      <div className="flex">
        <TimeAxis dayStart={dayStart} dayEnd={dayEnd} />
        <div className="flex flex-1 divide-x divide-slate-200 dark:divide-slate-700">
          {days.map((d, i) => (
            <DayColumn
              key={d}
              date={d}
              dayIndex={i}
              events={eventsByDay[d] || []}
              proposedEvents={proposedByDay[d] || []}
              dayStart={dayStart}
              dayEnd={dayEnd}
              allDayEvents={(eventsByDay[d] || []).filter((e) => e.all_day)}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
