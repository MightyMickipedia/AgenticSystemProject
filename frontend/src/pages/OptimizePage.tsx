import { OptimizePanel } from '../components/optimize/OptimizePanel'
import { FlowLog } from '../components/optimize/FlowLog'
import { useOptimizationStore } from '../store/useOptimizationStore'

interface OptimizePageProps {
  hasCalendar: boolean
}

export function OptimizePage({ hasCalendar }: OptimizePageProps) {
  const { flowMessages, status } = useOptimizationStore()

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-slate-900 dark:text-white">Optimize</h2>
      <OptimizePanel hasCalendar={hasCalendar} />
      <FlowLog messages={flowMessages} status={status} />
    </div>
  )
}
