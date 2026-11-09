'use client'

import { useEffect, useRef } from 'react'
import { AlertCircle, CheckCircle, X } from 'lucide-react'
import type { Toast as ToastType } from '@/lib/sentinel-types'

interface ToastContainerProps {
  toasts: ToastType[]
  onRemove: (id: string) => void
}

export function Toast({ toast, onRemove }: { toast: ToastType; onRemove: () => void }) {
  // The parent re-renders with every live reading and passes a new callback each time;
  // keying the timer on it would restart the countdown forever
  const onRemoveRef = useRef(onRemove)
  onRemoveRef.current = onRemove
  useEffect(() => {
    const timer = setTimeout(() => onRemoveRef.current(), 4000)
    return () => clearTimeout(timer)
  }, [])

  const isSuccess = toast.type === 'success'

  return (
    <div
      role="status"
      className="animate-enter flex w-[340px] items-center gap-3 rounded-xl border border-line-strong bg-raised px-4 py-3 shadow-[0_8px_24px_rgba(0,0,0,0.4)]"
    >
      {isSuccess ? (
        <CheckCircle className="h-4 w-4 shrink-0 text-ok" strokeWidth={1.5} />
      ) : (
        <AlertCircle className="h-4 w-4 shrink-0 text-crit" strokeWidth={1.5} />
      )}
      <span className="flex-1 text-[13px] leading-5 text-fg">{toast.message}</span>
      <button
        onClick={onRemove}
        aria-label="Dismiss"
        className="rounded-md p-1 text-fg-3 transition-colors duration-150 hover:text-fg"
      >
        <X className="h-4 w-4" strokeWidth={1.5} />
      </button>
    </div>
  )
}

export function ToastContainer({ toasts, onRemove }: ToastContainerProps) {
  return (
    <div className="fixed bottom-4 right-4 z-40 flex flex-col gap-2" aria-live="polite">
      {toasts.map(toast => (
        <Toast
          key={toast.id}
          toast={toast}
          onRemove={() => onRemove(toast.id)}
        />
      ))}
    </div>
  )
}
