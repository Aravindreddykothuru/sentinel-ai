'use client'

import type { Machine, HistoryPoint } from '@/lib/sentinel-types'
import { useState } from 'react'
import {
  AreaChart, Area, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts'
import { Thermometer, Zap, Gauge, Activity } from 'lucide-react'

// ─── Circular Gauge ────────────────────────────────────────────────
interface CircularGaugeProps {
  label: string
  value: number
  unit: string
  min: number
  max: number
  threshold: number
  icon: React.ReactNode
}

function CircularGauge({ label, value, unit, min, max, threshold, icon }: CircularGaugeProps) {
  const pct = Math.min(1, Math.max(0, (value - min) / (max - min)))
  const isOver = value > threshold
  const color = isOver ? '#ef4444' : pct > 0.75 ? '#e5a000' : '#00c896'
  const r = 36
  const circumference = Math.PI * r  // half-circle
  const offset = circumference - pct * circumference

  return (
    <div className="flex flex-col items-center bg-[#111827] border border-[#1e293b] rounded-lg p-3 flex-1" style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.02)' }}>
      <p className="text-[9px] text-[#64748b] tracking-widest uppercase mb-1">{label}</p>
      <div className="relative">
        <svg width="88" height="52" viewBox="0 0 88 52">
          {/* Track */}
          <path
            d="M 8 48 A 36 36 0 0 1 80 48"
            fill="none"
            stroke="#1e293b"
            strokeWidth="7"
            strokeLinecap="round"
          />
          {/* Value arc */}
          <path
            d="M 8 48 A 36 36 0 0 1 80 48"
            fill="none"
            stroke={color}
            strokeWidth="7"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{
              transition: 'stroke-dashoffset 0.5s ease, stroke 0.3s ease',
              filter: `drop-shadow(0 0 6px ${color}50)`,
            }}
          />
          {/* Icon */}
          <foreignObject x="36" y="10" width="16" height="16">
            <div className="text-[#64748b]" style={{ transform: 'scale(0.7)' }}>
              {icon}
            </div>
          </foreignObject>
        </svg>
        <div className="absolute bottom-0 left-0 right-0 text-center">
          <span className={`text-[18px] font-bold font-sans leading-none`} style={{ color }}>
            {value.toFixed(value < 100 ? 1 : 0)}
          </span>
          <span className="text-[9px] text-[#64748b] ml-0.5">{unit}</span>
        </div>
      </div>
      <div className="flex items-center gap-1 mt-1">
        {isOver && <span className="text-[9px] text-[#ef4444] font-bold animate-pulse-dot">OVER THRESHOLD</span>}
        {!isOver && <span className="text-[9px] text-[#475569]">Thresh: {threshold}{unit}</span>}
      </div>
    </div>
  )
}

