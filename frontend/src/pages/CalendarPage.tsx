import type { WeeklyCalendar } from '../api/types'
import { WeekTimeline } from '../components/calendar/WeekTimeline'
import { CalendarUpload } from '../components/upload/CalendarUpload'
import { useOptimizationStore } from '../store/useOptimizationStore'

interface CalendarPageProps {
  calendar: WeeklyCalendar | null
  onCalendarLoaded: (cal: WeeklyCalendar) => void
}

export function CalendarPage({ calendar, onCalendarLoaded }: CalendarPageProps) {
  const { report, selectedVariantName } = useOptimizationStore()

  const selectedVariant =
    report && selectedVariantName
      ? [report.recommended_variant, ...report.alternatives].find(
          (v) => v.name === selectedVariantName,
        ) || null
      : null

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Weekly Calendar</h2>
        {calendar && (
          <div className="text-sm text-slate-500">
            Week of {calendar.week_start} &middot; {calendar.events.length} events &middot;{' '}
            {calendar.timezone}
          </div>
        )}
      </div>

      {!calendar ? (
        <div className="max-w-md mx-auto">
          <CalendarUpload onLoaded={onCalendarLoaded} />
        </div>
      ) : (
        <>
          <WeekTimeline calendar={calendar} variant={selectedVariant} />

          {selectedVariant && (
            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-blue-300 border border-blue-400" />
                <span className="text-slate-600 dark:text-slate-400">Current events</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-purple-300 border border-purple-400 border-dashed opacity-75" />
                <span className="text-slate-600 dark:text-slate-400">
                  Proposed moves ({selectedVariant.name})
                </span>
              </div>
            </div>
          )}

          {report && (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm text-slate-500">Show variant:</span>
              {[report.recommended_variant, ...report.alternatives].map((v) => (
                <button
                  key={v.name}
                  onClick={() => useOptimizationStore.getState().selectVariant(v.name)}
                  className={`px-3 py-1 text-sm rounded-full transition-colors ${
                    selectedVariantName === v.name
                      ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                      : 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400 hover:bg-slate-200'
                  }`}
                >
                  {v.name}
                  {v.name === report.recommended_variant.name && ' *'}
                </button>
              ))}
            </div>
          )}

          <div className="pt-4 border-t border-slate-200 dark:border-slate-700">
            <CalendarUpload onLoaded={onCalendarLoaded} />
          </div>
        </>
      )}
    </div>
  )
}
