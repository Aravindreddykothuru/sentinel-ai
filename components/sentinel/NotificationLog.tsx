'use client'

import type { NotificationLog as NotificationLogType } from '@/lib/sentinel-types'

interface NotificationLogProps {
  logs: NotificationLogType[]
}

const STATUS_DOT: Record<NotificationLogType['status'], string> = {
  sent: 'bg-signal',
  acknowledged: 'bg-ok',
  resolved: 'bg-ok',
  escalated: 'bg-crit',
}
const STATUS_LABEL: Record<NotificationLogType['status'], string> = {
  sent: 'Sent',
  acknowledged: 'Acknowledged',
  resolved: 'Resolved',
  escalated: 'Escalated',
}
const CHANNEL_LABEL: Record<NotificationLogType['channel'], string> = { email: 'Email', sms: 'SMS', push: 'Push' }

export default function NotificationLog({ logs }: NotificationLogProps) {
  return (
    <section className="rounded-xl border border-line bg-panel">
      <div className="flex h-12 items-center justify-between border-b border-line px-4">
        <h3 className="text-[14px] font-medium text-fg">Notifications</h3>
        <span className="font-mono text-[12px] text-fg-3">{logs.length}</span>
      </div>
      <div className="max-h-[280px] overflow-y-auto">
        {logs.length === 0 ? (
          <p className="py-8 text-center text-[13px] text-fg-3">No notifications sent</p>
        ) : (
          logs.slice(0, 10).map(log => (
            <div key={log.id} className="border-b border-line px-4 py-3 last:border-b-0">
              <div className="flex items-center gap-2">
                <span className={`h-2 w-2 shrink-0 rounded-full ${STATUS_DOT[log.status]}`} />
                <p className="truncate text-[13px] text-fg">
                  {CHANNEL_LABEL[log.channel]} to <span className="font-medium">{log.mechanicName}</span>
                </p>
                <span className="ml-auto shrink-0 font-mono text-[12px] text-fg-3">{log.timeSent}</span>
              </div>
              <p className="mt-1 pl-4 text-[12px] text-fg-2">
                {log.machineName} · {STATUS_LABEL[log.status]}
                {log.escalationTimer != null && log.status === 'sent' && (
                  <span className="text-fg-3"> · escalates in {Math.round(log.escalationTimer / 60000)} min without a reply</span>
                )}
              </p>
            </div>
          ))
        )}
      </div>
    </section>
  )
}
