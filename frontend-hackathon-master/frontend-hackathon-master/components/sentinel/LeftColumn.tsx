'use client'

import { useState, useEffect } from 'react'
import { Plus, X } from 'lucide-react'
import type { Machine, StressConfig } from '@/lib/sentinel-types'

// ─── Health Ring ───────────────────────────────────────────────────
function HealthRing({ health }: { health: number }) {
  const r = 18
  const circumference = 2 * Math.PI * r
  const color = health > 70 ? '#00c896' : health > 40 ? '#e5a000' : '#ef4444'
  const offset = circumference - (health / 100) * circumference
  return (
    <svg width="44" height="44" className="shrink-0">
      <circle cx="22" cy="22" r={r} fill="none" stroke="#1e293b" strokeWidth="4" />
      <circle
        cx="22"
        cy="22"
        r={r}
        fill="none"
        stroke={color}
        strokeWidth="4"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform="rotate(-90 22 22)"
        style={{ transition: 'stroke-dashoffset 0.6s ease, stroke 0.4s ease', filter: `drop-shadow(0 0 6px ${color}50)` }}
      />
      <text x="22" y="27" textAnchor="middle" fontSize="10" fill={color} fontFamily="monospace" fontWeight="bold">
        {health}
      </text>
    </svg>
  )
}

// ─── Machine Card ──────────────────────────────────────────────────
interface MachineCardProps {
  machine: Machine
  selected: boolean
  onSelect: () => void
}

