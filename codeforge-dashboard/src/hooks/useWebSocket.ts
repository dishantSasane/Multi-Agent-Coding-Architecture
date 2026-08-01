import { useState, useEffect, useCallback, useRef } from 'react';
import type { WebSocketMessage, TaskStatus } from '@/types';
import { WS_RECONNECT_INTERVALS, WS_HEARTBEAT_INTERVAL } from '@/lib/constants';
import { getBackendUrl } from '@/lib/api';

interface UseWebSocketReturn {
  lastMessage: WebSocketMessage | null;
  connectionStatus: 'connecting' | 'open' | 'closed' | 'error';
  sendMessage: (msg: object) => void;
  reconnect: () => void;
}

export function useWebSocket(taskId: string | null): UseWebSocketReturn {
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'open' | 'closed' | 'error'>('closed');
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const cleanup = useCallback(() => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!taskId) {
      cleanup();
      setConnectionStatus('closed');
      return;
    }

    cleanup();
    setConnectionStatus('connecting');

    const baseUrl = getBackendUrl().replace('http://', 'ws://').replace('https://', 'wss://');
    const wsUrl = `${baseUrl}/ws/${taskId}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnectionStatus('open');
        reconnectAttemptsRef.current = 0;
        
        // Start heartbeat
        heartbeatIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, WS_HEARTBEAT_INTERVAL);
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(message);
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      ws.onerror = () => {
        setConnectionStatus('error');
      };

      ws.onclose = () => {
        setConnectionStatus('closed');
        cleanup();
        
        // Attempt reconnection with exponential backoff
        const attempt = reconnectAttemptsRef.current;
        if (attempt < WS_RECONNECT_INTERVALS.length) {
          const delay = WS_RECONNECT_INTERVALS[attempt];
          reconnectAttemptsRef.current += 1;
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        }
      };
    } catch (e) {
      setConnectionStatus('error');
    }
  }, [taskId, cleanup]);

  const sendMessage = useCallback((msg: object) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  const reconnect = useCallback(() => {
    reconnectAttemptsRef.current = 0;
    connect();
  }, [connect]);

  useEffect(() => {
    connect();
    return cleanup;
  }, [connect, cleanup]);

  return {
    lastMessage,
    connectionStatus,
    sendMessage,
    reconnect,
  };
}
