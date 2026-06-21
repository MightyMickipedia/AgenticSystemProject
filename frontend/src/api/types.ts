export interface CalendarEvent {
  id: string
  title: string
  start: string
  end: string
  all_day: boolean
  location: string
  description: string
  calendar_id: string
  recurring_event_id: string | null
  html_link: string | null
}

export interface WeeklyCalendar {
  week_start: string
  timezone: string
  events: CalendarEvent[]
  day_start: string
  day_end: string
}

export type Flexibility =
  | 'fixed'
  | 'likely_fixed'
  | 'uncertain'
  | 'likely_flexible'
  | 'flexible'

export interface MoveProposal {
  event_id: string
  new_start: string
  new_end: string
  reason: string
  flexibility: Flexibility
  confidence: number
}

export interface OptimizationVariant {
  name: string
  summary: string
  proposals: MoveProposal[]
}

export interface RejectedProposal {
  proposal: MoveProposal
  reason: string
}

export interface OptimizationReport {
  week_start: string
  generated_at: string
  recommended_variant: OptimizationVariant
  alternatives: OptimizationVariant[]
  hr_warnings: string[]
  traffic_warnings: string[]
  rejected_proposals: RejectedProposal[]
  notes: string[]
}

export type WSMessage =
  | { type: 'flow'; message: string; timestamp: number }
  | { type: 'report'; data: OptimizationReport }
  | { type: 'calendar'; data: WeeklyCalendar }
  | { type: 'error'; message: string }
