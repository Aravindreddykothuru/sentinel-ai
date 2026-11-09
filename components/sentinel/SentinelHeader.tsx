'use client'

import { useEffect, useState } from 'react'
import { Activity, Cpu, AlertTriangle, TrendingUp, DollarSign } from 'lucide-react'

interface MetricCardProps {
  icon: React.ReactNode
  label: string
  value: string | number
  sub?: string
  color?: 'green' | 'red' | 'amber' | 'blue'
}

function MetricCard({ icon, label, value, sub, color = 'green' }: MetricCardProps) {
  const colorMap = {
    green: { border: 'border-[#00c896]/20', text: 'text-[#00c896]', glow: 'box-glow-green' },
    red:   { border: 'border-[#ef4444]/20', text: 'text-[#ef4444]', glow: 'box-glow-red' },
    amber: { border: 'border-[#e5a000]/20', text: 'text-[#e5a000]', glow: 'box-glow-amber' },
    blue:  { border: 'border-[#38bdf8]/20', text: 'text-[#38bdf8]', glow: '' },
  }
  const c = colorMap[color]
  return (
    <div className={`flex-1 bg-[#111827] border ${c.border} rounded-lg px-4 py-3 flex items-center gap-3 ${c.glow} transition-all duration-300 hover:bg-[#151c2c]`}>
      <div className={`${c.text} shrink-0 opacity-80`}>{icon}</div>
      <div className="min-w-0">
        <p className="text-[10px] text-[#64748b] tracking-widest uppercase truncate">{label}</p>
        <p className={`text-xl font-bold ${c.text} font-sans leading-tight`}>{value}</p>
        {sub && <p className="text-[10px] text-[#475569]">{sub}</p>}
      </div>
    </div>
  )
}

interface SentinelHeaderProps {
  criticalCount: number
  uptime: number
  machineCount: number
}

export default function SentinelHeader({ criticalCount, uptime, machineCount }: SentinelHeaderProps) {
  const [now, setNow] = useState<Date | null>(null)

  useEffect(() => {
    setNow(new Date())
    const t = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  const dateStr = now
    ? now.toLocaleDateString('en-US', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' })
    : '\u00A0'
  const timeStr = now
    ? now.toLocaleTimeString('en-US', { hour12: false })
    : '\u00A0'

  return (
    <header className="bg-[#0f1623] border-b border-[#1e293b] px-4 py-3 shrink-0" style={{ boxShadow: '0 1px 8px rgba(0,0,0,0.3)' }}>
      {/* Top row */}
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-lg border border-[#00c896]/30 flex items-center justify-center bg-[#00c896]/5" style={{ boxShadow: '0 0 20px rgba(0,200,150,0.1)' }}>
              <Activity className="w-4 h-4 text-[#00c896]" />
            </div>
            <div>
              <h1 className="text-[22px] font-black font-sans text-[#00c896] glow-green tracking-widest leading-none">
                SENTINEL AI
              </h1>
              <p className="text-[9px] text-[#00c896]/40 tracking-[0.3em] font-mono">PREDICTIVE MAINTENANCE v3.0</p>
            </div>
          </div>
        </div>

        {/* Center status */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#00c896] animate-pulse-dot" style={{ boxShadow: '0 0 8px rgba(0,200,150,0.6)' }} />
            <span className="text-[10px] text-[#00c896] tracking-widest">SYSTEM LIVE</span>
          </div>
          <div className="h-4 w-px bg-[#1e293b]" />
          <div className="text-right">
            <p className="text-[10px] text-[#64748b] tracking-wider">{dateStr}</p>
            <p className="text-[13px] text-[#e8ecf4] font-mono tracking-widest">{timeStr}</p>
          </div>
          <div className="h-4 w-px bg-[#1e293b]" />
          <div className="text-right">
            <p className="text-[9px] text-[#64748b] tracking-widest">FACILITY</p>
            <p className="text-[11px] text-[#38bdf8] font-sans font-bold tracking-widest">PLANT-7 NORTH</p>
          </div>
        </div>
      </div>

      {/* Metric cards */}
      <div className="flex gap-3">
        <MetricCard
          icon={<Cpu className="w-5 h-5" />}
          label="Machines Monitored"
          value={machineCount}
          sub="active sensors"
          color="green"
        />
        <MetricCard
          icon={<AlertTriangle className="w-5 h-5" />}
          label="Critical Alerts"
          value={criticalCount}
          sub="last 24h"
          color={criticalCount > 0 ? 'red' : 'green'}
        />
        <MetricCard
          icon={<TrendingUp className="w-5 h-5" />}
          label="System Uptime"
          value={`${uptime.toFixed(1)}%`}
          sub="30-day avg"
          color="green"
        />
        <MetricCard
          icon={<DollarSign className="w-5 h-5" />}
          label="Est. Annual Savings"
          value="$2.4M"
          sub="vs reactive maintenance"
          color="amber"
        />
      </div>
    </header>
  )
}
