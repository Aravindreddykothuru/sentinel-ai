import type { Machine, SensorData, MachineStatus, HistoryPoint, NormalRanges } from './sentinel-types'

function clamp(v: number, min: number, max: number) {
  return Math.min(max, Math.max(min, v))
}

function jitter(v: number, amt: number) {
  return v + (Math.random() - 0.5) * amt * 2
}

export function computeHealth(sd: Omit<SensorData, 'health' | 'failureProbability' | 'timeToFailure'>, nr: NormalRanges): number {
  const tempScore  = 1 - clamp((sd.temperature - nr.temperature.max)  / (nr.temperature.max  * 0.4), 0, 1)
  const vibScore   = 1 - clamp((sd.vibration   - nr.vibration.max)    / (nr.vibration.max    * 0.5), 0, 1)
  const rpmScore   = 1 - clamp(Math.abs(sd.rpm - (nr.rpm.min + nr.rpm.max) / 2) / ((nr.rpm.max - nr.rpm.min) * 1.2), 0, 1)
  const presScore  = 1 - clamp((sd.pressure    - nr.pressure.max)     / (nr.pressure.max     * 0.5), 0, 1)
  return clamp(Math.round((tempScore * 0.3 + vibScore * 0.3 + rpmScore * 0.2 + presScore * 0.2) * 100), 0, 100)
}

export function computeFailureProbability(health: number): number {
  if (health > 80) return clamp(jitter(5, 3), 0, 20)
  if (health > 60) return clamp(jitter(25, 8), 5, 45)
  if (health > 40) return clamp(jitter(55, 10), 30, 75)
  return clamp(jitter(82, 8), 60, 99)
}

export function computeTTF(failProb: number): string {
  if (failProb > 80) return '< 2 hours'
  if (failProb > 60) return '4–12 hours'
  if (failProb > 40) return '1–3 days'
  if (failProb > 20) return '1–2 weeks'
  return '> 30 days'
}

export function computeStatus(health: number): MachineStatus {
  if (health < 40) return 'critical'
  if (health < 65) return 'warning'
  return 'normal'
}

export function simulateMachine(m: Machine, drift = 0): Machine {
  const nr = m.normalRanges
  const base = {
    temperature: clamp(jitter(m.sensorData.temperature, 2) + drift * 0.3, nr.temperature.min - 5, nr.temperature.max * 1.4),
    vibration:   clamp(jitter(m.sensorData.vibration,   0.2) + drift * 0.05, nr.vibration.min, nr.vibration.max * 1.6),
    rpm:         clamp(jitter(m.sensorData.rpm,          50)  + drift * 5,  nr.rpm.min * 0.8, nr.rpm.max * 1.3),
    pressure:    clamp(jitter(m.sensorData.pressure,     2)   + drift * 0.2, nr.pressure.min * 0.7, nr.pressure.max * 1.4),
  }
  const health = computeHealth(base, nr)
  const failureProbability = computeFailureProbability(health)
  const timeToFailure = computeTTF(failureProbability)
  const newSd: SensorData = { ...base, health, failureProbability, timeToFailure }
  const newPoint: HistoryPoint = { t: Date.now(), ...base, health, failureProbability }
  return {
    ...m,
    sensorData: newSd,
    status: computeStatus(health),
    history: [...m.history.slice(-19), newPoint],
  }
}

export function applyStressValues(
  m: Machine,
  stress: { temperature: number; vibration: number; rpm: number; pressure: number }
): Machine {
  const base = { temperature: stress.temperature, vibration: stress.vibration, rpm: stress.rpm, pressure: stress.pressure }
  const health = computeHealth(base, m.normalRanges)
  const failureProbability = computeFailureProbability(health)
  const timeToFailure = computeTTF(failureProbability)
  const newSd: SensorData = { ...base, health, failureProbability, timeToFailure }
  const newPoint: HistoryPoint = { t: Date.now(), ...base, health, failureProbability }
  return {
    ...m,
    sensorData: newSd,
    status: computeStatus(health),
    history: [...m.history.slice(-19), newPoint],
  }
}

const makeHistory = (nr: NormalRanges, len = 20): HistoryPoint[] =>
  Array.from({ length: len }, (_, i) => {
    const frac = i / len
    const temp = nr.temperature.min + (nr.temperature.max - nr.temperature.min) * 0.5 + jitter(0, 5)
    const vib  = nr.vibration.min   + (nr.vibration.max   - nr.vibration.min)   * 0.3 + jitter(0, 0.5)
    const rpm  = (nr.rpm.min + nr.rpm.max) / 2 + jitter(0, 100)
    const pres = nr.pressure.min    + (nr.pressure.max    - nr.pressure.min)    * 0.5 + jitter(0, 3)
    const base = { temperature: temp, vibration: vib, rpm, pressure: pres }
    const health = computeHealth(base, nr)
    return { t: Date.now() - (len - i) * 2000, ...base, health, failureProbability: computeFailureProbability(health) }
  })

const turbineRanges: NormalRanges = { temperature: { min: 20, max: 95 },  vibration: { min: 0, max: 4.5 }, rpm: { min: 2000, max: 4000 }, pressure: { min: 60, max: 110 } }
const compRanges:    NormalRanges = { temperature: { min: 20, max: 85 },  vibration: { min: 0, max: 3.5 }, rpm: { min: 1500, max: 3500 }, pressure: { min: 50, max: 100 } }
const pumpRanges:    NormalRanges = { temperature: { min: 20, max: 75 },  vibration: { min: 0, max: 3.0 }, rpm: { min: 1200, max: 3000 }, pressure: { min: 40, max: 90  } }
const motorRanges:   NormalRanges = { temperature: { min: 20, max: 80 },  vibration: { min: 0, max: 3.0 }, rpm: { min: 1000, max: 4500 }, pressure: { min: 30, max: 80  } }

export const INITIAL_MACHINES: Machine[] = [
  {
    id: 'A',
    name: 'Turbine Alpha',
    type: 'Gas Turbine',
    location: 'Bay 1',
    status: 'normal',
    normalRanges: turbineRanges,
    sensorData: { temperature: 78, vibration: 2.1, rpm: 3200, pressure: 82, health: 88, failureProbability: 8, timeToFailure: '> 30 days' },
    history: makeHistory(turbineRanges),
  },
  {
    id: 'B',
    name: 'Compressor Beta',
    type: 'Air Compressor',
    location: 'Bay 2',
    status: 'warning',
    normalRanges: compRanges,
    sensorData: { temperature: 91, vibration: 3.8, rpm: 2800, pressure: 105, health: 58, failureProbability: 32, timeToFailure: '1–2 weeks' },
    history: makeHistory(compRanges),
  },
  {
    id: 'C',
    name: 'Pump Gamma',
    type: 'Hydraulic Pump',
    location: 'Bay 3',
    status: 'critical',
    normalRanges: pumpRanges,
    sensorData: { temperature: 104, vibration: 6.2, rpm: 2100, pressure: 112, health: 22, failureProbability: 87, timeToFailure: '< 2 hours' },
    history: makeHistory(pumpRanges),
  },
  {
    id: 'D',
    name: 'Motor Delta',
    type: 'Drive Motor',
    location: 'Bay 4',
    status: 'normal',
    normalRanges: motorRanges,
    sensorData: { temperature: 62, vibration: 1.4, rpm: 3600, pressure: 58, health: 94, failureProbability: 4, timeToFailure: '> 30 days' },
    history: makeHistory(motorRanges),
  },
]
