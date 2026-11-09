'use client'

import { useEffect } from 'react'
import { AlertCircle, CheckCircle, X } from 'lucide-react'
import type { Toast as ToastType } from '@/lib/sentinel-types'

interface ToastContainerProps {
  toasts: ToastType[]
  onRemove: (id: string) => void
}

export function Toast({ toast, onRemove }: { toast: ToastType; onRemove: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onRemove, 4000)
    return () => clearTimeout(timer)
  }, [onRemove])

  const isSuccess = toast.type === 'success'

  return (
    <div
      className={`flex items-center gap-3 px-4 py-3 rounded-lg border animate-slideInRight ${
        isSuccess
          ? 'bg-[#00c896]/10 border-[#00c896]/30 text-[#00c896]'
          : 'bg-[#ef4444]/10 border-[#ef4444]/30 text-[#ef4444]'
      }`}
      style={{ backdropFilter: 'blur(12px)', boxShadow: '0 8px 24px rgba(0,0,0,0.4)' }}
    >
      {isSuccess ? (
        <CheckCircle className="w-4 h-4 shrink-0" />
      ) : (
        <AlertCircle className="w-4 h-4 shrink-0" />
      )}
      <span className="text-[12px] font-mono flex-1">{toast.message}</span>
      <button
        onClick={onRemove}
        className="text-current opacity-60 hover:opacity-100 transition-opacity"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  )
}

export function ToastContainer({ toasts, onRemove }: ToastContainerProps) {
  return (
    <div className="fixed bottom-4 right-4 z-40 flex flex-col gap-2 pointer-events-auto">
      {toasts.map(toast => (
        <div key={toast.id} className="pointer-events-auto">
          <Toast
            toast={toast}
            onRemove={() => onRemove(toast.id)}
          />
        </div>
      ))}
    </div>
  )
}
