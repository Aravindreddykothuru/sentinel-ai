'use client'

import { useRef, useEffect, useState } from 'react'
import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport } from 'ai'
import { ArrowUp } from 'lucide-react'
import type { Alert, MaintenanceItem, Machine, Mechanic, NotificationLog } from '@/lib/sentinel-types'
import MechanicPanel from './MechanicPanel'
import NotificationLogComponent from './NotificationLog'
import { EmailPreview } from './EmailPreview'

function getMessageText(parts: Array<{ type: string; text?: string }>): string {
  return parts.filter((p): p is { type: 'text'; text: string } => p.type === 'text').map(p => p.text).join('')
}

// Gemini answers in Markdown; show headings, emphasis and lists without the raw symbols
function FormattedAnswer({ text }: { text: string }) {
  return (
    <>
      {text.split('\n').map((line, i) => {
        if (!line.trim()) return <div key={i} className="h-2" />
        const heading = /^\s*#{1,6}\s+/.test(line)
        const bullet = /^\s*([*-]|\d+\.)\s+/.test(line)
        const marker = bullet ? line.match(/^\s*([*-]|\d+\.)\s+/)![1] : ''
        const clean = line.replace(/^\s*#{1,6}\s+/, '').replace(/^\s*([*-]|\d+\.)\s+/, '')
        // Odd parts were wrapped in **…**
        const content = clean.split(/\*\*(.+?)\*\*/g).map((part, j) =>
          j % 2 ? <span key={j} className="font-medium text-fg">{part}</span> : part.replace(/\*([^*\s][^*]*?)\*/g, '$1'),
        )
        return (
          <p key={i} className={heading ? 'font-medium text-fg' : bullet ? 'flex gap-2' : ''}>
            {bullet && <span className="shrink-0 text-fg-3">{/\d/.test(marker) ? marker : '•'}</span>}
            {bullet ? <span>{content}</span> : content}
          </p>
        )
      })}
    </>
  )
}

const LEVEL_DOT: Record<Alert['level'], string> = { critical: 'bg-crit', warning: 'bg-warn', info: 'bg-fg-3' }
const PRIORITY_DOT: Record<MaintenanceItem['priority'], string> = { critical: 'bg-crit', warning: 'bg-warn', ok: 'bg-ok' }

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
    <section className="flex flex-col rounded-xl border border-line bg-panel">
      <div className="flex h-12 items-center justify-between border-b border-line px-4">
        <h3 className="text-[14px] font-medium text-fg">Copilot</h3>
        <span className="font-mono text-[12px] text-fg-3">Gemini</span>
      </div>

      <div ref={messagesRef} className="flex h-[264px] flex-col gap-3 overflow-y-auto p-4">
        {messages.length === 0 && (
          <p className="m-auto max-w-[24ch] text-center text-[13px] leading-5 text-fg-3">
            Ask about {machine.name}. Answers use its live readings.
          </p>
        )}
        {messages.map((m) => {
          const text = getMessageText(m.parts as Array<{ type: string; text?: string }>)
          if (!text) return null
          return m.role === 'user' ? (
            <div key={m.id} className="ml-auto max-w-[85%] rounded-xl rounded-br-sm bg-raised px-3 py-2 text-[13px] leading-5 text-fg">
              {text}
            </div>
          ) : (
            <div key={m.id} data-role="assistant" className="max-w-[95%] text-[13px] leading-5 text-fg-2">
              <FormattedAnswer text={text} />
            </div>
          )
        })}
        {isStreaming && (
          <div className="flex gap-1 py-2" aria-label="Copilot is answering">
            {[0, 160, 320].map(d => (
              <span key={d} className="animate-typing h-1.5 w-1.5 rounded-full bg-fg-3" style={{ animationDelay: `${d}ms` }} />
            ))}
          </div>
        )}
        {error && !isStreaming && (
          <p className="text-[13px] leading-5 text-crit">
            {error.message || 'The copilot could not answer right now'}
          </p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2 px-4 pb-3">
        {QUICK_PROMPTS.map(p => (
          <button
            key={p}
            onClick={() => handleSend(p)}
            disabled={isStreaming}
            title={p}
            className="h-8 truncate rounded-lg border border-line px-2 text-left text-[12px] text-fg-2 transition-colors duration-150 hover:border-line-strong hover:text-fg disabled:opacity-40"
          >
            {p}
          </button>
        ))}
      </div>

      <div className="flex gap-2 border-t border-line p-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend(input)}
          placeholder={`Ask about ${machine.name}`}
          aria-label="Message the copilot"
          disabled={isStreaming}
          className="h-9 min-w-0 flex-1 rounded-lg border border-line bg-deep px-3 text-[13px] text-fg placeholder:text-fg-3 transition-colors duration-150 focus:border-signal/60 focus:outline-none disabled:opacity-50"
        />
        <button
          onClick={() => handleSend(input)}
          disabled={isStreaming || !input.trim()}
          aria-label="Send"
          className="flex h-9 w-9 items-center justify-center rounded-lg bg-fg text-page transition-colors duration-150 hover:bg-white active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-30"
        >
          <ArrowUp className="h-4 w-4" strokeWidth={1.75} />
        </button>
      </div>
    </section>
  )
}

// ─── Live Alerts ───────────────────────────────────────────────────
interface LiveAlertsProps {
  alerts: Alert[]
}

export function LiveAlerts({ alerts }: LiveAlertsProps) {
  const critical = alerts.filter(a => a.level === 'critical').length

  return (
    <section className="rounded-xl border border-line bg-panel">
      <div className="flex h-12 items-center justify-between border-b border-line px-4">
        <h3 className="text-[14px] font-medium text-fg">Alerts</h3>
        <span className={`font-mono text-[12px] ${critical > 0 ? 'text-crit' : 'text-fg-3'}`}>{critical} critical</span>
      </div>
      <div className="max-h-[248px] overflow-y-auto">
        {alerts.length === 0 && (
          <p className="py-8 text-center text-[13px] text-fg-3">No active alerts</p>
        )}
        {alerts.map((alert) => (
          <div key={alert.id} className="border-b border-line px-4 py-3 last:border-b-0">
            <div className="flex items-center gap-2">
              <span className={`h-2 w-2 shrink-0 rounded-full ${LEVEL_DOT[alert.level]}`} title={alert.level} />
              <span className="truncate text-[13px] font-medium text-fg">{alert.machine}</span>
              <span className="ml-auto shrink-0 font-mono text-[12px] text-fg-3">{alert.timestamp}</span>
            </div>
            <p className="mt-1 pl-4 text-[13px] leading-5 text-fg-2">{alert.message}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

// ─── Maintenance Schedule ──────────────────────────────────────────
interface MaintenanceProps {
  items: MaintenanceItem[]
}

export function MaintenanceSchedule({ items }: MaintenanceProps) {
  return (
    <section className="rounded-xl border border-line bg-panel">
      <div className="flex h-12 items-center border-b border-line px-4">
        <h3 className="text-[14px] font-medium text-fg">Maintenance plan</h3>
      </div>
      <div>
        {items.map((item) => (
          <div key={item.id} className="border-b border-line px-4 py-3 last:border-b-0">
            <div className="flex items-center gap-2">
              <span className={`h-2 w-2 shrink-0 rounded-full ${PRIORITY_DOT[item.priority]}`} />
              <span className="truncate text-[13px] font-medium text-fg">{item.machine}</span>
              <span className="ml-auto shrink-0 font-mono text-[12px] text-fg-3">{item.scheduledTime}</span>
            </div>
            <p className="mt-1 pl-4 text-[13px] leading-5 text-fg-2">{item.action}</p>
          </div>
        ))}
      </div>
    </section>
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
      <aside className="flex w-full shrink-0 flex-col gap-4 border-line bg-deep p-4 lg:w-[340px] lg:overflow-y-auto lg:border-l">
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
