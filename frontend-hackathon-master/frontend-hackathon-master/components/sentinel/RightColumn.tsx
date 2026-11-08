'use client'

import { useRef, useEffect, useState } from 'react'
import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport } from 'ai'
import { Send, Bot, Wrench, AlertTriangle } from 'lucide-react'
import type { Alert, MaintenanceItem, Machine, Mechanic, NotificationLog } from '@/lib/sentinel-types'
import MechanicPanel from './MechanicPanel'
import NotificationLogComponent from './NotificationLog'
import { EmailPreview } from './EmailPreview'

function getMessageText(parts: Array<{ type: string; text?: string }>): string {
  return parts.filter((p): p is { type: 'text'; text: string } => p.type === 'text').map(p => p.text).join('')
}

// ─── AI Copilot Chat ───────────────────────────────────────────────
interface AICopilotChatProps {
  machine: Machine
}

const QUICK_PROMPTS = [
  'Why is this machine failing?',
  'When should I schedule maintenance?',
  'What\'s the risk if I delay repair?',
  'Explain the sensor readings',
]

export function AICopilotChat({ machine }: AICopilotChatProps) {
  const [input, setInput] = useState('')
  const messagesRef = useRef<HTMLDivElement>(null)

  const { messages, sendMessage, status, error } = useChat({
    transport: new DefaultChatTransport({
      api: '/api/sentinel-chat',
      prepareSendMessagesRequest: ({ id, messages }) => ({
        body: {
          id,
          messages,
          machineContext: {
            name: machine.name,
            type: machine.type,
            status: machine.status,
            health: machine.sensorData.health,
            failureProbability: machine.sensorData.failureProbability,
            timeToFailure: machine.sensorData.timeToFailure,
            temperature: machine.sensorData.temperature,
            vibration: machine.sensorData.vibration,
            rpm: machine.sensorData.rpm,
            pressure: machine.sensorData.pressure,
          },
        },
      }),
    }),
  })

  // Scroll only the message list; scrollIntoView would also scroll the page and hide the header on load
  useEffect(() => {
    const list = messagesRef.current
    list?.scrollTo({ top: list.scrollHeight, behavior: 'smooth' })
  }, [messages, error])

  function handleSend(text: string) {
    if (!text.trim()) return
    sendMessage({ text })
    setInput('')
  }

  const isStreaming = status === 'streaming' || status === 'submitted'

  return (
    <div className="bg-[#111827] border border-[#1e293b] rounded-lg flex flex-col" style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.02)' }}>
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-[#1e293b]"
        style={{ background: 'linear-gradient(135deg, rgba(56,189,248,0.06) 0%, rgba(0,200,150,0.03) 100%)' }}>
        <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
          style={{ background: 'linear-gradient(135deg, #38bdf8, #0284c7)', boxShadow: '0 0 12px rgba(56,189,248,0.3)' }}>
          <Bot className="w-3.5 h-3.5 text-[#0a0e17]" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[11px] font-sans font-bold text-[#e8ecf4] tracking-wider leading-none">AI COPILOT</p>
          <p className="text-[9px] text-[#64748b]">Powered by Claude AI</p>
        </div>
        <span className="w-1.5 h-1.5 rounded-full bg-[#00c896] animate-pulse-dot" style={{ boxShadow: '0 0 6px rgba(0,200,150,0.5)' }} />
      </div>

      {/* Messages */}
      <div ref={messagesRef} className="h-[260px] overflow-y-auto p-3 flex flex-col gap-2">
        {messages.length === 0 && (
          <div className="text-center py-6">
            <Bot className="w-8 h-8 text-[#1e293b] mx-auto mb-2" />
            <p className="text-[11px] text-[#64748b]">Ask me about {machine.name}</p>
          </div>
        )}
        {messages.map((m) => {
          const text = getMessageText(m.parts as Array<{ type: string; text?: string }>)
          if (!text) return null
          return (
            <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'} animate-fadeInUp`}>
              <div className={`max-w-[85%] rounded-lg px-3 py-2 text-[11px] leading-relaxed ${
                m.role === 'user'
                  ? 'bg-[#38bdf8]/10 border border-[#38bdf8]/25 text-[#e8ecf4]'
                  : 'bg-[#0f1623] border border-[#1e293b] text-[#94a3b8]'
              }`}>
                {text}
              </div>
            </div>
          )
        })}
        {isStreaming && (
          <div className="flex justify-start">
            <div className="bg-[#0f1623] border border-[#1e293b] rounded-lg px-3 py-2.5 flex items-center gap-1">
              {[0, 150, 300].map(d => (
                <span key={d} className="w-1.5 h-1.5 rounded-full bg-[#38bdf8] animate-bounce-dot" style={{ animationDelay: `${d}ms` }} />
              ))}
            </div>
          </div>
        )}
        {error && !isStreaming && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-lg px-3 py-2 text-[11px] leading-relaxed bg-[#ef4444]/10 border border-[#ef4444]/25 text-[#ef4444]">
              {error.message || 'The AI copilot could not answer right now.'}
            </div>
          </div>
        )}
      </div>

      {/* Quick prompts */}
      <div className="px-3 pb-2 flex flex-col gap-1">
        <div className="grid grid-cols-2 gap-1">
          {QUICK_PROMPTS.map(p => (
            <button
              key={p}
              onClick={() => handleSend(p)}
              disabled={isStreaming}
              className="text-[9px] bg-[#0f1623] border border-[#1e293b] text-[#64748b] py-1.5 px-2 rounded-md hover:border-[#38bdf8]/25 hover:text-[#94a3b8] transition-colors text-left disabled:opacity-40 truncate"
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Input */}
      <div className="flex gap-2 px-3 pb-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend(input)}
          placeholder="Ask about sensor data..."
          disabled={isStreaming}
          className="flex-1 bg-[#0a0e17] border border-[#1e293b] text-[#e8ecf4] text-[11px] rounded-lg px-3 py-2 focus:outline-none focus:border-[#38bdf8]/40 placeholder-[#475569] disabled:opacity-50 transition-colors"
        />
        <button
          onClick={() => handleSend(input)}
          disabled={isStreaming || !input.trim()}
          className="bg-[#38bdf8]/10 border border-[#38bdf8]/30 text-[#38bdf8] px-3 rounded-lg hover:bg-[#38bdf8]/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Send className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  )
}

// ─── Live Alerts ───────────────────────────────────────────────────
interface LiveAlertsProps {
  alerts: Alert[]
}

export function LiveAlerts({ alerts }: LiveAlertsProps) {
  return (
    <div className="bg-[#111827] border border-[#ef4444]/15 rounded-lg" style={{ boxShadow: '0 0 20px rgba(239,68,68,0.03), inset 0 1px 0 rgba(255,255,255,0.02)' }}>
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-[#1e293b]">
        <AlertTriangle className="w-3.5 h-3.5 text-[#ef4444]" />
        <p className="text-[11px] font-sans font-bold text-[#e8ecf4] tracking-wider flex-1">LIVE ALERTS</p>
        <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded-full ${alerts.filter(a => a.level === 'critical').length > 0 ? 'bg-[#ef4444]/15 text-[#ef4444]' : 'bg-[#1e293b] text-[#64748b]'}`}>
          {alerts.filter(a => a.level === 'critical').length} CRITICAL
        </span>
      </div>
      <div className="max-h-[200px] overflow-y-auto p-2 flex flex-col gap-1.5">
        {alerts.length === 0 && (
          <p className="text-[11px] text-[#64748b] text-center py-4">No active alerts</p>
        )}
        {alerts.map((alert) => (
          <div
            key={alert.id}
            className={`flex items-start gap-2 p-2 rounded-md border animate-slideInAlert ${
              alert.level === 'critical'
                ? 'bg-[#ef4444]/5 border-[#ef4444]/15'
                : alert.level === 'warning'
                ? 'bg-[#e5a000]/5 border-[#e5a000]/15'
                : 'bg-[#38bdf8]/5 border-[#38bdf8]/10'
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full mt-1 shrink-0 animate-pulse-dot ${
              alert.level === 'critical' ? 'bg-[#ef4444]' : alert.level === 'warning' ? 'bg-[#e5a000]' : 'bg-[#38bdf8]'
            }`} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded font-sans tracking-wider ${
                  alert.level === 'critical' ? 'bg-[#ef4444]/15 text-[#ef4444]' : alert.level === 'warning' ? 'bg-[#e5a000]/15 text-[#e5a000]' : 'bg-[#38bdf8]/15 text-[#38bdf8]'
                }`}>
                  {alert.level.toUpperCase()}
                </span>
                <span className="text-[9px] text-[#64748b] truncate">{alert.machine}</span>
                <span className="text-[9px] text-[#475569] ml-auto shrink-0">{alert.timestamp}</span>
              </div>
              <p className="text-[10px] text-[#94a3b8] leading-relaxed">{alert.message}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Maintenance Schedule ──────────────────────────────────────────
interface MaintenanceProps {
  items: MaintenanceItem[]
}

export function MaintenanceSchedule({ items }: MaintenanceProps) {
  return (
    <div className="bg-[#111827] border border-[#1e293b] rounded-lg" style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.02)' }}>
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-[#1e293b]">
        <Wrench className="w-3.5 h-3.5 text-[#00c896]" />
        <p className="text-[11px] font-sans font-bold text-[#e8ecf4] tracking-wider">AI-SCHEDULED MAINTENANCE</p>
      </div>
      <div className="p-2 flex flex-col gap-2">
        {items.map((item) => (
          <div
            key={item.id}
            className={`p-2.5 rounded-md border-l-2 bg-[#0f1623] ${
              item.priority === 'critical'
                ? 'border-l-[#ef4444]'
                : item.priority === 'warning'
                ? 'border-l-[#e5a000]'
                : 'border-l-[#00c896]'
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="text-[11px] font-bold text-[#e8ecf4] font-sans truncate">{item.machine}</p>
                <p className="text-[10px] text-[#94a3b8] mt-0.5">{item.action}</p>
                <p className="text-[9px] text-[#64748b] mt-1">{item.scheduledTime}</p>
              </div>
              <div className="text-right shrink-0">
                <p className="text-[9px] text-[#64748b]">Est. Savings</p>
                <p className={`text-[12px] font-bold font-mono ${
                  item.priority === 'critical' ? 'text-[#ef4444]' : item.priority === 'warning' ? 'text-[#e5a000]' : 'text-[#00c896]'
                }`}>
                  {item.estimatedSavings}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Right Column wrapper ──────────────────────────────────────────
interface RightColumnProps {
  machine: Machine
  machines: Machine[]
  alerts: Alert[]
  maintenance: MaintenanceItem[]
  mechanics: Mechanic[]
  notificationLogs: NotificationLog[]
  onAddMechanic: (mechanic: Omit<Mechanic, 'id'>) => void
  onDeleteMechanic: (id: string) => void
}

export default function RightColumn({
  machine,
  machines,
  alerts,
  maintenance,
  mechanics,
  notificationLogs,
  onAddMechanic,
  onDeleteMechanic,
}: RightColumnProps) {
  const [previewMechanic, setPreviewMechanic] = useState<Mechanic | null>(null)

  return (
    <>
      <aside className="w-[280px] lg:w-[300px] xl:w-[320px] shrink-0 flex flex-col gap-3 overflow-y-auto p-3 bg-[#0c1220]">
        <AICopilotChat machine={machine} />
        <LiveAlerts alerts={alerts} />
        <MaintenanceSchedule items={maintenance} />
        <MechanicPanel
          mechanics={mechanics}
          machines={machines}
          onAddMechanic={onAddMechanic}
          onDeleteMechanic={onDeleteMechanic}
          onPreviewEmail={setPreviewMechanic}
        />
        <NotificationLogComponent logs={notificationLogs} />
      </aside>
      <EmailPreview
        isOpen={previewMechanic !== null}
        machine={machine}
        mechanic={previewMechanic}
        onClose={() => setPreviewMechanic(null)}
      />
    </>
  )
}
