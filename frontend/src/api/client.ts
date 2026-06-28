import type { WeeklyCalendar } from './types'

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    ...init,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(body.detail || res.statusText)
  }
  return res.json()
}

export async function uploadCalendar(
  file: File,
  opts: { timezone?: string; week_start?: string; day_start?: string; day_end?: string } = {},
): Promise<WeeklyCalendar> {
  const form = new FormData()
  form.append('file', file)
  const params = new URLSearchParams()
  if (opts.timezone) params.set('timezone', opts.timezone)
  if (opts.week_start) params.set('week_start', opts.week_start)
  if (opts.day_start) params.set('day_start', opts.day_start)
  if (opts.day_end) params.set('day_end', opts.day_end)
  const qs = params.toString()
  return request<WeeklyCalendar>(`/calendar/upload${qs ? '?' + qs : ''}`, {
    method: 'POST',
    body: form,
  })
}

export async function loadSnapshot(): Promise<WeeklyCalendar> {
  return request<WeeklyCalendar>('/calendar/load-snapshot', { method: 'POST' })
}

export async function getCalendar(): Promise<WeeklyCalendar> {
  return request<WeeklyCalendar>('/calendar')
}

export async function startOptimization(): Promise<{ optimize_id: string }> {
  return request<{ optimize_id: string }>('/optimize/start', { method: 'POST' })
}

export interface AuthStatus {
  authenticated: boolean
  has_calendar: boolean
  import_error?: string | null
}

export async function getAuthStatus(): Promise<AuthStatus> {
  return request('/auth/status')
}

export function googleLoginUrl(): string {
  return `${BASE}/auth/google/login`
}
