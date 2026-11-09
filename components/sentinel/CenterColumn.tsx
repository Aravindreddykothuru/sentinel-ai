'use client'

import type { Machine, HistoryPoint } from '@/lib/sentinel-types'
import { useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceArea,
} from 'recharts'
import {
  SENSORS, STATUS, COLORS, BAND_COLOR, bandState, formatReading, sensorsOutOfBand, type SensorKey,
} from '@/lib/sentinel-status'

// ─── Instrument dial ───────────────────────────────────────────────
// A 240° dial: the scale, the machine's normal band on it, and a needle that turns
// warn/crit once the reading leaves that band.
const MONO = { fontFamily: 'var(--font-plex-mono)' }
const SANS = { fontFamily: 'var(--font-plex-sans)' }
const CX = 80
const CY = 76
const R = 58
const START = 150
const SWEEP = 240

function polar(angle: number, radius: number) {
  const a = (angle * Math.PI) / 180
  return [CX + radius * Math.cos(a), CY + radius * Math.sin(a)]
}

function arcPath(from: number, to: number, radius: number) {
  const [x1, y1] = polar(from, radius)
  const [x2, y2] = polar(to, radius)
  const large = to - from > 180 ? 1 : 0
  return `M ${x1} ${y1} A ${radius} ${radius} 0 ${large} 1 ${x2} ${y2}`
}

interface InstrumentProps {
  label: string
  unit: string
  value: number
  decimals: number
  scale: [number, number]
  band: { min: number; max: number }
}

function Instrument({ label, unit, value, decimals, scale, band }: InstrumentProps) {
  const [lo, hi] = scale
  const toAngle = (v: number) => START + (Math.min(hi, Math.max(lo, v)) - lo) / (hi - lo) * SWEEP
  const state = bandState(value, band)
  const needleColor = BAND_COLOR[state]
  const ticks = Array.from({ length: 25 }, (_, i) => START + (i * SWEEP) / 24)

  return (
    <div className="flex min-w-0 flex-col items-center px-2 py-4">
      <p className="text-[13px] text-fg-2">{label}</p>
      <svg viewBox="0 0 160 124" className="mt-1 w-full max-w-[176px]" role="img" aria-label={`${label} ${formatReading(value, decimals)} ${unit}, normal ${band.min} to ${band.max}`}>
        {/* Scale */}
        <path d={arcPath(START, START + SWEEP, R)} fill="none" stroke={COLORS.raised} strokeWidth="6" />
        {/* Normal band: the product's signature */}
        <path d={arcPath(toAngle(band.min), toAngle(band.max), R)} fill="none" stroke={COLORS.ok} strokeOpacity="0.45" strokeWidth="6" />
        {ticks.map((a, i) => {
          const major = i % 6 === 0
          const [x1, y1] = polar(a, major ? 44 : 47)
          const [x2, y2] = polar(a, 50)
          return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke={major ? COLORS.fg3 : COLORS.lineStrong} strokeWidth={major ? 1.5 : 1} />
        })}
        {/* Needle */}
        <g style={{ transform: `rotate(${toAngle(value)}deg)`, transformOrigin: `${CX}px ${CY}px`, transition: 'transform 400ms cubic-bezier(0.22, 1, 0.36, 1)' }}>
          <line x1={CX - 8} y1={CY} x2={CX + 52} y2={CY} stroke={needleColor} strokeWidth="2" strokeLinecap="round" style={{ transition: 'stroke 180ms' }} />
        </g>
        <circle cx={CX} cy={CY} r="5" fill={COLORS.panel} stroke={needleColor} strokeWidth="2" style={{ transition: 'stroke 180ms' }} />
        {/* Scale ends */}
        <text x={polar(START, 58)[0]} y={polar(START, 58)[1] + 16} textAnchor="middle" fontSize="11" fill={COLORS.fg3} style={MONO}>{lo}</text>
        <text x={polar(START + SWEEP, 58)[0]} y={polar(START + SWEEP, 58)[1] + 16} textAnchor="middle" fontSize="11" fill={COLORS.fg3} style={MONO}>{hi}</text>
      </svg>
      <p className="mt-1 font-mono text-[24px] font-medium leading-none tabular-nums" style={{ color: needleColor }}>
        {formatReading(value, decimals)}
        <span className="ml-1 text-[13px] font-normal text-fg-3">{unit}</span>
      </p>
      <p className="mt-2 font-mono text-[12px] text-fg-3">
        Normal {band.min}–{band.max}
      </p>
    </div>
  )
}

