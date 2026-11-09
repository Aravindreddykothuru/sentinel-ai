/**
 * WebSocket hook for real-time machine data streaming
 * Connects to backend WebSocket endpoint and receives live sensor updates
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import { ENDPOINTS } from '@/lib/api-config'

interface SensorData {
  temperature: number
  vibration: number
  rpm: number
  pressure: number
  health?: number
  failureProbability?: number
  timeToFailure?: string
}

interface MachineUpdate {
  machine_id: string
  timestamp: string
  data_source: string
  sensors: SensorData
  reading_number: number
  degradation_factor: number
  health_score: number
  failure_probability: number
  tier: {
    level: number
    label: string
  }
}

interface WebSocketMessage {
  type: 'machine_data' | 'alert' | 'subscribed' | 'unsubscribed' | 'active_streams'
  machine_id?: string
  data?: MachineUpdate
  streams?: string[]
}

interface UseWebSocketOptions {
  url?: string
  onMessage?: (data: WebSocketMessage) => void
  onConnect?: () => void
  onDisconnect?: () => void
  autoReconnect?: boolean
  reconnectInterval?: number
}

export function useWebSocket({
  url = `${ENDPOINTS.websocket}/frontend`,
  onMessage,
  onConnect,
  onDisconnect,
  autoReconnect = true,
  reconnectInterval = 3000,
}: UseWebSocketOptions = {}) {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const [subscribedMachines, setSubscribedMachines] = useState<string[]>([])
  
  // Use refs for WebSocket and callbacks to prevent reconnection loops
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const manualDisconnectRef = useRef(false)
  const mountedRef = useRef(false)
  
  // Store callbacks in refs to avoid dependency changes
  const onMessageRef = useRef(onMessage)
  const onConnectRef = useRef(onConnect)
  const onDisconnectRef = useRef(onDisconnect)
  
  // Update refs when callbacks change
  useEffect(() => {
    onMessageRef.current = onMessage
    onConnectRef.current = onConnect
    onDisconnectRef.current = onDisconnect
  })

  const connect = useCallback(() => {
    // Prevent duplicate connections
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      return
    }
    
    manualDisconnectRef.current = false

    const ws = new WebSocket(url)
    wsRef.current = ws

    // Events from a socket we've already replaced must not touch the current one
    ws.onopen = () => {
      if (wsRef.current !== ws) return
      console.log('[WebSocket] Connected')
      setIsConnected(true)
      onConnectRef.current?.()
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WebSocketMessage
        setLastMessage(data)
        onMessageRef.current?.(data)
      } catch (err) {
        console.error('[WebSocket] Parse error:', err)
      }
    }

    ws.onclose = () => {
      if (wsRef.current !== ws) return
      console.log('[WebSocket] Disconnected')
      setIsConnected(false)
      onDisconnectRef.current?.()
      wsRef.current = null
      
      // Auto reconnect only if not manually disconnected
      if (autoReconnect && !manualDisconnectRef.current && mountedRef.current) {
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('[WebSocket] Reconnecting...')
          connect()
        }, reconnectInterval)
      }
    }

    ws.onerror = (error) => {
      console.error('[WebSocket] Error:', error)
    }
  }, [url, autoReconnect, reconnectInterval])

  const disconnect = useCallback(() => {
    manualDisconnectRef.current = true
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    const ws = wsRef.current
    wsRef.current = null
    ws?.close()
    setIsConnected(false)
  }, [])

  const subscribe = useCallback((machineId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'subscribe',
        machine_id: machineId
      }))
      setSubscribedMachines(prev => 
        prev.includes(machineId) ? prev : [...prev, machineId]
      )
    }
  }, [])

  const unsubscribe = useCallback((machineId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'unsubscribe',
        machine_id: machineId
      }))
      setSubscribedMachines(prev => prev.filter(id => id !== machineId))
    }
  }, [])

  const getActiveStreams = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'get_active_streams'
      }))
    }
  }, [])

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    mountedRef.current = true
    connect()
    return () => {
      mountedRef.current = false
      disconnect()
    }
  }, [connect, disconnect])

  return {
    isConnected,
    lastMessage,
    subscribedMachines,
    subscribe,
    unsubscribe,
    getActiveStreams,
    connect,
    disconnect,
  }
}

export type { MachineUpdate, WebSocketMessage, SensorData }
