'use client'

import { useState, useEffect } from 'react'
import { Plus, X } from 'lucide-react'
import type { Machine, StressConfig } from '@/lib/sentinel-types'
import { SENSORS, STATUS, BAND_COLOR, COLORS, bandState, formatReading } from '@/lib/sentinel-status'

// ─── Band ticks: one per sensor, lit when the reading leaves its normal range ──
function BandTicks({ machine }: { machine: Machine }) {
  return (
    <div className="flex items-center gap-1">
      {SENSORS.map(s => {
        const value = machine.sensorData[s.key]
        const range = machine.normalRanges[s.key]
        const state = bandState(value, range)
        return (
          <span
            key={s.key}
            title={`${s.label} ${formatReading(value, s.decimals)} ${s.unit}, normal ${range.min}–${range.max}`}
            className="h-1 w-3 rounded-full"
            style={{ backgroundColor: state === 'in' ? COLORS.lineStrong : BAND_COLOR[state] }}
          />
        )
      })}
    </div>
  )
}

// ─── Machine Card ──────────────────────────────────────────────────
interface MachineCardProps {
  machine: Machine
  selected: boolean
  onSelect: () => void
}

export function MachineCard({ machine, selected, onSelect }: MachineCardProps) {
  const status = STATUS[machine.status]
  const failProb = machine.sensorData.failureProbability
  const riskColor = failProb > 50 ? 'text-crit' : failProb > 30 ? 'text-warn' : 'text-fg-2'

  return (
    <button
      onClick={onSelect}
      aria-pressed={selected}
      className={`w-full text-left rounded-xl border p-3 transition-colors duration-150 ease-out-quint ${
        selected
          ? 'bg-raised border-line-strong shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]'
          : 'bg-transparent border-transparent hover:bg-panel'
      }`}
    >
      <div className="flex items-center gap-2">
        <span className={`h-2 w-2 shrink-0 rounded-full ${status.dot}`} title={status.label} />
        <span className="truncate text-[14px] font-medium text-fg">{machine.name}</span>
        <span className="ml-auto shrink-0 font-mono text-[12px] text-fg-3">{machine.location}</span>
      </div>
      <div className="mt-1 flex items-center gap-2 pl-4">
        <span className="truncate text-[13px] text-fg-2">{machine.type}</span>
        <span className={`ml-auto shrink-0 font-mono text-[13px] tabular-nums ${riskColor}`}>{failProb.toFixed(0)}% risk</span>
      </div>
      <div className="mt-2 flex items-center gap-2 pl-4">
        <BandTicks machine={machine} />
        <span className="ml-auto shrink-0 font-mono text-[12px] text-fg-3">
          {machine.sensorData.timeToFailure}
        </span>
      </div>
    </button>
  )
}

// ─── Slider with label ─────────────────────────────────────────────
interface SliderFieldProps {
  label: string
  unit: string
  value: number
  min: number
  max: number
  threshold: number
  onChange: (v: number) => void
}

function SliderField({ label, unit, value, min, max, threshold, onChange }: SliderFieldProps) {
  const isOver = value > threshold
  const pct = ((value - min) / (max - min)) * 100
  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between">
        <span className="text-[13px] text-fg-2">{label}</span>
        <span className="font-mono text-[12px] tabular-nums">
          <span className={isOver ? 'text-crit' : 'text-fg'}>{value.toFixed(0)}</span>
          <span className="text-fg-3"> / {threshold} {unit}</span>
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        aria-label={label}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full"
        style={{
          background: `linear-gradient(to right, ${isOver ? COLORS.crit : COLORS.fg2} ${pct}%, ${COLORS.raised} ${pct}%)`,
        }}
      />
    </div>
  )
}

// ─── Shared form styles ────────────────────────────────────────────
const fieldClass = 'h-9 w-full rounded-lg border border-line bg-deep px-3 text-[13px] text-fg placeholder:text-fg-3 transition-colors duration-150 focus:border-signal/60 focus:outline-none'
const labelClass = 'mb-2 block text-[12px] text-fg-2'
const primaryButton = 'h-9 rounded-lg bg-fg px-4 text-[13px] font-medium text-page transition-colors duration-150 hover:bg-white active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40'
const secondaryButton = 'h-9 rounded-lg border border-line bg-raised px-4 text-[13px] text-fg transition-colors duration-150 hover:border-line-strong active:scale-[0.98]'

// ─── Add Machine Modal ─────────────────────────────────────────────
interface AddMachineModalProps {
  onClose: () => void
  onAdd: (machine: Omit<Machine, 'id' | 'sensorData' | 'history'>) => void
}

