'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import dynamic from 'next/dynamic'
import SentinelHeader from '@/components/sentinel/SentinelHeader'
import CenterColumn from '@/components/sentinel/CenterColumn'
import RightColumn from '@/components/sentinel/RightColumn'
import { ToastContainer } from '@/components/sentinel/Toast'
import type { Machine, MachineStatus, Alert, MaintenanceItem, StressConfig, Mechanic, NotificationLog, NormalRanges, Toast as ToastType } from '@/lib/sentinel-types'
import { INITIAL_MACHINES, computeHealth, computeFailureProbability, computeTTF, computeStatus } from '@/lib/sentinel-simulation'
import { ENDPOINTS, fetchApi, parseBackendDate } from '@/lib/api-config'
import { useWebSocket } from '@/hooks/useWebSocket'

// Dynamic import LeftColumn to avoid SSR issues with modal
const LeftColumn = dynamic(() => import('@/components/sentinel/LeftColumn'), { ssr: false })

const DEFAULT_STRESS: StressConfig = {
  active: false,
  auto: false,
  temperature: 80,
  vibration: 3,
  rpm: 2500,
  pressure: 70,
}

const INITIAL_ALERTS: Alert[] = [
  { id: 'a1', level: 'critical', machine: 'Pump Gamma',      message: 'Vibration exceeds 6.0 mm/s — bearing failure imminent', timestamp: '09:41:22' },
  { id: 'a2', level: 'critical', machine: 'Pump Gamma',      message: 'Temperature 104°C — thermal runaway risk detected',      timestamp: '09:40:07' },
  { id: 'a3', level: 'warning',  machine: 'Compressor Beta', message: 'Pressure trending toward max threshold (105/100 bar)',    timestamp: '09:38:50' },
  { id: 'a4', level: 'warning',  machine: 'Compressor Beta', message: 'Vibration elevated — schedule inspection within 48h',    timestamp: '09:35:12' },
]

const INITIAL_MAINTENANCE: MaintenanceItem[] = [
  { id: 'm1', machine: 'Pump Gamma',      action: 'Emergency bearing replacement + seal inspection', scheduledTime: 'Today',              estimatedSavings: '$180K', priority: 'critical' },
  { id: 'm2', machine: 'Compressor Beta', action: 'Pressure valve calibration + vibration dampener',  scheduledTime: 'Within 48 hours',   estimatedSavings: '$45K',  priority: 'warning' },
  { id: 'm3', machine: 'Turbine Alpha',   action: 'Scheduled oil change + filter replacement',        scheduledTime: 'In 14 days',         estimatedSavings: '$12K',  priority: 'ok' },
]

const DEFAULT_RANGES: NormalRanges = {
  temperature: { min: 60, max: 95 },
  vibration: { min: 0.5, max: 4.0 },
  rpm: { min: 1300, max: 1700 },
  pressure: { min: 85, max: 105 },
}

// Re-alert a machine that stays critical at most this often
const AUTO_ALERT_COOLDOWN_MS = 5 * 60 * 1000
const MAX_HISTORY_POINTS = 30

let alertIdCounter = 100

const TIER_LABELS: Record<number, string> = { 1: 'NORMAL', 2: 'TRENDING', 3: 'CRITICAL' }

// The backend reports a tier (NORMAL / TRENDING / CRITICAL); out-of-range sensors also count as a warning
function toStatus(tierLabel: string | undefined, health: number): MachineStatus {
  if (tierLabel === 'CRITICAL') return 'critical'
  if (tierLabel === 'TRENDING' || health < 70) return 'warning'
  return 'normal'
}

// Backend stores normal ranges as { low, high }; the dashboard uses { min, max }
function toNormalRanges(ranges: Record<string, { low?: number; high?: number; min?: number; max?: number }> | undefined): NormalRanges {
  const pick = (sensor: keyof NormalRanges) => {
    const r = ranges?.[sensor]
    const min = r?.low ?? r?.min
    const max = r?.high ?? r?.max
    return min != null && max != null ? { min, max } : DEFAULT_RANGES[sensor]
  }
  return { temperature: pick('temperature'), vibration: pick('vibration'), rpm: pick('rpm'), pressure: pick('pressure') }
}

