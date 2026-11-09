'use client'

import { X, ExternalLink } from 'lucide-react'
import type { Machine, Mechanic } from '@/lib/sentinel-types'

interface EmailPreviewProps {
  isOpen: boolean
  machine: Machine | null
  mechanic: Mechanic | null
  onClose: () => void
}

export function EmailPreview({ isOpen, machine, mechanic, onClose }: EmailPreviewProps) {
  if (!isOpen || !machine || !mechanic) return null

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#111827] border border-[#1e293b] rounded-xl w-full max-w-2xl max-h-[80vh] overflow-y-auto" style={{ boxShadow: '0 25px 60px rgba(0,0,0,0.5), 0 0 40px rgba(56,189,248,0.05)' }}>
        {/* Close button */}
        <div className="flex items-center justify-between sticky top-0 bg-[#111827] border-b border-[#1e293b] px-6 py-4 z-10">
          <h2 className="text-[13px] font-bold text-[#e8ecf4] tracking-wider">ALERT EMAIL PREVIEW</h2>
          <button onClick={onClose} className="text-[#64748b] hover:text-[#e8ecf4] transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Email content */}
        <div className="p-6">
          {/* Email header */}
          <div className="bg-[#0a0e17] border border-[#1e293b] rounded-lg p-6 mb-4">
            <div className="flex items-center justify-between mb-6">
              <div>
                <p className="text-[20px] font-bold text-[#00c896] tracking-wider glow-green">SENTINEL AI</p>
                <p className="text-[11px] text-[#64748b]">Predictive Maintenance System</p>
              </div>
              <div className="text-right">
                <p className="text-[11px] text-[#94a3b8]">To: {mechanic.email}</p>
                <p className="text-[9px] text-[#64748b]">PLANT-7 NORTH</p>
              </div>
            </div>

            <div className="border-t border-[#1e293b] pt-4">
              <p className="text-[13px] font-bold text-[#ef4444] mb-3">CRITICAL ALERT: {machine.name}</p>
              <p className="text-[12px] text-[#e8ecf4] mb-4">
                Dear {mechanic.name},
              </p>
              <p className="text-[12px] text-[#94a3b8] leading-relaxed mb-4">
                A critical failure alert has been generated for <span className="text-[#e8ecf4] font-bold">{machine.name}</span> at <span className="font-mono text-[#00c896]">PLANT-7 NORTH</span>. Immediate inspection and maintenance action is required.
              </p>
            </div>
          </div>

          {/* Machine details */}
          <div className="bg-[#0a0e17] border border-[#1e293b] rounded-lg p-4 mb-4">
            <p className="text-[11px] font-bold text-[#e8ecf4] tracking-wider mb-3">MACHINE DETAILS</p>
            <div className="grid grid-cols-2 gap-4 text-[11px]">
              <div>
                <p className="text-[#64748b]">Machine Name</p>
                <p className="text-[#e8ecf4] font-mono">{machine.name}</p>
              </div>
              <div>
                <p className="text-[#64748b]">Type</p>
                <p className="text-[#e8ecf4] font-mono">{machine.type}</p>
              </div>
              <div>
                <p className="text-[#64748b]">Location</p>
                <p className="text-[#e8ecf4] font-mono">{machine.location}</p>
              </div>
              <div>
                <p className="text-[#64748b]">Status</p>
                <p className={`font-mono ${machine.status === 'critical' ? 'text-[#ef4444]' : machine.status === 'warning' ? 'text-[#e5a000]' : 'text-[#00c896]'}`}>
                  {machine.status.toUpperCase()}
                </p>
              </div>
            </div>
          </div>

          {/* Sensor readings */}
          <div className="bg-[#0a0e17] border border-[#1e293b] rounded-lg p-4 mb-4">
            <p className="text-[11px] font-bold text-[#e8ecf4] tracking-wider mb-3">CURRENT SENSOR READINGS</p>
            <div className="grid grid-cols-2 gap-4 text-[11px]">
              <div>
                <p className="text-[#64748b]">Temperature</p>
                <p className="text-[#e8ecf4] font-mono">{machine.sensorData.temperature.toFixed(1)}{'\u00B0'}C</p>
                <p className="text-[9px] text-[#475569]">Range: {machine.normalRanges.temperature.min}{'\u2013'}{machine.normalRanges.temperature.max}{'\u00B0'}C</p>
              </div>
              <div>
                <p className="text-[#64748b]">Vibration</p>
                <p className="text-[#e8ecf4] font-mono">{machine.sensorData.vibration.toFixed(2)} mm/s</p>
                <p className="text-[9px] text-[#475569]">Range: {machine.normalRanges.vibration.min}{'\u2013'}{machine.normalRanges.vibration.max} mm/s</p>
              </div>
              <div>
                <p className="text-[#64748b]">RPM</p>
                <p className="text-[#e8ecf4] font-mono">{machine.sensorData.rpm.toFixed(0)}</p>
                <p className="text-[9px] text-[#475569]">Range: {machine.normalRanges.rpm.min}{'\u2013'}{machine.normalRanges.rpm.max}</p>
              </div>
              <div>
                <p className="text-[#64748b]">Pressure</p>
                <p className="text-[#e8ecf4] font-mono">{machine.sensorData.pressure.toFixed(1)} bar</p>
                <p className="text-[9px] text-[#475569]">Range: {machine.normalRanges.pressure.min}{'\u2013'}{machine.normalRanges.pressure.max} bar</p>
              </div>
            </div>
          </div>

          {/* Health metrics */}
          <div className="bg-[#0a0e17] border border-[#1e293b] rounded-lg p-4 mb-4">
            <p className="text-[11px] font-bold text-[#e8ecf4] tracking-wider mb-3">HEALTH METRICS</p>
            <div className="grid grid-cols-2 gap-4 text-[11px]">
              <div>
                <p className="text-[#64748b]">Health Score</p>
                <p className={`text-[13px] font-bold font-mono ${machine.sensorData.health > 60 ? 'text-[#00c896]' : machine.sensorData.health > 40 ? 'text-[#e5a000]' : 'text-[#ef4444]'}`}>
                  {machine.sensorData.health.toFixed(1)}%
                </p>
              </div>
              <div>
                <p className="text-[#64748b]">Failure Probability</p>
                <p className={`text-[13px] font-bold font-mono ${machine.sensorData.failureProbability < 50 ? 'text-[#00c896]' : machine.sensorData.failureProbability < 70 ? 'text-[#e5a000]' : 'text-[#ef4444]'}`}>
                  {machine.sensorData.failureProbability.toFixed(0)}%
                </p>
              </div>
              <div>
                <p className="text-[#64748b]">Time to Failure</p>
                <p className="text-[13px] font-bold font-mono text-[#ef4444]">{machine.sensorData.timeToFailure}</p>
              </div>
            </div>
          </div>

          {/* AI insight */}
          <div className="bg-[#0a0e17] border border-[#38bdf8]/20 rounded-lg p-4 mb-4" style={{ background: 'linear-gradient(135deg, rgba(56,189,248,0.04) 0%, rgba(0,200,150,0.02) 100%)' }}>
            <p className="text-[11px] font-bold text-[#38bdf8] tracking-wider mb-2">AI INSIGHT</p>
            <p className="text-[11px] text-[#94a3b8] leading-relaxed">
              Sensor data indicates imminent component failure. Failure probability has exceeded critical threshold. Recommend immediate shutdown and inspection of bearing assemblies. Estimated maintenance time: 4{'–'}6 hours. Estimated cost avoidance: $180,000+.
            </p>
          </div>

          {/* Action button */}
          <div className="flex gap-3">
            <button className="flex-1 bg-[#00c896]/10 border border-[#00c896]/30 text-[#00c896] text-[11px] py-2.5 rounded-lg hover:bg-[#00c896]/20 transition-colors flex items-center justify-center gap-2">
              <ExternalLink className="w-3.5 h-3.5" />
              VIEW DASHBOARD
            </button>
            <button
              onClick={onClose}
              className="flex-1 bg-[#151c2c] border border-[#1e293b] text-[#94a3b8] text-[11px] py-2.5 rounded-lg hover:border-[#00c896]/25 transition-colors"
            >
              CLOSE
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
