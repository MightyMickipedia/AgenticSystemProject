interface TimeAxisProps {
  dayStart: number
  dayEnd: number
}

export function TimeAxis({ dayStart, dayEnd }: TimeAxisProps) {
  const hours = []
  for (let h = dayStart; h <= dayEnd; h++) {
    hours.push(h)
  }

  return (
    <div className="relative w-14 flex-shrink-0">
      {hours.map((h) => {
        const top = ((h - dayStart) / (dayEnd - dayStart)) * 100
        return (
          <div
            key={h}
            className="absolute right-2 text-xs text-slate-400 dark:text-slate-500 -translate-y-1/2"
            style={{ top: `${top}%` }}
          >
            {String(h).padStart(2, '0')}:00
          </div>
        )
      })}
    </div>
  )
}
