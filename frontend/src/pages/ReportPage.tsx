import { useState } from 'react'
import type { WeeklyCalendar } from '../api/types'
import { ReportViewer } from '../components/report/ReportViewer'
import { VariantComparison } from '../components/comparison/VariantComparison'
import { useOptimizationStore } from '../store/useOptimizationStore'

interface ReportPageProps {
  calendar: WeeklyCalendar | null
}

export function ReportPage({ calendar }: ReportPageProps) {
  const { report } = useOptimizationStore()
  const [tab, setTab] = useState<'report' | 'compare'>('report')

  if (!report || !calendar) {
    return (
      <div className="text-center py-16">
        <div className="text-slate-400 dark:text-slate-500 text-lg mb-2">No Report Available</div>
        <p className="text-sm text-slate-400">
          Upload a calendar and run optimization first.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Report</h2>
        <div className="flex gap-1 bg-slate-100 dark:bg-slate-700 rounded-lg p-1">
          <button
            onClick={() => setTab('report')}
            className={`px-3 py-1 text-sm rounded-md transition-colors ${
              tab === 'report'
                ? 'bg-white dark:bg-slate-600 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-500 dark:text-slate-400'
            }`}
          >
            Report
          </button>
          <button
            onClick={() => setTab('compare')}
            className={`px-3 py-1 text-sm rounded-md transition-colors ${
              tab === 'compare'
                ? 'bg-white dark:bg-slate-600 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-500 dark:text-slate-400'
            }`}
          >
            Compare Variants
          </button>
        </div>
      </div>

      {tab === 'report' ? (
        <ReportViewer report={report} calendar={calendar} />
      ) : (
        <VariantComparison report={report} calendar={calendar} />
      )}
    </div>
  )
}
