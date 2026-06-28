import { useCallback, useRef } from 'react'
import { startOptimization } from '../../api/client'
import { OptimizationSocket } from '../../api/websocket'
import { useOptimizationStore } from '../../store/useOptimizationStore'

interface OptimizePanelProps {
  hasCalendar: boolean
}

export function OptimizePanel({ hasCalendar }: OptimizePanelProps) {
  const { status, error, setStatus, setError, addFlowMessage, setReport, setCalendar, reset } =
    useOptimizationStore()
  const socketRef = useRef<OptimizationSocket | null>(null)

  const handleStart = useCallback(async () => {
    reset()
    setStatus('running')

    try {
      const { optimize_id } = await startOptimization()
      const socket = new OptimizationSocket()
      socketRef.current = socket

      socket.connect(optimize_id, {
        onFlow: (message, timestamp) => addFlowMessage({ message, timestamp }),
        onReport: (report) => setReport(report),
        onCalendar: (calendar) => setCalendar(calendar),
        onError: (message) => setError(message),
        onClose: () => {
          const currentStatus = useOptimizationStore.getState().status
          if (currentStatus === 'running') {
            setStatus('complete')
          }
        },
      })
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to start optimization')
    }
  }, [reset, setStatus, setError, addFlowMessage, setReport, setCalendar])

  const handleStop = useCallback(() => {
    socketRef.current?.disconnect()
    socketRef.current = null
    setStatus('idle')
  }, [setStatus])

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
      <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
        Optimization
      </h2>

      {!hasCalendar && (
        <div className="p-4 rounded-md bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-sm text-amber-700 dark:text-amber-400 mb-4">
          Upload a calendar first to start optimization.
        </div>
      )}

      <div className="flex items-center gap-3">
        {status === 'running' ? (
          <button
            onClick={handleStop}
            className="px-4 py-2 rounded-md bg-red-600 text-white text-sm font-medium hover:bg-red-700 transition-colors"
          >
            Stop
          </button>
        ) : (
          <button
            onClick={handleStart}
            disabled={!hasCalendar}
            className="px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Start Optimization
          </button>
        )}

        {status === 'complete' && (
          <span className="text-sm text-green-600 dark:text-green-400">
            Optimization complete
          </span>
        )}
      </div>

      {error && (
        <div className="mt-4 p-3 rounded-md bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-sm text-red-700 dark:text-red-400">
          {error}
        </div>
      )}

      <div className="mt-3 text-xs text-slate-400">
        Requires Ollama running at localhost:11434 with llama3.1:8b and qwen2.5:14b models.
      </div>
    </div>
  )
}