// ─── Digital twin: a schematic with each sensor's live reading ─────
function DigitalTwin({ machine }: { machine: Machine }) {
  const points: { key: SensorKey; x: number; y: number; anchor: 'end' | 'start' }[] = [
    { key: 'temperature', x: 120, y: 92,  anchor: 'end' },
    { key: 'vibration',   x: 280, y: 92,  anchor: 'start' },
    { key: 'pressure',    x: 120, y: 172, anchor: 'end' },
    { key: 'rpm',         x: 280, y: 172, anchor: 'start' },
  ]
  const status = STATUS[machine.status]

  return (
    <div className="flex flex-col items-center gap-4">
      <svg viewBox="0 0 400 248" className="w-full max-w-[520px]" role="img" aria-label={`Schematic of ${machine.name}`}>
        {/* Feed and outlet lines */}
        <line x1="24" y1="132" x2="120" y2="132" stroke={COLORS.lineStrong} strokeWidth="6" strokeLinecap="round" />
        <line x1="280" y1="132" x2="376" y2="132" stroke={COLORS.lineStrong} strokeWidth="6" strokeLinecap="round" />
        <line x1="200" y1="24" x2="200" y2="72" stroke={COLORS.lineStrong} strokeWidth="6" strokeLinecap="round" />
        <line x1="200" y1="192" x2="200" y2="232" stroke={COLORS.lineStrong} strokeWidth="6" strokeLinecap="round" />
        {/* Housing */}
        <rect x="120" y="72" width="160" height="120" rx="12" fill={COLORS.raised} stroke={COLORS.lineStrong} />
        {/* Rotor */}
        <circle cx="200" cy="132" r="24" fill="none" stroke={COLORS.fg3} strokeWidth="1.5" />
        <circle cx="200" cy="132" r="6" fill={COLORS.fg3} />
        {[0, 60, 120, 180, 240, 300].map(deg => {
          const a = (deg * Math.PI) / 180
          return <line key={deg} x1={200 + 8 * Math.cos(a)} y1={132 + 8 * Math.sin(a)} x2={200 + 22 * Math.cos(a)} y2={132 + 22 * Math.sin(a)} stroke={COLORS.fg3} strokeWidth="1.5" />
        })}
        {/* Sensor points with their readings */}
        {points.map(p => {
          const meta = SENSORS.find(s => s.key === p.key)!
          const value = machine.sensorData[p.key]
          const state = bandState(value, machine.normalRanges[p.key])
          const color = state === 'in' ? COLORS.ok : BAND_COLOR[state]
          const tx = p.anchor === 'end' ? p.x - 12 : p.x + 12
          return (
            <g key={p.key}>
              <circle cx={p.x} cy={p.y} r="5" fill={color} />
              <text x={tx} y={p.y - 4} textAnchor={p.anchor} fontSize="11" fill={COLORS.fg3} style={SANS}>{meta.label}</text>
              <text x={tx} y={p.y + 12} textAnchor={p.anchor} fontSize="13" fill={state === 'in' ? COLORS.fg : color} style={MONO}>
                {formatReading(value, meta.decimals)} {meta.unit}
              </text>
            </g>
          )
        })}
      </svg>
      <p className="flex items-center gap-2 text-[13px] text-fg-2">
        <span className={`h-2 w-2 rounded-full ${status.dot}`} />
        {status.label}
        {machine.status !== 'normal' && <span className="text-fg-3">· time to failure {machine.sensorData.timeToFailure}</span>}
      </p>
    </div>
  )
}

// ─── Sensor charts: risk over time, then each sensor against its band ─────
const axisTick = { fill: COLORS.fg3, fontSize: 11 }
const tooltipStyle = { background: COLORS.panel, border: `1px solid ${COLORS.lineStrong}`, borderRadius: 8, fontSize: 12, color: COLORS.fg }