// ─── Digital Twin SVG ──────────────────────────────────────────────
function DigitalTwin({ machine }: { machine: Machine }) {
  const h = machine.sensorData.health
  const bodyColor = h > 70 ? '#00c896' : h > 40 ? '#e5a000' : '#ef4444'
  const isCritical = machine.status === 'critical'
  const statusLabel = machine.status === 'critical' ? 'CRITICAL \u2014 FAILURE IMMINENT' : machine.status === 'warning' ? 'DEGRADING \u2014 MONITOR CLOSELY' : 'OPERATING NORMALLY'

  return (
    <div className="flex flex-col items-center gap-3">
      <svg width="320" height="220" viewBox="0 0 320 220" className="w-full max-w-sm">
        {/* Background grid */}
        <defs>
          <pattern id="twinGrid" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(0,200,150,0.03)" strokeWidth="0.5"/>
          </pattern>
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
        </defs>
        <rect width="320" height="220" fill="url(#twinGrid)" rx="8" />

        {/* Machine body */}
        <rect
          x="90" y="70" width="140" height="100" rx="10"
          fill={`${bodyColor}12`}
          stroke={bodyColor}
          strokeWidth="1.5"
          filter="url(#glow)"
          style={{ transition: 'fill 0.5s, stroke 0.5s' }}
        />

        {/* Rotating gear */}
        <g transform="translate(160, 120)">
          <circle r="18" fill="none" stroke={bodyColor} strokeWidth="1.5" opacity="0.5" />
          <circle r="6" fill={bodyColor} opacity="0.7" />
          {[0,45,90,135,180,225,270,315].map((deg) => (
            <rect
              key={deg}
              x="-3" y="-24"
              width="6" height="8"
              rx="2"
              fill={bodyColor}
              transform={`rotate(${deg})`}
              style={{ transition: 'fill 0.4s' }}
            />
          ))}
          <animateTransform
            attributeName="transform"
            type="rotate"
            from="0 0 0"
            to="360 0 0"
            dur={isCritical ? '0.8s' : '3s'}
            repeatCount="indefinite"
            additive="sum"
          />
        </g>

        {/* Pipes */}
        <line x1="20" y1="120" x2="90" y2="120" stroke="#1e293b" strokeWidth="8" strokeLinecap="round" />
        <line x1="20" y1="120" x2="90" y2="120" stroke={bodyColor} strokeWidth="2"
          strokeDasharray="6 4" opacity="0.6">
          <animate attributeName="stroke-dashoffset" from="20" to="0" dur="1s" repeatCount="indefinite" />
        </line>
        <line x1="230" y1="120" x2="300" y2="120" stroke="#1e293b" strokeWidth="8" strokeLinecap="round" />
        <line x1="230" y1="120" x2="300" y2="120" stroke={bodyColor} strokeWidth="2"
          strokeDasharray="6 4" opacity="0.6">
          <animate attributeName="stroke-dashoffset" from="0" to="20" dur="1s" repeatCount="indefinite" />
        </line>
        <line x1="160" y1="20" x2="160" y2="70" stroke="#1e293b" strokeWidth="8" strokeLinecap="round" />
        <line x1="160" y1="20" x2="160" y2="70" stroke={bodyColor} strokeWidth="2"
          strokeDasharray="6 4" opacity="0.6">
          <animate attributeName="stroke-dashoffset" from="20" to="0" dur="0.7s" repeatCount="indefinite" />
        </line>
        <line x1="160" y1="170" x2="160" y2="210" stroke="#1e293b" strokeWidth="8" strokeLinecap="round" />
        <line x1="160" y1="170" x2="160" y2="210" stroke={bodyColor} strokeWidth="2"
          strokeDasharray="6 4" opacity="0.6">
          <animate attributeName="stroke-dashoffset" from="0" to="20" dur="0.7s" repeatCount="indefinite" />
        </line>

        {/* Sensor dots */}
        {[
          { cx: 90,  cy: 88,  label: 'TEMP', sensor: 'temperature', normal: machine.sensorData.temperature < (machine.normalRanges?.temperature?.max ?? 100) },
          { cx: 230, cy: 88,  label: 'VIB',  sensor: 'vibration',   normal: machine.sensorData.vibration   < (machine.normalRanges?.vibration?.max ?? 3)   },
          { cx: 90,  cy: 158, label: 'PRES', sensor: 'pressure',    normal: machine.sensorData.pressure    < (machine.normalRanges?.pressure?.max ?? 100)  },
          { cx: 230, cy: 158, label: 'RPM',  sensor: 'rpm',         normal: machine.sensorData.rpm         < (machine.normalRanges?.rpm?.max ?? 3500)      },
        ].map(({ cx, cy, label, normal }) => (
          <g key={label}>
            <circle cx={cx} cy={cy} r="8" fill={normal ? '#00c896' : '#ef4444'} opacity="0.15" />
            <circle cx={cx} cy={cy} r="4" fill={normal ? '#00c896' : '#ef4444'} />
            <text x={cx} y={cy - 12} textAnchor="middle" fontSize="8" fill="#64748b" fontFamily="monospace">
              {label}
            </text>
          </g>
        ))}
      </svg>

      <div className={`text-[11px] font-sans font-bold tracking-widest px-4 py-1.5 rounded-lg border ${
        machine.status === 'critical' ? 'bg-[#ef4444]/10 border-[#ef4444]/30 text-[#ef4444]' :
        machine.status === 'warning'  ? 'bg-[#e5a000]/10 border-[#e5a000]/30 text-[#e5a000]' :
                                        'bg-[#00c896]/10 border-[#00c896]/30 text-[#00c896]'
      }`}>
        {statusLabel}
      </div>
    </div>
  )
}

