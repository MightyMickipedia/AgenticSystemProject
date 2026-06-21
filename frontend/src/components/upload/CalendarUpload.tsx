import { useCallback, useState } from 'react'
import { uploadCalendar, loadSnapshot } from '../../api/client'
import type { WeeklyCalendar } from '../../api/types'

interface CalendarUploadProps {
  onLoaded: (calendar: WeeklyCalendar) => void
}

export function CalendarUpload({ onLoaded }: CalendarUploadProps) {
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleFile = useCallback(
    async (file: File) => {
      setError(null)
      setLoading(true)
      try {
        const cal = await uploadCalendar(file)
        onLoaded(cal)
      } catch (e: any) {
        setError(e.message || 'Upload failed')
      } finally {
        setLoading(false)
      }
    },
    [onLoaded],
  )

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragging(false)
      const file = e.dataTransfer.files[0]
      if (file) handleFile(file)
    },
    [handleFile],
  )

  const handleSnapshot = useCallback(async () => {
    setError(null)
    setLoading(true)
    try {
      const cal = await loadSnapshot()
      onLoaded(cal)
    } catch (e: any) {
      setError(e.message || 'Failed to load snapshot')
    } finally {
      setLoading(false)
    }
  }, [onLoaded])

  return (
    <div className="space-y-4">
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          dragging
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
            : 'border-slate-300 dark:border-slate-600 hover:border-slate-400'
        }`}
      >
        <div className="text-slate-500 dark:text-slate-400 mb-3">
          {loading ? (
            <div className="flex items-center justify-center gap-2">
              <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              Loading...
            </div>
          ) : (
            <>
              <p className="text-lg mb-1">Drop a JSON calendar file here</p>
              <p className="text-sm">or click to browse</p>
            </>
          )}
        </div>
        <input
          type="file"
          accept=".json"
          className="hidden"
          id="calendar-upload"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) handleFile(file)
          }}
        />
        {!loading && (
          <label
            htmlFor="calendar-upload"
            className="inline-block px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium cursor-pointer hover:bg-blue-700 transition-colors"
          >
            Choose File
          </label>
        )}
      </div>

      <div className="flex items-center gap-3">
        <div className="h-px flex-1 bg-slate-200 dark:bg-slate-700" />
        <span className="text-sm text-slate-400">or</span>
        <div className="h-px flex-1 bg-slate-200 dark:bg-slate-700" />
      </div>

      <button
        onClick={handleSnapshot}
        disabled={loading}
        className="w-full py-2 rounded-md border border-slate-300 dark:border-slate-600 text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors disabled:opacity-50"
      >
        Load Latest Snapshot
      </button>

      {error && (
        <div className="p-3 rounded-md bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-sm text-red-700 dark:text-red-400">
          {error}
        </div>
      )}
    </div>
  )
}
