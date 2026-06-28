import type { OptimizationReport, WeeklyCalendar } from '../../api/types'
import { VariantCard } from './VariantCard'
import { WarningsSection } from './WarningsSection'

interface ReportViewerProps {
  report: OptimizationReport
  calendar: WeeklyCalendar
}

export function ReportViewer({ report, calendar }: ReportViewerProps) {
  const generatedAt = new Date(report.generated_at).toLocaleString('de-DE')

  return (
    <div className="space-y-6">
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md p-4 text-sm text-blue-800 dark:text-blue-300">
        This report contains advisory suggestions only. <strong>No changes were made to the calendar.</strong>
      </div>

      <div className="text-sm text-slate-500 dark:text-slate-400">
        Week: {report.week_start} &middot; Generated: {generatedAt} &middot; Timezone: {calendar.timezone}
      </div>

      <div>
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-3">Recommendation</h3>
        <VariantCard
          variant={report.recommended_variant}
          events={calendar.events}
          isRecommended
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <WarningsSection
          title="Human Feasibility"
          warnings={report.hr_warnings}
          color="yellow"
        />
        <WarningsSection
          title="Transitions & Travel"
          warnings={report.traffic_warnings}
          color="orange"
        />
      </div>

      <div>
        <h3 className="text-sm font-medium text-slate-600 dark:text-slate-400 mb-2">
          Human Recommendations
        </h3>
        {report.human_recommendations.length > 0 ? (
          <div className="rounded-md border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-900/10 p-3 space-y-2">
            {report.human_recommendations.map((recommendation, i) => (
              <div
                key={i}
                className="text-sm text-emerald-800 dark:text-emerald-300 flex items-start gap-2"
              >
                <span className="text-emerald-500 mt-0.5">&gt;</span>
                <span>{recommendation}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-400">No additional recommendations.</p>
        )}
      </div>

      {report.alternatives.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-3">
            Alternatives
          </h3>
          <div className="space-y-3">
            {report.alternatives.map((v) => (
              <VariantCard key={v.name} variant={v} events={calendar.events} />
            ))}
          </div>
        </div>
      )}

      {report.rejected_proposals.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-slate-600 dark:text-slate-400 mb-2">
            Rejected Proposals
          </h3>
          <div className="space-y-1">
            {report.rejected_proposals.map((r, i) => (
              <div
                key={i}
                className="text-sm text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800 rounded p-2"
              >
                <code className="text-xs">{r.proposal.event_id}</code>: {r.reason}
              </div>
            ))}
          </div>
        </div>
      )}

      {report.notes.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-slate-600 dark:text-slate-400 mb-2">Notes</h3>
          <ul className="list-disc list-inside text-sm text-slate-500 dark:text-slate-400 space-y-1">
            {report.notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="pt-4 border-t border-slate-200 dark:border-slate-700">
        <a
          href="/api/optimize/report/markdown"
          download
          className="inline-block px-4 py-2 rounded-md bg-slate-700 text-white text-sm hover:bg-slate-600 transition-colors no-underline"
        >
          Download Markdown Report
        </a>
      </div>
    </div>
  )
}