function SensorCharts({ machine }: { machine: Machine }) {
  const history = machine.history

  if (history.length < 2) {
    return <p className="py-16 text-center text-[13px] text-fg-3">Collecting readings, the charts fill in every 2 seconds</p>
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <div className="mb-3 flex items-center gap-4 text-[12px]">
          <p className="text-[13px] text-fg-2">Health and failure risk</p>
          <span className="ml-auto flex items-center gap-2 text-fg-3"><span className="h-0.5 w-3 bg-signal" />Health</span>
          <span className="flex items-center gap-2 text-fg-3"><span className="h-0.5 w-3 bg-fg-3" />Failure risk</span>
        </div>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={history} margin={{ top: 4, right: 4, bottom: 0, left: -24 }}>
              <CartesianGrid stroke={COLORS.line} vertical={false} />
              <XAxis dataKey="t" hide />
              <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tick={axisTick} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={tooltipStyle} labelFormatter={() => ''} formatter={(v: number) => `${v.toFixed(0)}%`} />
              <Line type="monotone" dataKey="health" name="Health" stroke={COLORS.signal} strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="failureProbability" name="Failure risk" stroke={COLORS.fg3} strokeWidth={1.5} strokeDasharray="4 4" dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {SENSORS.filter(s => s.key !== 'rpm').map(s => {
          const band = machine.normalRanges[s.key]
          return (
            <div key={s.key} className="rounded-lg border border-line p-3">
              <div className="mb-2 flex items-baseline justify-between">
                <p className="text-[12px] text-fg-2">{s.label}</p>
                <p className="font-mono text-[12px] text-fg-3">{s.unit}</p>
              </div>
              <div className="h-24">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={history} margin={{ top: 4, right: 4, bottom: 0, left: -28 }}>
                    <ReferenceArea y1={band.min} y2={band.max} fill={COLORS.ok} fillOpacity={0.08} ifOverflow="extendDomain" />
                    <XAxis dataKey="t" hide />
                    <YAxis tick={axisTick} axisLine={false} tickLine={false} width={48} domain={['auto', 'auto']} />
                    <Tooltip contentStyle={tooltipStyle} labelFormatter={() => ''} formatter={(v: number) => `${formatReading(v, s.decimals)} ${s.unit}`} />
                    <Line type="monotone" dataKey={s.key} name={s.label} stroke={COLORS.fg2} strokeWidth={1.5} dot={false} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )
        })}
      </div>
      <p className="-mt-2 text-[12px] text-fg-3">Shaded area is the machine's normal operating range</p>
    </div>
  )
}

// ─── ROI Calculator ────────────────────────────────────────────────
function ROICalculator() {
  const [machines, setMachines] = useState(12)
  const [downtime, setDowntime] = useState(48)
  const [hourCost, setHourCost] = useState(25000)

  const annualLoss = machines * downtime * hourCost
  const savings = annualLoss * 0.72
  const roi = savings / (machines * 15000)

  const sliders = [
    { label: 'Machines', value: machines, display: `${machines}`, min: 1, max: 200, step: 1, set: setMachines },
    { label: 'Downtime per machine, hours a year', value: downtime, display: `${downtime} h`, min: 1, max: 200, step: 1, set: setDowntime },
    { label: 'Cost of an hour of downtime', value: hourCost, display: `$${(hourCost / 1000).toFixed(0)}K`, min: 1000, max: 100000, step: 1000, set: setHourCost },
  ]

  return (
    <div className="grid gap-6 md:grid-cols-[1fr_280px]">
      <div className="space-y-5">
        {sliders.map(s => {
          const pct = ((s.value - s.min) / (s.max - s.min)) * 100
          return (
            <div key={s.label}>
              <div className="mb-2 flex items-baseline justify-between">
                <span className="text-[13px] text-fg-2">{s.label}</span>
                <span className="font-mono text-[13px] tabular-nums text-fg">{s.display}</span>
              </div>
              <input
                type="range" min={s.min} max={s.max} step={s.step} value={s.value} aria-label={s.label}
                onChange={(e) => s.set(Number(e.target.value))}
                className="w-full"
                style={{ background: `linear-gradient(to right, ${COLORS.fg2} ${pct}%, ${COLORS.raised} ${pct}%)` }}
              />
            </div>
          )
        })}
      </div>
      <div className="flex flex-col gap-3">
        <div className="rounded-xl border border-line bg-deep p-4">
          <p className="text-[13px] text-fg-2">Estimated annual savings</p>
          <p className="mt-2 font-mono text-[28px] font-medium leading-none tabular-nums text-fg">${(savings / 1_000_000).toFixed(1)}M</p>
        </div>
        <div className="rounded-xl border border-line bg-deep p-4">
          <p className="text-[13px] text-fg-2">Return on cost</p>
          <p className="mt-2 font-mono text-[28px] font-medium leading-none tabular-nums text-fg">{roi.toFixed(1)}×</p>
        </div>
        <p className="text-[12px] leading-5 text-fg-3">Assumes 72% of downtime is prevented and $15K to set up each machine</p>
      </div>
    </div>
  )
}

