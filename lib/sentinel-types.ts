export type MachineStatus = 'normal' | 'warning' | 'critical'

export interface SensorData {
  temperature: number
  vibration: number
  rpm: number
  pressure: number
  health: number
  failureProbability: number
  timeToFailure: string
}

export interface NormalRanges {
  temperature: { min: number; max: number }
  vibration:   { min: number; max: number }
  rpm:          { min: number; max: number }
  pressure:     { min: number; max: number }
}

export interface Machine {
  id: string
  name: string
  type: string
  location: string
  status: MachineStatus
  normalRanges: NormalRanges
  sensorData: SensorData
  history: HistoryPoint[]
}

export interface HistoryPoint {
  t: number
  health: number
  failureProbability: number
  temperature: number
  pressure: number
  vibration: number
}

export interface Alert {
  id: string
  level: 'critical' | 'warning' | 'info'
  machine: string
  message: string
  timestamp: string
}

export interface StressConfig {
  active: boolean
  auto: boolean
  temperature: number
  vibration: number
  rpm: number
  pressure: number
}

export interface MaintenanceItem {
  id: string
  machine: string
  action: string
  scheduledTime: string
  estimatedSavings: string
  priority: 'critical' | 'warning' | 'ok'
}

export type MechanicStatus = 'available' | 'on-duty' | 'off-shift'
export type Shift = 'morning' | 'evening' | 'night'

export interface Mechanic {
  id: string
  name: string
  email: string
  phone: string
  assignedMachine: string
  shift: Shift
  status: MechanicStatus
}

export interface NotificationLog {
  id: string
  timeSent: string
  channel: 'email' | 'sms' | 'push'
  mechanicName: string
  machineName: string
  status: 'sent' | 'acknowledged' | 'resolved' | 'escalated'
  escalationTimer?: number // milliseconds until escalation
}

export interface Toast {
  id: string
  type: 'success' | 'critical'
  message: string
  mechanicName?: string
  machineName?: string
}
