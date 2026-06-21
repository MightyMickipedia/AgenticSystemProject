import { useEffect, useRef } from 'react'
import type { FlowMessage } from '../../store/useOptimizationStore'

interface FlowLogProps {
  messages: FlowMessage[]
  status: 'idle' | 'running' | 'complete' | 'error'
}

function formatTimestamp(ts: number): string {
  const d = new Date(ts * 1000)
  return d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export function FlowLog({ messages, status }: FlowLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])

  return (
    <div className="bg-slate-900 rounded-lg border border-slate-700 overflow-hidden">
      <div className="px-4 py-2 border-b border-slate-700 flex items-center justify-between">
        <span className="text-sm font-medium text-slate-300">Agent Flow Log</span>
        {status === 'running' && (
          <span className="flex items-center gap-2 text-xs text-green-400">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            Running
          </span>
        )}
        {status === 'complete' && (
          <span className="text-xs text-blue-400">Complete</span>
        )}
        {status === 'error' && (
          <span className="text-xs text-red-400">Error</span>
        )}
      </div>
      <div className="p-4 h-80 overflow-y-auto font-mono text-xs leading-relaxed">
        {messages.length === 0 && status === 'idle' && (
          <div className="text-slate-500">Waiting for optimization to start...</div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className="flex gap-3 hover:bg-slate-800/50 py-0.5">
            <span className="text-slate-500 flex-shrink-0">{formatTimestamp(msg.timestamp)}</span>
            <span className="text-emerald-400">[FLOW]</span>
            <span className="text-slate-300">{msg.message}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
