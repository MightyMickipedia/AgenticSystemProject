import { useState } from 'react'
import type { OptimizationReport, WeeklyCalendar } from '../../api/types'
import { WeekTimeline } from '../calendar/WeekTimeline'
import { VariantCard } from '../report/VariantCard'

interface VariantComparisonProps {
  report: OptimizationReport
  calendar: WeeklyCalendar
}

export function VariantComparison({ report, calendar }: VariantComparisonProps) {
  const allVariants = [report.recommended_variant, ...report.alternatives]
  const [leftIdx, setLeftIdx] = useState(0)
  const [rightIdx, setRightIdx] = useState(allVariants.length > 1 ? 1 : 0)

  if (allVariants.length < 2) {
    return (
      <div className="text-sm text-slate-400 dark:text-slate-500 text-center py-8">
        Only one variant available — nothing to compare.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-4 items-center justify-center">
        <div className="flex items-center gap-2">
          <label className="text-sm text-slate-500">Left:</label>
          <select
            value={leftIdx}
            onChange={(e) => setLeftIdx(Number(e.target.value))}
            className="text-sm rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-2 py-1"
          >
            {allVariants.map((v, i) => (
              <option key={i} value={i}>
                {v.name} {i === 0 ? '(Recommended)' : ''}
              </option>
            ))}
          </select>
        </div>
        <span className="text-slate-400">vs</span>
        <div className="flex items-center gap-2">
          <label className="text-sm text-slate-500">Right:</label>
          <select
            value={rightIdx}
            onChange={(e) => setRightIdx(Number(e.target.value))}
            className="text-sm rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-2 py-1"
          >
            {allVariants.map((v, i) => (
              <option key={i} value={i}>
                {v.name} {i === 0 ? '(Recommended)' : ''}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <WeekTimeline calendar={calendar} variant={allVariants[leftIdx]} />
          <div className="mt-3">
            <VariantCard
              variant={allVariants[leftIdx]}
              events={calendar.events}
              isRecommended={leftIdx === 0}
            />
          </div>
        </div>
        <div>
          <WeekTimeline calendar={calendar} variant={allVariants[rightIdx]} />
          <div className="mt-3">
            <VariantCard
              variant={allVariants[rightIdx]}
              events={calendar.events}
              isRecommended={rightIdx === 0}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
