'use client'

import { Mail } from 'lucide-react'
import type { NotificationLog as NotificationLogType } from '@/lib/sentinel-types'

interface NotificationLogProps {
  logs: NotificationLogType[]
}

export default function NotificationLog({ logs }: NotificationLogProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'sent':
        return 'text-[#0099ff] bg-[#0099ff]/10'
      case 'acknowledged':
        return 'text-[#00ffb4] bg-[#00ffb4]/10'
      case 'resolved':
        return 'text-[#00ffb4] bg-[#00ffb4]/10'
      case 'escalated':
        return 'text-[#ff3355] bg-[#ff3355]/10'
      default:
        return 'text-[#64748b] bg-[#64748b]/10'
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'sent':
        return '📧'
      case 'acknowledged':
        return '✅'
      case 'resolved':
        return '✅'
      case 'escalated':
        return '🔴'
      default:
        return '⏳'
    }
  }

  return (
    <div className="bg-[#0a1422] border border-[#1a2a45] rounded-md">
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-[#1a2a45]">
        <Mail className="w-3.5 h-3.5 text-[#0099ff]" />
        <p className="text-[11px] font-sans font-bold text-[#e2e8f0] tracking-wider">NOTIFICATION LOG</p>
      </div>
      <div className="max-h-[280px] overflow-y-auto p-2 flex flex-col gap-1.5">
        {logs.length === 0 ? (
          <p className="text-[11px] text-[#64748b] text-center py-4">No notifications sent</p>
        ) : (
          logs.slice(0, 10).map(log => (
            <div
              key={log.id}
              className="bg-[#060b18] border border-[#1a2a45] rounded p-2 text-[10px] animate-slideInUp"
            >
              <div className="flex items-start gap-2 mb-1">
                <span className="text-[12px]">{getStatusBadge(log.status)}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-[#64748b]">{log.timeSent}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${getStatusColor(log.status)}`}>
                      {log.status.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-[#e2e8f0] truncate">
                    <span className="font-bold">{log.mechanicName}</span> — {log.machineName}
                  </p>
                </div>
              </div>
              {log.escalationTimer && (
                <div className="ml-6 text-[9px] text-[#ff3355]">
                  Escalates in {Math.ceil(log.escalationTimer / 1000)}s
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}
