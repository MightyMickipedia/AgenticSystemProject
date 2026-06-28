import { useMemo } from 'react'
import type { WeeklyCalendar, OptimizationVariant, CalendarEvent } from '../../api/types'
import { DayColumn } from './DayColumn'
import { TimeAxis } from './TimeAxis'

function parseTimeToHour(t: string): number {
  const [h] = t.split(':').map(Number)
  return h
}

function addDays(dateStr: string, days: number): string {
  const [y, m, d] = dateStr.split('-').map(Number)
  const dt = new Date(y, m - 1, d + days)
  return [
    dt.getFullYear(),
    String(dt.getMonth() + 1).padStart(2, '0'),
    String(dt.getDate()).padStart(2, '0'),
  ].join('-')
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
      const es = new Date(e.start).getTime()
      const ee = new Date(e.end).getTime()
      for (const d of days) {
        const [y, mo, dy] = d.split('-').map(Number)
        const ds = new Date(y, mo - 1, dy).getTime()
        const de = new Date(y, mo - 1, dy + 1).getTime()
        if (es < de && ee > ds) map[d].push(e)
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
      const ps = new Date(proposed.start).getTime()
      const pe = new Date(proposed.end).getTime()
      for (const d of days) {
        const [y, mo, dy] = d.split('-').map(Number)
        const ds = new Date(y, mo - 1, dy).getTime()
        const de = new Date(y, mo - 1, dy + 1).getTime()
        if (ps < de && pe > ds) map[d].push(proposed)
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
