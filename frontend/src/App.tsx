import { useEffect, useState } from 'react'
import type { WeeklyCalendar } from './api/types'
import { getCalendar } from './api/client'
import { Header } from './components/layout/Header'
import { CalendarPage } from './pages/CalendarPage'
import { OptimizePage } from './pages/OptimizePage'
import { ReportPage } from './pages/ReportPage'

export default function App() {
  const [page, setPage] = useState('calendar')
  const [calendar, setCalendar] = useState<WeeklyCalendar | null>(null)

  // Pull any calendar already attached to the session (e.g. imported during the
  // Google OAuth redirect) so it shows up after the post-login page reload.
  useEffect(() => {
    getCalendar()
      .then(setCalendar)
      .catch(() => {})
  }, [])

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <Header activePage={page} onNavigate={setPage} />
      <main className="max-w-7xl mx-auto px-6 py-6">
        {page === 'calendar' && (
          <CalendarPage calendar={calendar} onCalendarLoaded={setCalendar} />
        )}
        {page === 'optimize' && <OptimizePage hasCalendar={calendar !== null} />}
        {page === 'report' && <ReportPage calendar={calendar} />}
      </main>
    </div>
  )
}