const PRESETS: Record<string, { tempMin: number; tempMax: number; vibMin: number; vibMax: number; rpmMin: number; rpmMax: number; presMin: number; presMax: number }> = {
  'Steel & Metal':   { tempMin: 20, tempMax: 120, vibMin: 0, vibMax: 6,  rpmMin: 500,  rpmMax: 4000, presMin: 30, presMax: 100 },
  'Automotive':      { tempMin: 20, tempMax: 110, vibMin: 0, vibMax: 5,  rpmMin: 800,  rpmMax: 5000, presMin: 40, presMax: 120 },
  'Food & Beverage': { tempMin: 5,  tempMax: 80,  vibMin: 0, vibMax: 3,  rpmMin: 200,  rpmMax: 2000, presMin: 20, presMax: 80  },
  'Oil & Gas':       { tempMin: 20, tempMax: 130, vibMin: 0, vibMax: 7,  rpmMin: 1000, rpmMax: 4500, presMin: 50, presMax: 130 },
  'Power Plant':     { tempMin: 30, tempMax: 125, vibMin: 0, vibMax: 7,  rpmMin: 1500, rpmMax: 5000, presMin: 60, presMax: 130 },
  'Custom':          { tempMin: 20, tempMax: 100, vibMin: 0, vibMax: 5,  rpmMin: 1000, rpmMax: 4000, presMin: 40, presMax: 120 },
}

