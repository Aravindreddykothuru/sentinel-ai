'use client'

import { useState } from 'react'
import { Plus, X } from 'lucide-react'
import type { Mechanic, Machine } from '@/lib/sentinel-types'

const fieldClass = 'h-9 w-full rounded-lg border border-line bg-deep px-3 text-[13px] text-fg placeholder:text-fg-3 transition-colors duration-150 focus:border-signal/60 focus:outline-none'
const labelClass = 'mb-2 block text-[12px] text-fg-2'

const STATUS_DOT: Record<Mechanic['status'], string> = { 'available': 'bg-ok', 'on-duty': 'bg-warn', 'off-shift': 'bg-fg-3' }
const STATUS_LABEL: Record<Mechanic['status'], string> = { 'available': 'Available', 'on-duty': 'On a job', 'off-shift': 'Off shift' }
const SHIFT_LABEL: Record<Mechanic['shift'], string> = { morning: 'Morning shift', evening: 'Evening shift', night: 'Night shift' }

// ─── Add Mechanic Modal ────────────────────────────────────────────
interface AddMechanicModalProps {
  isOpen: boolean
  machines: Machine[]
  onClose: () => void
  onAdd: (mechanic: Omit<Mechanic, 'id'>) => void
}

function AddMechanicModal({ isOpen, machines, onClose, onAdd }: AddMechanicModalProps) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  // Alerts find a machine's mechanic by machine name, so store the name
  const [machine, setMachine] = useState(machines[0]?.name || '')
  const [shift, setShift] = useState<'morning' | 'evening' | 'night'>('morning')

  const handleSubmit = () => {
    if (!name.trim() || !email.trim() || !phone.trim() || !machine) return
    onAdd({
      name,
      email,
      phone,
      assignedMachine: machine,
      shift,
      status: 'available',
    })
    setName('')
    setEmail('')
    setPhone('')
    setMachine(machines[0]?.name || '')
    setShift('morning')
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div role="dialog" aria-modal="true" aria-labelledby="add-mechanic-title" className="animate-enter w-full max-w-sm rounded-2xl border border-line bg-panel shadow-[0_24px_64px_rgba(0,0,0,0.5)]">
        <div className="flex items-center justify-between border-b border-line px-6 py-4">
          <h2 id="add-mechanic-title" className="text-[16px] font-medium text-fg">Add mechanic</h2>
          <button onClick={onClose} aria-label="Close" className="rounded-md p-1 text-fg-3 transition-colors duration-150 hover:text-fg">
            <X className="h-4 w-4" strokeWidth={1.5} />
          </button>
        </div>

        <div className="space-y-4 p-6">
          <div>
            <label className={labelClass}>Name</label>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="John Smith" className={fieldClass} />
          </div>
          <div>
            <label className={labelClass}>Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="john@facility.com" className={fieldClass} />
          </div>
          <div>
            <label className={labelClass}>Phone</label>
            <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+1 555 123 4567" className={fieldClass} />
          </div>
          <div>
            <label className={labelClass}>Machine</label>
            <select value={machine} onChange={(e) => setMachine(e.target.value)} className={fieldClass}>
              {machines.map(m => (
                <option key={m.id} value={m.name}>{m.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelClass}>Shift</label>
            <select value={shift} onChange={(e) => setShift(e.target.value as 'morning' | 'evening' | 'night')} className={fieldClass}>
              <option value="morning">Morning, 06:00–14:00</option>
              <option value="evening">Evening, 14:00–22:00</option>
              <option value="night">Night, 22:00–06:00</option>
            </select>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button onClick={onClose} className="h-9 rounded-lg border border-line bg-raised px-4 text-[13px] text-fg transition-colors duration-150 hover:border-line-strong">
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={!name.trim() || !email.trim() || !phone.trim()}
              className="h-9 rounded-lg bg-fg px-4 text-[13px] font-medium text-page transition-colors duration-150 hover:bg-white active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40"
            >
              Add mechanic
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Mechanic Card ────────────────────────────────────────────────
interface MechanicCardProps {
  mechanic: Mechanic
  onDelete: (id: string) => void
  onPreviewEmail: (mechanic: Mechanic) => void
}

function MechanicCard({ mechanic, onDelete }: MechanicCardProps) {
  return (
    <div className="group border-b border-line px-4 py-3 last:border-b-0">
      <div className="flex items-center gap-2">
        <span className={`h-2 w-2 shrink-0 rounded-full ${STATUS_DOT[mechanic.status]}`} title={STATUS_LABEL[mechanic.status]} />
        <p className="truncate text-[13px] font-medium text-fg">{mechanic.name}</p>
        <span className="truncate text-[13px] text-fg-3">· {mechanic.assignedMachine}</span>
        <button
          onClick={() => onDelete(mechanic.id)}
          aria-label={`Remove ${mechanic.name}`}
          className="ml-auto shrink-0 rounded-md p-1 text-fg-3 opacity-60 transition-[color,opacity] duration-150 hover:text-crit hover:opacity-100 group-hover:opacity-100"
        >
          <X className="h-4 w-4" strokeWidth={1.5} />
        </button>
      </div>
      <p className="mt-1 pl-4 text-[12px] text-fg-2">
        {STATUS_LABEL[mechanic.status]} · {SHIFT_LABEL[mechanic.shift]}
      </p>
      <p className="mt-1 truncate pl-4 font-mono text-[12px] text-fg-3">
        {mechanic.email} · {mechanic.phone}
      </p>
    </div>
  )
}

// ─── Mechanic Panel wrapper ────────────────────────────────────────
interface MechanicPanelProps {
  mechanics: Mechanic[]
  machines: Machine[]
  onAddMechanic: (mechanic: Omit<Mechanic, 'id'>) => void
  onDeleteMechanic: (id: string) => void
  onPreviewEmail: (mechanic: Mechanic) => void
}

export default function MechanicPanel({ mechanics, machines, onAddMechanic, onDeleteMechanic, onPreviewEmail }: MechanicPanelProps) {
  const [showModal, setShowModal] = useState(false)

  return (
    <>
      <section className="rounded-xl border border-line bg-panel">
        <div className="flex h-12 items-center justify-between border-b border-line px-4">
          <h3 className="text-[14px] font-medium text-fg">Mechanics</h3>
          <button
            onClick={() => setShowModal(true)}
            className="flex h-8 items-center gap-1 rounded-lg px-2 text-[12px] text-fg-2 transition-colors duration-150 hover:bg-raised hover:text-fg"
          >
            <Plus className="h-4 w-4" strokeWidth={1.5} />
            Add
          </button>
        </div>
        <div className="max-h-[320px] overflow-y-auto">
          {mechanics.length === 0 ? (
            <p className="py-8 text-center text-[13px] text-fg-3">No mechanics assigned</p>
          ) : (
            mechanics.map(m => (
              <MechanicCard
                key={m.id}
                mechanic={m}
                onDelete={onDeleteMechanic}
                onPreviewEmail={onPreviewEmail}
              />
            ))
          )}
        </div>
      </section>

      <AddMechanicModal
        isOpen={showModal}
        machines={machines}
        onClose={() => setShowModal(false)}
        onAdd={(mechanic) => {
          onAddMechanic(mechanic)
          setShowModal(false)
        }}
      />
    </>
  )
}
