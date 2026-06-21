import { useEffect, useState } from 'react'
import { getAuthStatus, googleLoginUrl } from '../../api/client'

const NAV_ITEMS = [
  { id: 'calendar', label: 'Calendar' },
  { id: 'optimize', label: 'Optimize' },
  { id: 'report', label: 'Report' },
] as const

interface HeaderProps {
  activePage: string
  onNavigate: (page: string) => void
}

export function Header({ activePage, onNavigate }: HeaderProps) {
  const [auth, setAuth] = useState<{ authenticated: boolean; has_calendar: boolean }>({
    authenticated: false,
    has_calendar: false,
  })

  useEffect(() => {
    getAuthStatus().then(setAuth).catch(() => {})
  }, [])

  return (
    <header className="border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-6">
        <h1 className="text-lg font-bold text-slate-900 dark:text-white m-0">
          Calendar Optimizer
        </h1>
        <nav className="flex gap-1">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                activePage === item.id
                  ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </div>
      <div className="flex items-center gap-3">
        {auth.authenticated ? (
          <span className="text-sm text-green-600 dark:text-green-400 flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
            Google Connected
          </span>
        ) : (
          <a
            href={googleLoginUrl()}
            className="text-sm px-3 py-1.5 rounded-md bg-blue-600 text-white hover:bg-blue-700 transition-colors no-underline"
          >
            Connect Google
          </a>
        )}
      </div>
    </header>
  )
}
