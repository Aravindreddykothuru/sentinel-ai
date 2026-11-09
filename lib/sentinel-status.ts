import type { Machine, MachineStatus } from './sentinel-types'

// Raw values of the CSS tokens in app/globals.css, for SVG and charts
export const COLORS = {
  deep: '#0f0f10',
  page: '#141415',
  panel: '#19191b',
  raised: '#232325',
  line: 'rgba(237,237,237,0.08)',
  lineStrong: 'rgba(237,237,237,0.14)',
  fg: '#ededed',
  fg2: '#a1a1a6',
  fg3: '#85858b',
  signal: '#6cb4ee',
  ok: '#4cc38a',
  warn: '#d6a243',
  crit: '#e5484d',
}

export type SensorKey = 'temperature' | 'vibration' | 'rpm' | 'pressure'

// Dial scales match the instrument ranges the dashboard has always used
export const SENSORS: { key: SensorKey; label: string; short: string; unit: string; scale: [number, number]; decimals: number }[] = [
  { key: 'temperature', label: 'Temperature', short: 'Temp',  unit: '°C',   scale: [20, 150],  decimals: 1 },
  { key: 'vibration',   label: 'Vibration',   short: 'Vib',   unit: 'mm/s', scale: [0, 10],    decimals: 2 },
  { key: 'rpm',         label: 'Speed',       short: 'RPM',   unit: 'rpm',  scale: [500, 5500], decimals: 0 },
  { key: 'pressure',    label: 'Pressure',    short: 'Press', unit: 'bar',  scale: [20, 140],  decimals: 1 },
]

export const STATUS: Record<MachineStatus, { label: string; color: string; dot: string; text: string }> = {
  normal:   { label: 'Normal',    color: COLORS.ok,   dot: 'bg-ok',   text: 'text-ok' },
  warning:  { label: 'Degrading', color: COLORS.warn, dot: 'bg-warn', text: 'text-warn' },
  critical: { label: 'Critical',  color: COLORS.crit, dot: 'bg-crit', text: 'text-crit' },
}

/**
 * Where a reading sits against its normal band. The backend's alarm limits sit 15% past
 * the normal range, so beyond that counts as far out.
 */
export type BandState = 'in' | 'out' | 'far'

export function bandState(value: number, range: { min: number; max: number }): BandState {
  if (value >= range.min && value <= range.max) return 'in'
  if (value > range.max * 1.15 || value < range.min * 0.85) return 'far'
  return 'out'
}

export const BAND_COLOR: Record<BandState, string> = {
  in: COLORS.fg,
  out: COLORS.warn,
  far: COLORS.crit,
}

export function sensorsOutOfBand(machine: Machine): { label: string; state: BandState }[] {
  return SENSORS
    .map(s => ({ label: s.label.toLowerCase(), state: bandState(machine.sensorData[s.key], machine.normalRanges[s.key]) }))
    .filter(s => s.state !== 'in')
}

export function formatReading(value: number, decimals: number): string {
  return value.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}
