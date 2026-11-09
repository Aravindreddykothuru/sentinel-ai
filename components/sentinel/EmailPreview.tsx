'use client'

import { X } from 'lucide-react'
import type { Machine, Mechanic } from '@/lib/sentinel-types'
import { SENSORS, STATUS, formatReading } from '@/lib/sentinel-status'

interface EmailPreviewProps {
  isOpen: boolean
  machine: Machine | null
  mechanic: Mechanic | null
  onClose: () => void
}

export function EmailPreview({ isOpen, machine, mechanic, onClose }: EmailPreviewProps) {
  if (!isOpen || !machine || !mechanic) return null

  const status = STATUS[machine.status]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div role="dialog" aria-modal="true" aria-labelledby="email-preview-title" className="animate-enter max-h-[80vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-line bg-panel shadow-[0_24px_64px_rgba(0,0,0,0.5)]">
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-line bg-panel px-6 py-4">
          <h2 id="email-preview-title" className="text-[16px] font-medium text-fg">Alert email preview</h2>
          <button onClick={onClose} aria-label="Close" className="rounded-md p-1 text-fg-3 transition-colors duration-150 hover:text-fg">
            <X className="h-4 w-4" strokeWidth={1.5} />
          </button>
        </div>

        <div className="space-y-4 p-6">
          <div className="rounded-xl border border-line bg-deep p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[16px] font-medium text-fg">Sentinel AI</p>
                <p className="text-[12px] text-fg-3">Plant-7 North</p>
              </div>
              <p className="font-mono text-[12px] text-fg-3">To {mechanic.email}</p>
            </div>
            <div className="mt-6 border-t border-line pt-6">
              <p className="flex items-center gap-2 text-[16px] font-medium text-fg">
                <span className={`h-2 w-2 rounded-full ${status.dot}`} />
                {status.label}: {machine.name}
              </p>
              <p className="mt-4 text-[14px] text-fg">Hi {mechanic.name},</p>
              <p className="mt-2 text-[14px] leading-6 text-fg-2">
                {machine.name} in {machine.location} needs inspection. Its readings are outside the normal operating range and the failure risk is {machine.sensorData.failureProbability.toFixed(0)}%.
              </p>
            </div>
          </div>

          <div className="rounded-xl border border-line bg-deep p-5">
            <p className="text-[13px] text-fg-2">Current readings</p>
            <div className="mt-3 grid grid-cols-2 gap-4">
              {SENSORS.map(s => (
                <div key={s.key}>
                  <p className="text-[12px] text-fg-3">{s.label}</p>
                  <p className="font-mono text-[14px] tabular-nums text-fg">{formatReading(machine.sensorData[s.key], s.decimals)} {s.unit}</p>
                  <p className="font-mono text-[12px] text-fg-3">Normal {machine.normalRanges[s.key].min}–{machine.normalRanges[s.key].max}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4 rounded-xl border border-line bg-deep p-5">
            <div>
              <p className="text-[12px] text-fg-3">Health</p>
              <p className="font-mono text-[16px] tabular-nums text-fg">{machine.sensorData.health.toFixed(0)}</p>
            </div>
            <div>
              <p className="text-[12px] text-fg-3">Failure risk</p>
              <p className="font-mono text-[16px] tabular-nums text-fg">{machine.sensorData.failureProbability.toFixed(0)}%</p>
            </div>
            <div>
              <p className="text-[12px] text-fg-3">Time to failure</p>
              <p className="font-mono text-[16px] text-fg">{machine.sensorData.timeToFailure}</p>
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <button onClick={onClose} className="h-9 rounded-lg border border-line bg-raised px-4 text-[13px] text-fg transition-colors duration-150 hover:border-line-strong">
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
