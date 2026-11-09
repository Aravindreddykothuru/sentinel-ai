'use client'

import { useEffect, useState } from 'react'
import type { Machine } from '@/lib/sentinel-types'

interface StatProps {
  label: string
  value: string | number
  detail: string
  tone?: 'default' | 'crit' | 'warn'
}

function Stat({ label, value, detail, tone = 'default' }: StatProps) {
  const valueColor = tone === 'crit' ? 'text-crit' : tone === 'warn' ? 'text-warn' : 'text-fg'
  return (
    <div className="bg-panel border border-line rounded-xl px-5 py-4">
      <p className="text-[13px] text-fg-2">{label}</p>
      <p className={`mt-2 font-mono text-[28px] leading-none font-medium tabular-nums ${valueColor}`}>{value}</p>
      <p className="mt-2 text-[12px] text-fg-3">{detail}</p>
    </div>
  )
}

// A dial with its needle: the product's mark, flat and in one color
function DialMark() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M3.5 14.5a7.5 7.5 0 1 1 13 0" stroke="#ededed" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M10 11.5 13.5 6" stroke="#ededed" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="10" cy="11.5" r="1.5" fill="#ededed" />
    </svg>
  )
}

interface SentinelHeaderProps {
  machines: Machine[]
  criticalCount: number
  isConnected: boolean
}

export default function SentinelHeader({ machines, criticalCount, isConnected }: SentinelHeaderProps) {
  const [now, setNow] = useState<Date | null>(null)

  useEffect(() => {
    setNow(new Date())
    const t = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  const dateStr = now
    ? now.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
    : ' '
  const timeStr = now
    ? now.toLocaleTimeString('en-US', { hour12: false })
    : ' '

  const critical = machines.filter(m => m.status === 'critical').length
  const degrading = machines.filter(m => m.status === 'warning').length
  const inRange = machines.length - critical - degrading
  const avgHealth = machines.length
    ? Math.round(machines.reduce((sum, m) => sum + m.sensorData.health, 0) / machines.length)
    : 0

  return (
    <header className="shrink-0 border-b border-line bg-deep px-6 pt-4 pb-6">
      <div className="flex min-h-10 flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <div className="flex items-center gap-3 whitespace-nowrap">
          <DialMark />
          <p className="text-[17px] font-medium leading-none text-fg">Sentinel AI</p>
          <span className="h-4 w-px bg-line-strong" />
          <p className="text-[13px] text-fg-2">Plant-7 North</p>
        </div>

        <div className="flex items-center gap-4 whitespace-nowrap text-[13px]">
          <div className="flex items-center gap-2" title={isConnected ? 'Receiving live readings from the backend' : 'Waiting for the backend, showing last known data'}>
            <span className={`h-2 w-2 rounded-full ${isConnected ? 'bg-ok' : 'bg-warn'}`} />
            <span className="text-fg-2">{isConnected ? 'Live' : 'Reconnecting'}</span>
          </div>
          <span className="hidden h-4 w-px bg-line-strong sm:block" />
          <p className="hidden text-fg-3 sm:block">{dateStr}</p>
          <p className="w-[72px] font-mono tabular-nums text-fg">{timeStr}</p>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 xl:grid-cols-4">
        <Stat label="Machines monitored" value={machines.length} detail={`${inRange} within normal range`} />
        <Stat
          label="Need attention"
          value={critical + degrading}
          detail={`${critical} critical, ${degrading} degrading`}
          tone={critical > 0 ? 'crit' : degrading > 0 ? 'warn' : 'default'}
        />
        <Stat label="Average health" value={`${avgHealth}%`} detail="Across all machines, live" />
        <Stat label="Critical alerts" value={criticalCount} detail="In the alert feed" tone={criticalCount > 0 ? 'crit' : 'default'} />
      </div>
    </header>
  )
}