// ─── Sensor Charts ─────────────────────────────────────────────────
function SensorCharts({ history }: { history: HistoryPoint[] }) {
  return (
    <div className="flex flex-col gap-4">
      {/* Health + Failure Probability */}
      <div>
        <p className="text-[10px] text-[#64748b] tracking-widest mb-2">HEALTH % vs FAILURE PROBABILITY %</p>
        <div className="h-40">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={history} margin={{ top: 5, right: 5, bottom: 0, left: -20 }}>
              <defs>
                <linearGradient id="healthGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#00c896" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#00c896" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="failGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#ef4444" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
              <XAxis dataKey="t" hide />
              <YAxis domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 9 }} />
              <Tooltip contentStyle={{ background: '#111827', border: '1px solid #1e293b', fontSize: 11, color: '#e8ecf4', borderRadius: 8 }} />
              <Area type="monotone" dataKey="health" name="Health %" stroke="#00c896" fill="url(#healthGrad)" strokeWidth={2} dot={false} />
              <Area type="monotone" dataKey="failureProbability" name="Fail Prob %" stroke="#ef4444" fill="url(#failGrad)" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
      {/* Temp / Pressure / Vibration */}
      <div>
        <p className="text-[10px] text-[#64748b] tracking-widest mb-2">TEMPERATURE / PRESSURE / VIBRATION</p>
        <div className="h-40">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={history} margin={{ top: 5, right: 5, bottom: 0, left: -20 }}>
              <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
              <XAxis dataKey="t" hide />
              <YAxis tick={{ fill: '#64748b', fontSize: 9 }} />
              <Tooltip contentStyle={{ background: '#111827', border: '1px solid #1e293b', fontSize: 11, color: '#e8ecf4', borderRadius: 8 }} />
              <Legend iconSize={8} wrapperStyle={{ fontSize: 10, color: '#64748b' }} />
              <Line type="monotone" dataKey="temperature" name="Temp °C" stroke="#ef4444" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="pressure"    name="Press bar" stroke="#38bdf8" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="vibration"   name="Vib mm/s" stroke="#e5a000" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
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

  return (
    <div className="space-y-4">
      <p className="text-[10px] text-[#64748b] tracking-widest">ADJUST PARAMETERS TO CALCULATE ROI</p>

      <div>
        <div className="flex justify-between mb-1">
          <span className="text-[11px] text-[#94a3b8]">Number of Machines</span>
          <span className="text-[13px] font-bold text-[#e5a000] font-mono">{machines}</span>
        </div>
        <input type="range" min={1} max={200} value={machines} onChange={(e) => setMachines(Number(e.target.value))}
          className="w-full range-amber" style={{ background: `linear-gradient(to right, #e5a000 ${machines/2}%, #1e293b ${machines/2}%)` }} />
      </div>

      <div>
        <div className="flex justify-between mb-1">
          <span className="text-[11px] text-[#94a3b8]">Avg Downtime Hours / Year</span>
          <span className="text-[13px] font-bold text-[#e5a000] font-mono">{downtime}h</span>
        </div>
        <input type="range" min={1} max={200} value={downtime} onChange={(e) => setDowntime(Number(e.target.value))}
          className="w-full range-amber" style={{ background: `linear-gradient(to right, #e5a000 ${downtime/2}%, #1e293b ${downtime/2}%)` }} />
      </div>

      <div>
        <div className="flex justify-between mb-1">
          <span className="text-[11px] text-[#94a3b8]">Hourly Downtime Cost</span>
          <span className="text-[13px] font-bold text-[#e5a000] font-mono">${(hourCost/1000).toFixed(0)}K</span>
        </div>
        <input type="range" min={1000} max={100000} step={1000} value={hourCost} onChange={(e) => setHourCost(Number(e.target.value))}
          className="w-full range-amber" style={{ background: `linear-gradient(to right, #e5a000 ${(hourCost-1000)/990}%, #1e293b ${(hourCost-1000)/990}%)` }} />
      </div>

      <div className="grid grid-cols-2 gap-3 pt-2">
        <div className="bg-[#0a0e17] border border-[#e5a000]/20 rounded-lg p-3 text-center" style={{ boxShadow: '0 0 20px rgba(229,160,0,0.05)' }}>
          <p className="text-[9px] text-[#64748b] tracking-widest mb-1">ANNUAL SAVINGS</p>
          <p className="text-[22px] font-bold font-sans text-[#e5a000] glow-amber">${(savings/1_000_000).toFixed(1)}M</p>
          <p className="text-[9px] text-[#475569]">72% of prevented loss</p>
        </div>
        <div className="bg-[#0a0e17] border border-[#00c896]/20 rounded-lg p-3 text-center" style={{ boxShadow: '0 0 20px rgba(0,200,150,0.05)' }}>
          <p className="text-[9px] text-[#64748b] tracking-widest mb-1">ROI MULTIPLE</p>
          <p className="text-[22px] font-bold font-sans text-[#00c896] glow-green">{roi.toFixed(1)}x</p>
          <p className="text-[9px] text-[#475569]">vs implementation cost</p>
        </div>
      </div>
    </div>
  )
}

