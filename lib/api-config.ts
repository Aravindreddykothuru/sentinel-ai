// API Configuration for SENTINEL AI Backend

// NEXT_PUBLIC_API_URL may be a full URL or a bare host (e.g. "sentinel-api.onrender.com")
function normalizeBaseUrl(raw: string): string {
  const url = raw.trim().replace(/\/+$/, '')
  if (/^https?:\/\//.test(url)) return url
  const isLocal = /^(localhost|127\.0\.0\.1)(:|$)/.test(url)
  return `${isLocal ? 'http' : 'https'}://${url}`
}

export const API_BASE_URL = normalizeBaseUrl(process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000')

// http -> ws, https -> wss (an https page may only open wss sockets)
export const WS_BASE_URL = (process.env.NEXT_PUBLIC_WS_URL || API_BASE_URL.replace(/^http/, 'ws')).replace(/\/+$/, '')

// API Endpoints
export const ENDPOINTS = {
  // Machines
  machines: `${API_BASE_URL}/machines/`,
  machineReadings: (id: string) => `${API_BASE_URL}/machines/${id}/readings`,

  // Alerts
  alerts: `${API_BASE_URL}/alerts/`,
  alertStats: `${API_BASE_URL}/alerts/stats/summary`,

  // Digital Twin
  twinState: (id: string) => `${API_BASE_URL}/twin/state/${id}`,
  twinSimulate: (id: string) => `${API_BASE_URL}/twin/simulate/${id}`,
  twinOptimize: (id: string) => `${API_BASE_URL}/twin/optimize/${id}`,

  // Maintenance
  maintenanceSchedules: `${API_BASE_URL}/maintenance/schedules`,

  // Copilot
  copilotChat: `${API_BASE_URL}/copilot/chat`,

  // WebSocket
  websocket: `${WS_BASE_URL}/ws`,
}

// Helper function for API calls
export async function fetchApi(url: string, options?: RequestInit) {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }

  return response.json()
}

// Backend timestamps are naive UTC ("2026-01-01T09:41:22"); mark them as UTC before parsing
export function parseBackendDate(value: string): Date {
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(value) ? value : `${value}Z`)
}
