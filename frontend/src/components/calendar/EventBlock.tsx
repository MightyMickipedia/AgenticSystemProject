import type { CalendarEvent } from '../../api/types'

const COLORS: Record<string, string> = {
  default: 'bg-blue-100 border-blue-300 text-blue-900 dark:bg-blue-900/40 dark:border-blue-700 dark:text-blue-200',
  allDay: 'bg-amber-100 border-amber-300 text-amber-900 dark:bg-amber-900/40 dark:border-amber-700 dark:text-amber-200',
  virtual: 'bg-green-100 border-green-300 text-green-900 dark:bg-green-900/40 dark:border-green-700 dark:text-green-200',
  proposed: 'bg-purple-100 border-purple-300 text-purple-900 dark:bg-purple-900/40 dark:border-purple-700 dark:text-purple-200 border-dashed opacity-75',
}

function isVirtual(location: string): boolean {
  const l = location.toLowerCase()
  return ['zoom', 'meet', 'teams', 'online', 'virtual'].some((t) => l.includes(t))
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
}

interface EventBlockProps {
  event: CalendarEvent
  dayStart: number
  dayEnd: number
  variant?: 'default' | 'proposed'
}

export function EventBlock({ event, dayStart, dayEnd, variant = 'default' }: EventBlockProps) {
  if (event.all_day) return null

  const start = new Date(event.start)
  const end = new Date(event.end)
  const startMinutes = start.getHours() * 60 + start.getMinutes()
  const endMinutes = end.getHours() * 60 + end.getMinutes()
  const totalMinutes = (dayEnd - dayStart) * 60

  const top = ((startMinutes - dayStart * 60) / totalMinutes) * 100
  const height = ((endMinutes - startMinutes) / totalMinutes) * 100

  const colorClass =
    variant === 'proposed'
      ? COLORS.proposed
      : isVirtual(event.location)
        ? COLORS.virtual
        : COLORS.default

  return (
    <div
      className={`absolute left-1 right-1 rounded-md border px-2 py-1 text-xs overflow-hidden cursor-default ${colorClass}`}
      style={{ top: `${top}%`, height: `${Math.max(height, 2.5)}%` }}
      title={`${event.title}\n${formatTime(event.start)}–${formatTime(event.end)}${event.location ? '\n' + event.location : ''}`}
    >
      <div className="font-semibold truncate">{event.title}</div>
      {height > 5 && (
        <div className="truncate opacity-75">
          {formatTime(event.start)}–{formatTime(event.end)}
        </div>
      )}
      {height > 8 && event.location && (
        <div className="truncate opacity-60">{event.location}</div>
      )}
    </div>
  )
}