// ─── AI Insight Banner ─────────────────────────────────────────────
function AIInsightBanner({ machine }: { machine: Machine }) {
  const isCritical = machine.status === 'critical'
  const isWarning  = machine.status === 'warning'

  const msg = isCritical
    ? `CRITICAL: ${machine.name} exhibits cascading failure pattern \u2014 elevated vibration (${machine.sensorData.vibration.toFixed(1)} mm/s) combined with thermal spike indicates bearing degradation. Isolation Forest anomaly score: 0.94. Estimated failure in ${machine.sensorData.timeToFailure}. Immediate shutdown recommended.`
    : isWarning
    ? `WARNING: Early degradation detected in ${machine.name}. Temperature trending ${((machine.sensorData.temperature / (machine.normalRanges?.temperature?.max ?? 100)) * 100).toFixed(0)}% of max threshold. Autoencoder reconstruction error rising. Schedule inspection within 48\u201372 hours.`
    : `${machine.name} is operating within normal parameters. All sensor readings nominal. Autoencoder reconstruction error: 0.012. No anomalies detected. Next scheduled maintenance in 14 days.`

  return (
    <div className={`rounded-lg p-3 flex items-start gap-3 border ${
      isCritical ? 'bg-[#ef4444]/5 border-[#ef4444]/20' :
      isWarning  ? 'bg-[#e5a000]/5 border-[#e5a000]/20' :
                   'bg-[#38bdf8]/5 border-[#38bdf8]/20'
    }`}
      style={{ background: isCritical ? 'linear-gradient(135deg, rgba(239,68,68,0.06) 0%, rgba(0,200,150,0.02) 100%)' : isWarning ? 'linear-gradient(135deg, rgba(229,160,0,0.06) 0%, rgba(0,200,150,0.02) 100%)' : 'linear-gradient(135deg, rgba(56,189,248,0.06) 0%, rgba(0,200,150,0.02) 100%)' }}
    >
      <Zap className={`w-4 h-4 shrink-0 mt-0.5 ${isCritical ? 'text-[#ef4444]' : isWarning ? 'text-[#e5a000]' : 'text-[#38bdf8]'}`} />
      <div className="flex-1 min-w-0">
        <p className="text-[11px] text-[#cbd5e1] leading-relaxed">{msg}</p>
        <p className="text-[9px] text-[#475569] mt-1">
          Model Confidence: <span className="text-[#38bdf8]">94.7%</span>
          <span className="mx-2 text-[#1e293b]">|</span>
          <span className="text-[#64748b]">Isolation Forest + Keras Autoencoder</span>
        </p>
      </div>
    </div>
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

  return (
    <main className="flex-1 flex flex-col gap-3 overflow-y-auto min-w-0 p-3 bg-[#0a0e17]">
      {/* Machine title */}
      <div>
        <h2 className="text-[20px] font-black font-sans text-[#e8ecf4] tracking-widest leading-none">
          {machine.name.toUpperCase()}
        </h2>
        <p className="text-[10px] text-[#38bdf8] tracking-[0.25em] mt-0.5">REAL-TIME SENSOR TELEMETRY — {machine.type} — {machine.location}</p>
      </div>

      {/* 4 gauges */}
      <div className="flex gap-2">
        <CircularGauge label="Temperature" value={sd.temperature} unit="°C"   min={20}  max={150}  threshold={machine.normalRanges?.temperature?.max ?? 100} icon={<Thermometer className="w-4 h-4" />} />
        <CircularGauge label="Vibration"   value={sd.vibration}   unit="mm/s" min={0}   max={10}   threshold={machine.normalRanges?.vibration?.max ?? 3}   icon={<Activity className="w-4 h-4" />} />
        <CircularGauge label="RPM"         value={sd.rpm}         unit="rpm"  min={500} max={5500} threshold={machine.normalRanges?.rpm?.max ?? 3500}         icon={<Gauge className="w-4 h-4" />} />
        <CircularGauge label="Pressure"    value={sd.pressure}    unit="bar"  min={20}  max={140}  threshold={machine.normalRanges?.pressure?.max ?? 100}    icon={<Activity className="w-4 h-4" />} />
      </div>

      {/* ML Confidence */}
      <div className="bg-[#111827] border border-[#1e293b] rounded-lg px-4 py-2 flex items-center gap-3" style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.02)' }}>
        <span className="text-[10px] text-[#64748b] tracking-widest shrink-0">ML CONFIDENCE</span>
        <div className="flex-1 h-1.5 bg-[#1e293b] rounded-full overflow-hidden">
          <div className="h-full bg-[#38bdf8] rounded-full" style={{ width: '94.7%', boxShadow: '0 0 10px rgba(56,189,248,0.3)' }} />
        </div>
        <span className="text-[13px] font-bold text-[#38bdf8] font-mono">94.7%</span>
        <span className="text-[10px] text-[#475569] shrink-0">Isolation Forest + Keras Autoencoder</span>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-[#111827] border border-[#1e293b] rounded-lg p-1" style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.02)' }}>
        {([['twin','Digital Twin'],['charts','Sensor Charts'],['roi','ROI Calculator']] as [Tab, string][]).map(([key, lbl]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex-1 text-[11px] py-2 rounded-md font-sans tracking-wider transition-all ${
              tab === key
                ? 'bg-[#00c896]/10 text-[#00c896] border border-[#00c896]/25'
                : 'text-[#64748b] hover:text-[#94a3b8]'
            }`}
          >
            {lbl}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="bg-[#111827] border border-[#1e293b] rounded-lg p-4 animate-fadeInUp" style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.02)' }}>
        {tab === 'twin'   && <DigitalTwin machine={machine} />}
        {tab === 'charts' && <SensorCharts history={machine.history} />}
        {tab === 'roi'    && <ROICalculator />}
      </div>

      {/* AI Insight Banner */}
      <AIInsightBanner machine={machine} />
    </main>
  )
}
