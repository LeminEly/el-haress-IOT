import { useEffect, useRef, useState } from 'react';

import { useAuthStore } from '@/stores/auth';
import type { LiveReading } from '@/types/api';

/** Connexion WebSocket au flux temps reel de l'entreprise (reconnexion auto). */
export function useLiveReadings(onReading: (reading: LiveReading) => void) {
  const token = useAuthStore((state) => state.token);
  const [connected, setConnected] = useState(false);
  const callbackRef = useRef(onReading);
  callbackRef.current = onReading;

  useEffect(() => {
    if (!token) {
      return;
    }
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${scheme}://${window.location.host}/api/v1/ws/live?token=${encodeURIComponent(token)}`;
    let socket: WebSocket | null = null;
    let closedByUs = false;
    let retryTimer = 0;

    const connect = () => {
      socket = new WebSocket(url);
      socket.onopen = () => setConnected(true);
      socket.onmessage = (event) => {
        try {
          callbackRef.current(JSON.parse(event.data) as LiveReading);
        } catch {
          /* message malforme : ignore */
        }
      };
      socket.onclose = () => {
        setConnected(false);
        if (!closedByUs) {
          retryTimer = window.setTimeout(connect, 3000);
        }
      };
      socket.onerror = () => socket?.close();
    };
    connect();

    return () => {
      closedByUs = true;
      window.clearTimeout(retryTimer);
      socket?.close();
    };
  }, [token]);

  return { connected };
}