export function MachineCard({ machine, selected, onSelect }: MachineCardProps) {
  const statusColors = {
    normal:    { dot: 'bg-[#00c896]',  border: 'border-[#00c896]/20', bg: selected ? 'bg-[#00c896]/8' : 'bg-[#111827]' },
    warning:   { dot: 'bg-[#e5a000]',  border: 'border-[#e5a000]/20', bg: selected ? 'bg-[#e5a000]/8' : 'bg-[#111827]' },
    critical:  { dot: 'bg-[#ef4444]',  border: 'border-[#ef4444]/20', bg: selected ? 'bg-[#ef4444]/8' : 'bg-[#111827]' },
  }
  const s = statusColors[machine.status]
  const failProb = machine.sensorData.failureProbability

  return (
    <button
      onClick={onSelect}
      className={`w-full text-left ${s.bg} border ${s.border} rounded-lg p-3 transition-all duration-200 hover:bg-[#192133] ${selected ? 'ring-1 ring-inset ring-[#00c896]/30' : ''}`}
      style={selected ? { boxShadow: '0 0 15px rgba(0,200,150,0.06), inset 0 1px 0 rgba(255,255,255,0.02)' } : { boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.02)' }}
    >
      <div className="flex items-center gap-2 mb-2">
        <span className={`w-2 h-2 rounded-full ${s.dot} animate-pulse-dot shrink-0`} />
        <span className="text-[11px] font-sans font-bold text-[#e8ecf4] truncate">{machine.name}</span>
        <span className="ml-auto text-[9px] text-[#64748b] shrink-0">{machine.location}</span>
      </div>
      <div className="flex items-center gap-2">
        <HealthRing health={machine.sensorData.health} />
        <div className="flex-1 min-w-0">
          <p className="text-[9px] text-[#64748b] truncate">{machine.type}</p>
          <div className="flex items-center gap-1 mt-1">
            <span className="text-[9px] text-[#64748b]">Fail Prob:</span>
            <span className={`text-[11px] font-bold font-mono ${failProb > 50 ? 'text-[#ef4444] glow-red' : failProb > 30 ? 'text-[#e5a000]' : 'text-[#00c896]'}`}>
              {failProb.toFixed(1)}%
            </span>
          </div>
          <p className="text-[9px] text-[#64748b] mt-0.5">TTF: {machine.sensorData.timeToFailure}</p>
        </div>
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
  const cls = isOver ? 'range-red' : value > threshold * 0.85 ? 'range-amber' : ''
  return (
    <div className="mb-2">
      <div className="flex justify-between items-center mb-1">
        <span className="text-[10px] text-[#64748b]">{label}</span>
        <div className="flex items-center gap-1">
          <span className={`text-[11px] font-mono font-bold ${isOver ? 'text-[#ef4444]' : 'text-[#e8ecf4]'}`}>
            {value.toFixed(0)}<span className="text-[9px] text-[#64748b] ml-0.5">{unit}</span>
          </span>
          <span className="text-[9px] text-[#475569]">/ {threshold}{unit}</span>
        </div>
      </div>
      <div className="relative">
        <input
          type="range"
          min={min}
          max={max}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className={`w-full ${cls}`}
          style={{
            background: `linear-gradient(to right, ${isOver ? '#ef4444' : '#00c896'} ${pct}%, #1e293b ${pct}%)`,
          }}
        />
      </div>
    </div>
  )
}

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
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#111827] border border-[#1e293b] rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto" style={{ boxShadow: '0 25px 60px rgba(0,0,0,0.5), 0 0 40px rgba(0,200,150,0.05)' }}>
        <div className="flex items-center justify-between p-4 border-b border-[#1e293b]">
          <h2 className="text-[14px] font-sans font-bold text-[#00c896] tracking-widest">ADD NEW MACHINE</h2>
          <button onClick={onClose} className="text-[#64748b] hover:text-[#e8ecf4] transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-4 space-y-4">
          {/* Basic info */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] text-[#64748b] tracking-wider block mb-1">MACHINE NAME</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Pump Delta"
                className="w-full bg-[#0a0e17] border border-[#1e293b] text-[#e8ecf4] text-[12px] rounded-lg px-3 py-2 focus:outline-none focus:border-[#00c896]/50 placeholder-[#475569] transition-colors"
              />
            </div>
            <div>
              <label className="text-[10px] text-[#64748b] tracking-wider block mb-1">LOCATION</label>
              <input
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g. Bay 5"
                className="w-full bg-[#0a0e17] border border-[#1e293b] text-[#e8ecf4] text-[12px] rounded-lg px-3 py-2 focus:outline-none focus:border-[#00c896]/50 placeholder-[#475569] transition-colors"
              />
            </div>
          </div>
          <div>
            <label className="text-[10px] text-[#64748b] tracking-wider block mb-1">MACHINE TYPE</label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="w-full bg-[#0a0e17] border border-[#1e293b] text-[#e8ecf4] text-[12px] rounded-lg px-3 py-2 focus:outline-none focus:border-[#00c896]/50"
            >
              {['Gas Turbine','Air Compressor','Hydraulic Pump','Drive Motor','Heat Exchanger','Conveyor Drive','CNC Spindle'].map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          {/* Industry presets */}
          <div>
            <label className="text-[10px] text-[#64748b] tracking-wider block mb-2">INDUSTRY PRESET</label>
            <div className="flex flex-wrap gap-2">
              {Object.keys(PRESETS).map(p => (
                <button
                  key={p}
                  onClick={() => applyPreset(p)}
                  className={`text-[10px] px-3 py-1.5 rounded-lg border transition-all ${
                    preset === p
                      ? 'bg-[#00c896]/10 border-[#00c896]/40 text-[#00c896]'
                      : 'bg-[#0a0e17] border-[#1e293b] text-[#64748b] hover:border-[#00c896]/20 hover:text-[#94a3b8]'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          {/* Operating ranges */}
          <div>
            <p className="text-[10px] text-[#64748b] tracking-widest mb-2">NORMAL OPERATING RANGES</p>
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'Temp Min (\u00B0C)', key: 'tempMin' },
                { label: 'Temp Max (\u00B0C)', key: 'tempMax' },
                { label: 'Vib Min (mm/s)', key: 'vibMin'  },
                { label: 'Vib Max (mm/s)', key: 'vibMax'  },
                { label: 'RPM Min',        key: 'rpmMin'  },
                { label: 'RPM Max',        key: 'rpmMax'  },
                { label: 'Press Min (bar)', key: 'presMin' },
                { label: 'Press Max (bar)', key: 'presMax' },
              ].map(({ label, key }) => (
                <div key={key}>
                  <label className="text-[9px] text-[#64748b] block mb-1">{label}</label>
                  <input
                    type="number"
                    value={(ranges as Record<string, number>)[key]}
                    onChange={(e) => setRanges(prev => ({ ...prev, [key]: Number(e.target.value) }))}
                    className="w-full bg-[#0a0e17] border border-[#1e293b] text-[#e8ecf4] text-[12px] rounded-lg px-2 py-1.5 focus:outline-none focus:border-[#00c896]/50"
                  />
                </div>
              ))}
            </div>
          </div>

          <div className="flex gap-2 pt-2">
            <button
              onClick={onClose}
              className="flex-1 bg-[#151c2c] border border-[#1e293b] text-[#64748b] text-[11px] py-2.5 rounded-lg font-sans tracking-wider hover:border-[#2d3a52] hover:text-[#94a3b8] transition-colors"
            >
              CANCEL
            </button>
            <button
              onClick={handleSave}
              disabled={!name.trim()}
              className="flex-1 bg-[#00c896]/10 border border-[#00c896]/40 text-[#00c896] text-[11px] py-2.5 rounded-lg font-sans tracking-wider hover:bg-[#00c896]/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              SAVE & START MONITORING
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
  'Bearing Fail': { vibration: 7.5, rpm: 1200, active: true },
  'Pressure Drop': { pressure: 28, active: true },
  'RPM Surge':   { rpm: 4800, active: true },
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
    <div className="bg-[#111827] border border-[#1e293b] rounded-lg p-3 mt-3" style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.02)' }}>
      <div className="flex items-center justify-between mb-3">
        <p className="text-[11px] font-sans font-bold text-[#e5a000] tracking-widest">STRESS TEST SIMULATOR</p>
        <div className="flex items-center gap-1 bg-[#0a0e17] rounded-lg border border-[#1e293b] p-0.5">
          {(['MANUAL', 'AUTO'] as const).map(m => (
            <button
              key={m}
              onClick={() => onChange({ ...stress, auto: m === 'AUTO', active: stress.active })}
              className={`text-[9px] px-2 py-1 rounded-md transition-all ${
                (m === 'AUTO') === stress.auto
                  ? 'bg-[#e5a000]/15 text-[#e5a000] border border-[#e5a000]/30'
                  : 'text-[#64748b]'
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {/* Fault presets */}
      <div className="grid grid-cols-2 gap-1.5 mb-3">
        {Object.keys(FAULT_PRESETS).map(name => (
          <button
            key={name}
            onClick={() => onChange({ ...stress, ...FAULT_PRESETS[name] })}
            className="text-[10px] bg-[#ef4444]/8 border border-[#ef4444]/20 text-[#ef4444] py-1.5 rounded-lg hover:bg-[#ef4444]/15 transition-colors"
          >
            {name}
          </button>
        ))}
      </div>

      {/* Sliders */}
      <SliderField label="Temperature" unit="°C"   value={stress.temperature} min={50}   max={130}  threshold={110} onChange={(v) => onChange({ ...stress, temperature: v, active: true })} />
      <SliderField label="Vibration"   unit="mm/s" value={stress.vibration}   min={0}    max={8}    threshold={6}   onChange={(v) => onChange({ ...stress, vibration: v, active: true })} />
      <SliderField label="RPM"         unit=""     value={stress.rpm}         min={1000} max={5000} threshold={4200} onChange={(v) => onChange({ ...stress, rpm: v, active: true })} />
      <SliderField label="Pressure"    unit="bar"  value={stress.pressure}    min={40}   max={130}  threshold={100} onChange={(v) => onChange({ ...stress, pressure: v, active: true })} />

      {/* Activate + Reset */}
      <div className="flex gap-2 mt-3">
        <button
          onClick={() => onChange({ ...stress, active: !stress.active })}
          className={`flex-1 text-[10px] py-2 rounded-lg border font-sans tracking-wider transition-all ${
            stress.active
              ? 'bg-[#ef4444]/15 border-[#ef4444]/40 text-[#ef4444]'
              : 'bg-[#e5a000]/10 border-[#e5a000]/30 text-[#e5a000]'
          }`}
        >
          {stress.active ? 'DEACTIVATE' : 'ACTIVATE TEST'}
        </button>
        <button
          onClick={onReset}
          className="flex-1 text-[10px] py-2 rounded-lg border border-[#1e293b] text-[#64748b] hover:border-[#2d3a52] hover:text-[#94a3b8] font-sans tracking-wider transition-colors"
        >
          RESET NORMAL
        </button>
      </div>
    </div>
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
    <aside className="w-[260px] lg:w-[280px] xl:w-[300px] shrink-0 flex flex-col gap-0 overflow-y-auto bg-[#0c1220]">
      {/* Equipment status */}
      <div className="p-3">
        <p className="text-[11px] font-sans font-bold text-[#38bdf8] tracking-widest mb-2 flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-[#38bdf8] animate-pulse-dot" />
          EQUIPMENT STATUS
        </p>
        <div className="flex flex-col gap-2">
          {machines.map(m => (
            <MachineCard
              key={m.id}
              machine={m}
              selected={selectedId === m.id}
              onSelect={() => onSelect(m.id)}
            />
          ))}
        </div>

        <StressTestPanel stress={stress} onChange={onStressChange} onReset={onStressReset} />

        <button
          onClick={() => setShowModal(true)}
          className="mt-3 w-full flex items-center justify-center gap-2 bg-[#00c896]/8 border border-[#00c896]/30 text-[#00c896] text-[11px] py-2.5 rounded-lg font-sans tracking-widest hover:bg-[#00c896]/15 transition-colors"
        >
          <Plus className="w-3.5 h-3.5" /> ADD NEW MACHINE
        </button>
      </div>

      {showModal && (
        <AddMachineModal onClose={() => setShowModal(false)} onAdd={onAddMachine} />
      )}
    </aside>
  )
}
