'use client'

import { useState } from 'react'
import { Users, Plus, X, Mail, Phone } from 'lucide-react'
import type { Mechanic, Machine } from '@/lib/sentinel-types'

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
  const [machine, setMachine] = useState(machines[0]?.id || '')
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
    setMachine(machines[0]?.id || '')
    setShift('morning')
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#111827] border border-[#1e293b] rounded-xl w-full max-w-sm p-6" style={{ boxShadow: '0 25px 60px rgba(0,0,0,0.5), 0 0 40px rgba(0,200,150,0.05)' }}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[13px] font-bold text-[#e8ecf4] tracking-wider">ADD MECHANIC</h2>
          <button onClick={onClose} className="text-[#64748b] hover:text-[#e8ecf4] transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-3 mb-6">
          <div>
            <label className="text-[10px] text-[#64748b] font-mono block mb-1">NAME</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="John Smith"
              className="w-full bg-[#0a0e17] border border-[#1e293b] text-[#e8ecf4] text-[11px] rounded-lg px-3 py-2 focus:outline-none focus:border-[#00c896]/40 placeholder-[#475569] transition-colors"
            />
          </div>

          <div>
            <label className="text-[10px] text-[#64748b] font-mono block mb-1">EMAIL</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="john@facility.com"
              className="w-full bg-[#0a0e17] border border-[#1e293b] text-[#e8ecf4] text-[11px] rounded-lg px-3 py-2 focus:outline-none focus:border-[#00c896]/40 placeholder-[#475569] transition-colors"
            />
          </div>

          <div>
            <label className="text-[10px] text-[#64748b] font-mono block mb-1">PHONE</label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+1 (555) 123-4567"
              className="w-full bg-[#0a0e17] border border-[#1e293b] text-[#e8ecf4] text-[11px] rounded-lg px-3 py-2 focus:outline-none focus:border-[#00c896]/40 placeholder-[#475569] transition-colors"
            />
          </div>

          <div>
            <label className="text-[10px] text-[#64748b] font-mono block mb-1">ASSIGN TO MACHINE</label>
            <select
              value={machine}
              onChange={(e) => setMachine(e.target.value)}
              className="w-full bg-[#0a0e17] border border-[#1e293b] text-[#e8ecf4] text-[11px] rounded-lg px-3 py-2 focus:outline-none focus:border-[#00c896]/40"
            >
              {machines.map(m => (
                <option key={m.id} value={m.id}>{m.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-[10px] text-[#64748b] font-mono block mb-1">SHIFT</label>
            <select
              value={shift}
              onChange={(e) => setShift(e.target.value as 'morning' | 'evening' | 'night')}
              className="w-full bg-[#0a0e17] border border-[#1e293b] text-[#e8ecf4] text-[11px] rounded-lg px-3 py-2 focus:outline-none focus:border-[#00c896]/40"
            >
              <option value="morning">Morning (6AM - 2PM)</option>
              <option value="evening">Evening (2PM - 10PM)</option>
              <option value="night">Night (10PM - 6AM)</option>
            </select>
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={onClose}
            className="flex-1 bg-[#151c2c] border border-[#1e293b] text-[#64748b] text-[11px] py-2 rounded-lg hover:border-[#2d3a52] hover:text-[#94a3b8] transition-colors"
          >
            CANCEL
          </button>
          <button
            onClick={handleSubmit}
            disabled={!name.trim() || !email.trim() || !phone.trim()}
            className="flex-1 bg-[#00c896]/10 border border-[#00c896]/30 text-[#00c896] text-[11px] py-2 rounded-lg hover:bg-[#00c896]/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            ADD
          </button>
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

function MechanicCard({ mechanic, onDelete, onPreviewEmail }: MechanicCardProps) {
  const statusColor = {
    'available': 'bg-[#00c896]',
    'on-duty': 'bg-[#e5a000]',
    'off-shift': 'bg-[#64748b]',
  }[mechanic.status]

  return (
    <div className="bg-[#0f1623] border border-[#1e293b] rounded-lg p-3 animate-slideInUp" style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.02)' }}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <p className="text-[11px] font-bold text-[#e8ecf4] truncate">{mechanic.name}</p>
          <p className="text-[9px] text-[#64748b]">{mechanic.assignedMachine}</p>
        </div>
        <button
          onClick={() => onDelete(mechanic.id)}
          className="text-[#475569] hover:text-[#ef4444] ml-2 transition-colors"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="space-y-1.5 mb-2">
        <div className="flex items-center gap-2 text-[10px]">
          <Mail className="w-3 h-3 text-[#38bdf8]" />
          <span className="text-[#94a3b8] truncate">{mechanic.email}</span>
        </div>
        <div className="flex items-center gap-2 text-[10px]">
          <Phone className="w-3 h-3 text-[#38bdf8]" />
          <span className="text-[#94a3b8]">{mechanic.phone}</span>
        </div>
      </div>

      <div className="flex items-center justify-between pt-2 border-t border-[#1e293b]">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${statusColor}`} />
          <span className="text-[9px] text-[#64748b] uppercase">{mechanic.status.replace('-', ' ')}</span>
        </div>
        <span className="text-[8px] text-[#475569] uppercase tracking-wider">{mechanic.shift}</span>
      </div>
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
      <div className="bg-[#111827] border border-[#1e293b] rounded-lg" style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.02)' }}>
        <div className="flex items-center gap-2 px-3 py-2.5 border-b border-[#1e293b]">
          <Users className="w-3.5 h-3.5 text-[#00c896]" />
          <p className="text-[11px] font-sans font-bold text-[#e8ecf4] tracking-wider flex-1">MECHANIC ASSIGNMENTS</p>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-1 bg-[#00c896]/8 border border-[#00c896]/25 text-[#00c896] px-2 py-1 rounded-md text-[9px] hover:bg-[#00c896]/15 transition-colors"
          >
            <Plus className="w-3 h-3" />
            ADD
          </button>
        </div>
        <div className="p-3 grid grid-cols-2 gap-2 max-h-[320px] overflow-y-auto">
          {mechanics.length === 0 ? (
            <p className="col-span-2 text-[11px] text-[#64748b] text-center py-4">No mechanics assigned</p>
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
      </div>

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