function toFrontendMachine(m: any): Machine {
  const sensors = m.latest_reading?.sensor_values || {}
  const health = m.health_score ?? 85
  const failureProbability = m.failure_probability ?? 15
  return {
    id: m.machine_id,
    name: m.name,
    type: m.type,
    location: m.location || 'Unknown',
    status: toStatus(TIER_LABELS[m.current_tier], health),
    normalRanges: toNormalRanges(m.normal_ranges),
    sensorData: {
      temperature: sensors.temperature ?? sensors.temperature_c ?? 75,
      vibration: sensors.vibration ?? sensors.vibration_mm_s ?? 2.0,
      rpm: sensors.rpm ?? 1480,
      pressure: sensors.pressure ?? sensors.pressure_bar ?? 95,
      health,
      failureProbability,
      timeToFailure: computeTTF(failureProbability),
    },
    history: [],
  }
}

export default function SentinelDashboard() {
  const [machines, setMachines] = useState<Machine[]>(INITIAL_MACHINES)
  const [selectedId, setSelectedId] = useState<string>('C')
  const [stress, setStress] = useState<StressConfig>(DEFAULT_STRESS)
  // Alerts from the backend (demo alerts until it answers) and alerts raised in this browser
  const [serverAlerts, setServerAlerts] = useState<Alert[]>(INITIAL_ALERTS)
  const [localAlerts, setLocalAlerts] = useState<Alert[]>([])
  const [maintenance, setMaintenance] = useState<MaintenanceItem[]>(INITIAL_MAINTENANCE)
  const [mechanics, setMechanics] = useState<Mechanic[]>([
    {
      id: 'mech-1',
      name: 'John Smith',
      email: 'john.smith@facility.com',
      phone: '+1 (555) 123-4567',
      assignedMachine: 'Pump Gamma',
      shift: 'morning',
      status: 'available',
    },
    {
      id: 'mech-2',
      name: 'Sarah Johnson',
      email: 'sarah.johnson@facility.com',
      phone: '+1 (555) 234-5678',
      assignedMachine: 'Compressor Beta',
      shift: 'evening',
      status: 'on-duty',
    },
  ])
  const [notificationLogs, setNotificationLogs] = useState<NotificationLog[]>([])
  const [toasts, setToasts] = useState<ToastType[]>([])
  const stressRef = useRef(stress)
  stressRef.current = stress
  const selectedIdRef = useRef(selectedId)
  selectedIdRef.current = selectedId
  const machinesRef = useRef(machines)
  machinesRef.current = machines
  const lastAutoAlertRef = useRef<Record<string, number>>({})
  const lastStressToastRef = useRef<Record<string, number>>({})
  const hasBackendDataRef = useRef(false)

  // Unique per tab: the backend keys sockets by client id, so a shared id would kick other viewers off
  const [wsUrl] = useState(() => `${ENDPOINTS.websocket}/frontend-${Math.random().toString(36).slice(2, 10)}`)

  // ─── WebSocket connection for real-time data ───────────────────────────────
  const handleWebSocketMessage = useCallback((msg: any) => {
    // Backend sends: { machine_id, timestamp, sensors, health_score, failure_probability, tier }
    if (!msg.machine_id || !msg.sensors) return
    // While a stress test drives the selected machine, live data must not overwrite it
    if (stressRef.current.active && msg.machine_id === selectedIdRef.current) return

    setMachines(prev => prev.map(m => {
      if (m.id !== msg.machine_id) return m

      // Map sensor names (backend uses different names)
      const sensors = msg.sensors || {}
      const temperature = sensors.temperature ?? sensors.temperature_c ?? m.sensorData.temperature
      const vibration = sensors.vibration ?? sensors.vibration_mm_s ?? m.sensorData.vibration
      const rpm = sensors.rpm ?? m.sensorData.rpm
      const pressure = sensors.pressure ?? sensors.pressure_bar ?? m.sensorData.pressure

      const health = msg.health_score ?? m.sensorData.health
      const failureProb = msg.failure_probability ?? m.sensorData.failureProbability

      return {
        ...m,
        status: toStatus(msg.tier?.label, health),
        sensorData: {
          temperature,
          vibration,
          rpm,
          pressure,
          health,
          failureProbability: failureProb,
          timeToFailure: computeTTF(failureProb),
        },
        history: [
          ...m.history.slice(-(MAX_HISTORY_POINTS - 1)),
          { t: Date.now(), health, failureProbability: failureProb, temperature, pressure, vibration },
        ],
      }
    }))
  }, [])

  const { isConnected, subscribe } = useWebSocket({
    url: wsUrl,
    onMessage: handleWebSocketMessage,
    onConnect: () => console.log('[Frontend] WebSocket connected'),
    onDisconnect: () => console.log('[Frontend] WebSocket disconnected'),
  })

  // (Re)subscribe to every machine whenever the socket (re)connects or the machine list changes
  const machineIdsKey = machines.map(m => m.id).join(',')
  useEffect(() => {
    if (!isConnected) return
    machineIdsKey.split(',').filter(Boolean).forEach(id => subscribe(id))
  }, [isConnected, machineIdsKey, subscribe])

  // ─── Fetch real data from backend on mount and whenever the socket (re)connects ────
  // (a sleeping free-tier backend may miss the first request; WebSocket provides updates in between)
  useEffect(() => {
    const fetchMachines = async () => {
      try {
        const data = await fetchApi(ENDPOINTS.machines)
        if (data.machines && data.machines.length > 0) {
          // The first real answer replaces the offline demo history; later refetches keep live history
          const keepHistory = hasBackendDataRef.current
          hasBackendDataRef.current = true
          setMachines(prev => data.machines.map((m: any) => ({
            ...toFrontendMachine(m),
            history: keepHistory ? prev.find(p => p.id === m.machine_id)?.history ?? [] : [],
          })))
          if (!data.machines.some((m: any) => m.machine_id === selectedIdRef.current)) {
            setSelectedId(data.machines[0].machine_id)
          }
        }
      } catch (error) {
        console.log('Using simulated data - backend not available')
      }
    }

    fetchMachines()
  }, [isConnected])

  // ─── Fetch alerts from backend ───────────────────────────────────
  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const data = await fetchApi(ENDPOINTS.alerts)
        if (data.alerts) {
          const nameFor = (id: string) => machinesRef.current.find(m => m.id === id)?.name || id
          const mappedAlerts: Alert[] = data.alerts.map((a: any) => {
            const severity = String(a.severity || '').toLowerCase()
            return {
              id: a.alert_id,
              level: severity === 'critical' || severity === 'emergency' ? 'critical' : severity === 'warning' ? 'warning' : 'info',
              machine: nameFor(a.machine_id),
              message: a.recommended_action ? `${a.failure_type} — ${a.recommended_action}` : a.failure_type,
              timestamp: parseBackendDate(a.created_at).toLocaleTimeString('en-US', { hour12: false }),
            }
          })
          setServerAlerts(mappedAlerts)
        }
      } catch (error) {
        console.log('Using initial alerts - backend not available')
      }
    }

    fetchAlerts()
    const interval = setInterval(fetchAlerts, 5000)
    return () => clearInterval(interval)
  }, [])

  const alerts = [...localAlerts, ...serverAlerts].slice(0, 40)

  // ─── Auto-generate alerts when failure probability crosses 70% ──
  useEffect(() => {
    machines.forEach(m => {
      if (m.sensorData.failureProbability > 70 && m.status === 'critical') {
        const nowMs = Date.now()
        if (nowMs - (lastAutoAlertRef.current[m.id] ?? 0) < AUTO_ALERT_COOLDOWN_MS) return
        lastAutoAlertRef.current[m.id] = nowMs

        const ts = new Date(nowMs).toLocaleTimeString('en-US', { hour12: false })

        // Find assigned mechanic
        const assignedMechanic = mechanics.find(mech => mech.assignedMachine === m.name)

        const newAlert: Alert = {
          id: `auto-${++alertIdCounter}`,
          level: 'critical',
          machine: m.name,
          message: `Failure risk at ${m.sensorData.failureProbability.toFixed(0)}%, inspect now`,
          timestamp: ts,
        }

        setLocalAlerts(prev => [newAlert, ...prev.slice(0, 19)])

        // Auto-send alert to mechanic and create notification log
        if (assignedMechanic) {
          const notificationId = `notif-${nowMs}-${m.id}`
          setNotificationLogs(prev => [
            {
              id: notificationId,
              timeSent: ts,
              channel: 'email',
              mechanicName: assignedMechanic.name,
              machineName: m.name,
              status: 'sent',
              escalationTimer: 30 * 60 * 1000, // 30 minutes in milliseconds
            },
            ...prev.slice(0, 9),
          ])

          // Show toast notification
          setToasts(prev => [
            {
              id: `toast-${nowMs}-${m.id}`,
              type: 'critical',
              message: `Alert sent to ${assignedMechanic.name} for ${m.name}`,
              mechanicName: assignedMechanic.name,
              machineName: m.name,
            },
            ...prev.slice(0, 4),
          ])
        }
      }
    })
  }, [machines, mechanics])

  const handleAddMachine = useCallback((newMachineData: Omit<Machine, 'id' | 'sensorData' | 'history'>) => {
    const nr = newMachineData.normalRanges
    const base = {
      temperature: (nr.temperature.min + nr.temperature.max) / 2,
      vibration:   (nr.vibration.min   + nr.vibration.max)   / 2,
      rpm:          (nr.rpm.min         + nr.rpm.max)          / 2,
      pressure:    (nr.pressure.min    + nr.pressure.max)    / 2,
    }
    const health = computeHealth(base, nr)
    const fp = computeFailureProbability(health)
    const newMachine: Machine = {
      ...newMachineData,
      id: `machine-${Date.now()}`,
      status: computeStatus(health),
      sensorData: { ...base, health, failureProbability: fp, timeToFailure: computeTTF(fp) },
      history: [],
    }
    setMachines(prev => [...prev, newMachine])

    // Register it with the backend so it gets monitored and streamed like the others
    fetchApi(ENDPOINTS.machines, {
      method: 'POST',
      body: JSON.stringify({
        machine_id: newMachine.id,
        name: newMachine.name,
        type: newMachine.type,
        location: newMachine.location,
        normal_ranges: nr,
      }),
    }).catch(() => console.log('Machine kept locally - backend not available'))
  }, [])

  const handleStressReset = useCallback(() => {
    setStress(DEFAULT_STRESS)
  }, [])

  const handleAddMechanic = useCallback((newMechanic: Omit<Mechanic, 'id'>) => {
    const mechanic: Mechanic = {
      ...newMechanic,
      id: `mech-${Date.now()}`,
    }
    setMechanics(prev => [...prev, mechanic])
  }, [])

  const handleDeleteMechanic = useCallback((id: string) => {
    setMechanics(prev => prev.filter(m => m.id !== id))
  }, [])

  const selectedMachine = machines.find(m => m.id === selectedId) || machines[0]
  const criticalCount = alerts.filter(a => a.level === 'critical').length

  // ─── Apply stress test values to selected machine ────────────────
  useEffect(() => {
    if (!stress.active) return
    const machineName = machinesRef.current.find(m => m.id === selectedId)?.name
    if (!machineName) return

    // Update the selected machine with stress test values
    setMachines(prev => prev.map(m => {
      if (m.id !== selectedId) return m

      // Calculate new health based on stress values
      const tempRatio = stress.temperature / 130 // max temp
      const vibRatio = stress.vibration / 8 // max vibration
      const rpmRatio = Math.abs(stress.rpm - 3000) / 2000 // deviation from normal

      const health = Math.max(10, 100 - (tempRatio * 30 + vibRatio * 40 + rpmRatio * 10))
      const failureProbability = Math.min(100, 100 - health + Math.random() * 10)
      const status = health < 40 ? 'critical' : health < 70 ? 'warning' : 'normal'
      const pressure = stress.pressure || m.sensorData.pressure

      return {
        ...m,
        status,
        sensorData: {
          ...m.sensorData,
          temperature: stress.temperature,
          vibration: stress.vibration,
          rpm: stress.rpm,
          pressure,
          health,
          failureProbability,
          timeToFailure: failureProbability > 80 ? '< 2 hours' :
                        failureProbability > 60 ? '< 8 hours' :
                        failureProbability > 40 ? '< 24 hours' : '> 30 days'
        },
        history: [
          ...m.history.slice(-(MAX_HISTORY_POINTS - 1)),
          { t: Date.now(), health, failureProbability, temperature: stress.temperature, pressure, vibration: stress.vibration },
        ],
      }
    }))

    // Trigger alert if critical
    if (stress.temperature > 110 || stress.vibration > 6) {
      const now = new Date()
      const ts = now.toLocaleTimeString('en-US', { hour12: false })

      const faults = [stress.temperature > 110 && 'overheating', stress.vibration > 6 && 'excessive vibration'].filter(Boolean).join(' and ')
      const newAlert: Alert = {
        id: `stress-${Date.now()}`,
        level: 'critical',
        machine: machineName,
        message: `Stress test: ${faults} detected`,
        timestamp: ts,
      }

      setLocalAlerts(prev => {
        // Don't duplicate recent stress alerts
        const recent = prev.filter(a => a.id.startsWith('stress-') && a.machine === machineName)
        if (recent.length > 0) return prev
        return [newAlert, ...prev.slice(0, 19)]
      })

      // Show toast, at most once a minute per machine (auto mode changes values every 1.5 s)
      if (Date.now() - (lastStressToastRef.current[machineName] ?? 0) > 60_000) {
        lastStressToastRef.current[machineName] = Date.now()
        setToasts(prev => [{
          id: `toast-${Date.now()}`,
          type: 'critical',
          message: `Stress test: ${machineName} crossed its critical limits`,
        }, ...prev.slice(0, 4)])
      }
    }
  }, [stress.active, stress.temperature, stress.vibration, stress.rpm, stress.pressure, selectedId])

  return (
    <div className="flex min-h-screen flex-col bg-page lg:h-screen lg:overflow-hidden">
      <ToastContainer
        toasts={toasts}
        onRemove={(id) => setToasts(prev => prev.filter(t => t.id !== id))}
      />
      <SentinelHeader
        machines={machines}
        criticalCount={criticalCount}
        isConnected={isConnected}
      />

      {/* Main 3-column layout; stacks on small screens */}
      <div className="flex flex-1 flex-col lg:flex-row lg:overflow-hidden">
        <LeftColumn
          machines={machines}
          selectedId={selectedId}
          onSelect={setSelectedId}
          stress={stress}
          onStressChange={setStress}
          onStressReset={handleStressReset}
          onAddMachine={handleAddMachine}
        />

        <CenterColumn machine={selectedMachine} />

        <RightColumn
          machine={selectedMachine}
          machines={machines}
          alerts={alerts}
          maintenance={maintenance}
          mechanics={mechanics}
          notificationLogs={notificationLogs}
          onAddMechanic={handleAddMechanic}
          onDeleteMechanic={handleDeleteMechanic}
        />
      </div>
    </div>
  )
}
