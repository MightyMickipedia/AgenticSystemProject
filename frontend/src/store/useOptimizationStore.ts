import { create } from 'zustand'
import type { OptimizationReport, WeeklyCalendar } from '../api/types'

export interface FlowMessage {
  message: string
  timestamp: number
}

interface OptimizationState {
  status: 'idle' | 'running' | 'complete' | 'error'
  flowMessages: FlowMessage[]
  report: OptimizationReport | null
  calendar: WeeklyCalendar | null
  selectedVariantName: string | null
  error: string | null

  addFlowMessage: (msg: FlowMessage) => void
  setReport: (report: OptimizationReport) => void
  setCalendar: (calendar: WeeklyCalendar) => void
  setStatus: (status: OptimizationState['status']) => void
  setError: (error: string) => void
  selectVariant: (name: string) => void
  reset: () => void
}

export const useOptimizationStore = create<OptimizationState>((set) => ({
  status: 'idle',
  flowMessages: [],
  report: null,
  calendar: null,
  selectedVariantName: null,
  error: null,

  addFlowMessage: (msg) =>
    set((s) => ({ flowMessages: [...s.flowMessages, msg] })),

  setReport: (report) =>
    set({ report, status: 'complete', selectedVariantName: report.recommended_variant.name }),

  setCalendar: (calendar) => set({ calendar }),

  setStatus: (status) => set({ status }),

  setError: (error) => set({ error, status: 'error' }),

  selectVariant: (name) => set({ selectedVariantName: name }),

  reset: () =>
    set({
      status: 'idle',
      flowMessages: [],
      report: null,
      calendar: null,
      selectedVariantName: null,
      error: null,
    }),
}))
