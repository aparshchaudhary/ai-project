import { useEffect, useRef, useState, useCallback } from 'react';
import { AssistantState } from '../types';

interface UseWebSocketOptions {
  onStateChange?: (state: AssistantState) => void;
  onReminderAlert?: (data: { id: number; title: string; due_time: string }) => void;
  onCommandResult?: (data: any) => void;
}

export function useWebSocket({ onStateChange, onReminderAlert, onCommandResult }: UseWebSocketOptions = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<any>(null);

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.port === '5173' ? '127.0.0.1:8000' : window.location.host;
    const wsUrl = `${protocol}//${host}/ws/assistant`;

    try {
      const socket = new WebSocket(wsUrl);

      socket.onopen = () => {
        setIsConnected(true);
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'state_change' && data.state && onStateChange) {
            onStateChange(data.state as AssistantState);
          } else if (data.type === 'reminder_alert' && onReminderAlert) {
            onReminderAlert(data);
          } else if (data.type === 'command_result' && onCommandResult) {
            onCommandResult(data.result);
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message', e);
        }
      };

      socket.onclose = () => {
        setIsConnected(false);
        reconnectTimeoutRef.current = setTimeout(connect, 3000);
      };

      socket.onerror = () => {
        socket.close();
      };

      socketRef.current = socket;
    } catch (e) {
      reconnectTimeoutRef.current = setTimeout(connect, 3000);
    }
  }, [onCommandResult, onReminderAlert, onStateChange]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (socketRef.current) socketRef.current.close();
    };
  }, [connect]);

  const sendPing = useCallback(() => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'ping' }));
    }
  }, []);

  return { isConnected, sendPing };
}