export function AddMachineModal({ onClose, onAdd }: AddMachineModalProps) {
  const [name, setName] = useState('')
  const [type, setType] = useState('Gas Turbine')
  const [location, setLocation] = useState('')
  const [preset, setPreset] = useState('Custom')
  const [ranges, setRanges] = useState(PRESETS['Custom'])

  function applyPreset(p: string) {
    setPreset(p)
    setRanges(PRESETS[p] || PRESETS['Custom'])
  }

  function handleSave() {
    if (!name.trim()) return
    onAdd({
      name: name.trim(),
      type,
      location: location || 'Bay X',
      status: 'normal',
      normalRanges: {
        temperature: { min: ranges.tempMin, max: ranges.tempMax },
        vibration:   { min: ranges.vibMin,  max: ranges.vibMax  },
        rpm:         { min: ranges.rpmMin,  max: ranges.rpmMax  },
        pressure:    { min: ranges.presMin, max: ranges.presMax },
      },
    })
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div role="dialog" aria-modal="true" aria-labelledby="add-machine-title" className="animate-enter max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-line bg-panel shadow-[0_24px_64px_rgba(0,0,0,0.5)]">
        <div className="flex items-center justify-between border-b border-line px-6 py-4">
          <h2 id="add-machine-title" className="text-[16px] font-medium text-fg">Add machine</h2>
          <button onClick={onClose} aria-label="Close" className="rounded-md p-1 text-fg-3 transition-colors duration-150 hover:text-fg">
            <X className="h-4 w-4" strokeWidth={1.5} />
          </button>
        </div>
        <div className="space-y-6 p-6">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Name</label>
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Pump Delta" className={fieldClass} />
            </div>
            <div>
              <label className={labelClass}>Location</label>
              <input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Bay 5" className={fieldClass} />
            </div>
          </div>
          <div>
            <label className={labelClass}>Type</label>
            <select value={type} onChange={(e) => setType(e.target.value)} className={fieldClass}>
              {['Gas Turbine','Air Compressor','Hydraulic Pump','Drive Motor','Heat Exchanger','Conveyor Drive','CNC Spindle'].map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          <div>
            <label className={labelClass}>Industry preset</label>
            <div className="flex flex-wrap gap-2">
              {Object.keys(PRESETS).map(p => (
                <button
                  key={p}
                  onClick={() => applyPreset(p)}
                  aria-pressed={preset === p}
                  className={`h-8 rounded-lg border px-3 text-[12px] transition-colors duration-150 ${
                    preset === p
                      ? 'border-line-strong bg-raised text-fg'
                      : 'border-line text-fg-2 hover:text-fg'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          <div>
            <p className={labelClass}>Normal operating ranges</p>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: 'Temperature min, °C', key: 'tempMin' },
                { label: 'Temperature max, °C', key: 'tempMax' },
                { label: 'Vibration min, mm/s', key: 'vibMin'  },
                { label: 'Vibration max, mm/s', key: 'vibMax'  },
                { label: 'Speed min, rpm',      key: 'rpmMin'  },
                { label: 'Speed max, rpm',      key: 'rpmMax'  },
                { label: 'Pressure min, bar',   key: 'presMin' },
                { label: 'Pressure max, bar',   key: 'presMax' },
              ].map(({ label, key }) => (
                <div key={key}>
                  <label className="mb-1 block text-[12px] text-fg-3">{label}</label>
                  <input
                    type="number"
                    value={(ranges as Record<string, number>)[key]}
                    onChange={(e) => setRanges(prev => ({ ...prev, [key]: Number(e.target.value) }))}
                    className={`${fieldClass} font-mono tabular-nums`}
                  />
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <button onClick={onClose} className={secondaryButton}>Cancel</button>
            <button onClick={handleSave} disabled={!name.trim()} className={primaryButton}>
              Save and start monitoring
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Stress Test Simulator ─────────────────────────────────────────
interface StressTestProps {
  stress: StressConfig
  onChange: (s: StressConfig) => void
  onReset: () => void
}

const FAULT_PRESETS: Record<string, Partial<StressConfig>> = {
  Overheat:      { temperature: 128, active: true },
  'Bearing fail': { vibration: 7.5, rpm: 1200, active: true },
  'Pressure drop': { pressure: 28, active: true },
  'RPM surge':   { rpm: 4800, active: true },
}

export function StressTestPanel({ stress, onChange, onReset }: StressTestProps) {
  const autoTick = () => {
    if (!stress.auto || !stress.active) return
    onChange({
      ...stress,
      temperature: Math.min(130, stress.temperature + (Math.random() - 0.3) * 3),
      vibration:   Math.min(8,   stress.vibration   + (Math.random() - 0.3) * 0.5),
    })
  }

  useEffect(() => {
    if (!stress.auto || !stress.active) return
    const t = setInterval(autoTick, 1500)
    return () => clearInterval(t)
  })

  return (
    <section className="rounded-xl border border-line bg-panel p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-[14px] font-medium text-fg">Stress test</h3>
          {stress.active && <span className="font-mono text-[12px] text-warn">Running</span>}
        </div>
        <div className="flex rounded-lg border border-line bg-deep p-0.5" role="group" aria-label="Stress test mode">
          {(['Manual', 'Auto'] as const).map(m => (
            <button
              key={m}
              onClick={() => onChange({ ...stress, auto: m === 'Auto', active: stress.active })}
              aria-pressed={(m === 'Auto') === stress.auto}
              className={`h-6 rounded-md px-2 text-[12px] transition-colors duration-150 ${
                (m === 'Auto') === stress.auto ? 'bg-raised text-fg' : 'text-fg-3 hover:text-fg-2'
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>
      <p className="mt-1 text-[12px] text-fg-3">Drives the selected machine with simulated readings</p>

      <div className="mt-4 grid grid-cols-2 gap-2">
        {Object.keys(FAULT_PRESETS).map(name => (
          <button
            key={name}
            onClick={() => onChange({ ...stress, ...FAULT_PRESETS[name] })}
            className="h-8 rounded-lg border border-line bg-raised text-[12px] text-fg-2 transition-colors duration-150 hover:border-line-strong hover:text-fg active:scale-[0.98]"
          >
            {name}
          </button>
        ))}
      </div>

      <div className="mt-4 space-y-4">
        <SliderField label="Temperature" unit="°C"   value={stress.temperature} min={50}   max={130}  threshold={110} onChange={(v) => onChange({ ...stress, temperature: v, active: true })} />
        <SliderField label="Vibration"   unit="mm/s" value={stress.vibration}   min={0}    max={8}    threshold={6}   onChange={(v) => onChange({ ...stress, vibration: v, active: true })} />
        <SliderField label="Speed"       unit="rpm"  value={stress.rpm}         min={1000} max={5000} threshold={4200} onChange={(v) => onChange({ ...stress, rpm: v, active: true })} />
        <SliderField label="Pressure"    unit="bar"  value={stress.pressure}    min={40}   max={130}  threshold={100} onChange={(v) => onChange({ ...stress, pressure: v, active: true })} />
      </div>

      <div className="mt-4 flex gap-2">
        <button onClick={() => onChange({ ...stress, active: !stress.active })} className={`flex-1 ${primaryButton}`}>
          {stress.active ? 'Stop test' : 'Run test'}
        </button>
        <button onClick={onReset} className={`flex-1 ${secondaryButton}`}>
          Reset
        </button>
      </div>
    </section>
  )
}

// ─── Left Column wrapper ───────────────────────────────────────────

interface LeftColumnProps {
  machines: Machine[]
  selectedId: string
  onSelect: (id: string) => void
  stress: StressConfig
  onStressChange: (s: StressConfig) => void
  onStressReset: () => void
  onAddMachine: (m: Omit<Machine, 'id' | 'sensorData' | 'history'>) => void
}

export default function LeftColumn({
  machines,
  selectedId,
  onSelect,
  stress,
  onStressChange,
  onStressReset,
  onAddMachine,
}: LeftColumnProps) {
  const [showModal, setShowModal] = useState(false)

  return (
    <aside className="flex w-full shrink-0 flex-col gap-6 border-line bg-deep p-4 lg:w-72 lg:overflow-y-auto lg:border-r">
      <section>
        <div className="mb-2 flex items-baseline justify-between px-3">
          <h3 className="text-[12px] text-fg-3">Equipment</h3>
          <span className="font-mono text-[12px] text-fg-3">{machines.length}</span>
        </div>
        <div className="flex flex-col gap-1">
          {machines.map(m => (
            <MachineCard
              key={m.id}
              machine={m}
              selected={selectedId === m.id}
              onSelect={() => onSelect(m.id)}
            />
          ))}
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="mt-2 flex h-9 w-full items-center gap-2 rounded-lg px-3 text-[13px] text-fg-2 transition-colors duration-150 hover:bg-panel hover:text-fg"
        >
          <Plus className="h-4 w-4" strokeWidth={1.5} /> Add machine
        </button>
      </section>

      <StressTestPanel stress={stress} onChange={onStressChange} onReset={onStressReset} />

      {showModal && (
        <AddMachineModal onClose={() => setShowModal(false)} onAdd={onAddMachine} />
      )}
    </aside>
  )
}
