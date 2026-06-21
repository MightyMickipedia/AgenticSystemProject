interface WarningsSectionProps {
  title: string
  warnings: string[]
  color: 'yellow' | 'orange'
}

const COLORS = {
  yellow: {
    bg: 'bg-yellow-50 dark:bg-yellow-900/10',
    border: 'border-yellow-200 dark:border-yellow-800',
    icon: 'text-yellow-500',
    text: 'text-yellow-800 dark:text-yellow-300',
  },
  orange: {
    bg: 'bg-orange-50 dark:bg-orange-900/10',
    border: 'border-orange-200 dark:border-orange-800',
    icon: 'text-orange-500',
    text: 'text-orange-800 dark:text-orange-300',
  },
}

export function WarningsSection({ title, warnings, color }: WarningsSectionProps) {
  const c = COLORS[color]

  if (warnings.length === 0) {
    return (
      <div className="mb-4">
        <h4 className="text-sm font-medium text-slate-600 dark:text-slate-400 mb-2">{title}</h4>
        <p className="text-sm text-slate-400">No warnings.</p>
      </div>
    )
  }

  return (
    <div className="mb-4">
      <h4 className="text-sm font-medium text-slate-600 dark:text-slate-400 mb-2">{title}</h4>
      <div className={`rounded-md border ${c.bg} ${c.border} p-3 space-y-1`}>
        {warnings.map((w, i) => (
          <div key={i} className={`text-sm ${c.text} flex items-start gap-2`}>
            <span className={`${c.icon} mt-0.5`}>!</span>
            <span>{w}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
