import type { WSMessage, OptimizationReport, WeeklyCalendar } from './types'

export interface WSHandlers {
  onFlow: (message: string, timestamp: number) => void
  onReport: (report: OptimizationReport) => void
  onCalendar: (calendar: WeeklyCalendar) => void
  onError: (message: string) => void
  onClose: () => void
}

export class OptimizationSocket {
  private ws: WebSocket | null = null

  connect(optimizeId: string, handlers: WSHandlers) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${window.location.host}/api/optimize/ws/${optimizeId}`
    this.ws = new WebSocket(url)

    this.ws.onmessage = (event) => {
      const data: WSMessage = JSON.parse(event.data)
      switch (data.type) {
        case 'flow':
          handlers.onFlow(data.message, data.timestamp)
          break
        case 'report':
          handlers.onReport(data.data)
          break
        case 'calendar':
          handlers.onCalendar(data.data)
          break
        case 'error':
          handlers.onError(data.message)
          break
      }
    }

    this.ws.onclose = () => handlers.onClose()
    this.ws.onerror = () => handlers.onError('WebSocket connection error')
  }

  disconnect() {
    this.ws?.close()
    this.ws = null
  }
}