// ─── Assessment: what the live readings say, in plain words ────────
function Assessment({ machine }: { machine: Machine }) {
  const out = sensorsOutOfBand(machine)
  const outList = out.map(s => s.label).join(', ')
  const status = STATUS[machine.status]

  const msg = machine.status === 'critical'
    ? `${machine.name} is outside its normal range on ${outList || 'several sensors'}. Failure risk is ${machine.sensorData.failureProbability.toFixed(0)}% with an estimated ${machine.sensorData.timeToFailure} to failure. The Gemini diagnosis and recommended action are in the alert feed.`
    : machine.status === 'warning'
    ? `${machine.name} is drifting${outList ? `: ${outList} above normal` : ''}. Failure risk is ${machine.sensorData.failureProbability.toFixed(0)}%. Plan an inspection before it reaches the alarm limits.`
    : `All four sensors on ${machine.name} are within their normal ranges.`

  return (
    <section className="rounded-xl border border-line bg-panel p-5">
      <div className="flex items-center gap-2">
        <span className={`h-2 w-2 rounded-full ${status.dot}`} />
        <h3 className="text-[14px] font-medium text-fg">Assessment</h3>
      </div>
      <p className="mt-2 max-w-[72ch] text-[14px] leading-6 text-fg-2">{msg}</p>
      <p className="mt-3 font-mono text-[12px] text-fg-3">Live readings every 2 s · threshold analysis every 60 s · diagnosis by Gemini</p>
    </section>
  )
}

// ─── Center Column ─────────────────────────────────────────────────
interface CenterColumnProps {
  machine: Machine
}

type Tab = 'twin' | 'charts' | 'roi'

export default function CenterColumn({ machine }: CenterColumnProps) {
  const [tab, setTab] = useState<Tab>('twin')
  const sd = machine.sensorData
  const status = STATUS[machine.status]
  const health = Math.max(0, Math.min(100, sd.health))
  const healthColor = health < 40 ? COLORS.crit : health < 70 ? COLORS.warn : COLORS.fg2

  return (
    <main className="flex min-w-0 flex-1 flex-col gap-6 bg-page p-6 lg:overflow-y-auto">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-medium leading-tight text-fg">{machine.name}</h1>
          <p className="mt-1 text-[14px] text-fg-2">{machine.type} · {machine.location}</p>
        </div>
        <p className="flex items-center gap-2 text-[14px]">
          <span className={`h-2 w-2 rounded-full ${status.dot}`} />
          <span className={status.text}>{status.label}</span>
        </p>
      </div>

      {/* Instrument cluster */}
      <section className="rounded-2xl border border-line bg-panel" aria-label="Live sensor instruments">
        <div className="grid grid-cols-2 divide-line md:grid-cols-4 md:divide-x">
          {SENSORS.map(s => (
            <Instrument
              key={s.key}
              label={s.label}
              unit={s.unit}
              value={sd[s.key]}
              decimals={s.decimals}
              scale={s.scale}
              band={machine.normalRanges[s.key]}
            />
          ))}
        </div>
        <div className="grid grid-cols-1 gap-4 border-t border-line px-5 py-4 sm:grid-cols-[1fr_auto_auto] sm:items-center sm:gap-8">
          <div className="flex items-center gap-3">
            <span className="w-24 shrink-0 text-[13px] text-fg-2">Health score</span>
            <div className="h-1 flex-1 overflow-hidden rounded-full bg-raised">
              <div className="h-full w-full origin-left rounded-full transition-transform duration-300 ease-out-quint" style={{ transform: `scaleX(${health / 100})`, backgroundColor: healthColor }} />
            </div>
            <span className="w-10 text-right font-mono text-[14px] tabular-nums text-fg">{health.toFixed(0)}</span>
          </div>
          <p className="text-[13px] text-fg-2">Failure risk <span className="ml-1 font-mono tabular-nums text-fg">{sd.failureProbability.toFixed(0)}%</span></p>
          <p className="text-[13px] text-fg-2">Time to failure <span className="ml-1 font-mono text-fg">{sd.timeToFailure}</span></p>
        </div>
      </section>

      {/* Tabs */}
      <section className="rounded-2xl border border-line bg-panel">
        <div className="flex gap-1 border-b border-line px-3 pt-2" role="tablist">
          {([['twin', 'Digital twin'], ['charts', 'Sensor charts'], ['roi', 'ROI calculator']] as [Tab, string][]).map(([key, lbl]) => (
            <button
              key={key}
              role="tab"
              aria-selected={tab === key}
              onClick={() => setTab(key)}
              className={`-mb-px h-10 border-b-2 px-3 text-[13px] transition-colors duration-150 ${
                tab === key ? 'border-signal text-fg' : 'border-transparent text-fg-3 hover:text-fg-2'
              }`}
            >
              {lbl}
            </button>
          ))}
        </div>
        <div key={tab} className="animate-enter p-5">
          {tab === 'twin'   && <DigitalTwin machine={machine} />}
          {tab === 'charts' && <SensorCharts machine={machine} />}
          {tab === 'roi'    && <ROICalculator />}
        </div>
      </section>

      <Assessment machine={machine} />
    </main>
  )
}
