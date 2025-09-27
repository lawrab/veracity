'use client';

import { useEffect, useCallback, useRef } from 'react';
import useWebSocket, { ReadyState } from 'react-use-websocket';

export interface WebSocketMessage {
  type: string;
  data?: any;
  timestamp?: string;
  error?: string;
  story_id?: string;
  trust_score?: number;
  signals?: any[];
  channel?: string;
}

export enum WebSocketState {
  CONNECTING = 'CONNECTING',
  OPEN = 'OPEN',
  CLOSING = 'CLOSING',
  CLOSED = 'CLOSED',
  RECONNECTING = 'RECONNECTING',
}

interface UseSharedWebSocketOptions {
  shouldReconnect?: boolean;
  reconnectAttempts?: number;
  reconnectInterval?: number;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
}

// Convert ReadyState to our WebSocketState enum
const mapReadyState = (readyState: ReadyState): WebSocketState => {
  switch (readyState) {
    case ReadyState.CONNECTING:
      return WebSocketState.CONNECTING;
    case ReadyState.OPEN:
      return WebSocketState.OPEN;
    case ReadyState.CLOSING:
      return WebSocketState.CLOSING;
    case ReadyState.CLOSED:
      return WebSocketState.CLOSED;
    default:
      return WebSocketState.CLOSED;
  }
};

export function useSharedWebSocket(options: UseSharedWebSocketOptions = {}) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const wsUrl = apiUrl.replace('http', 'ws') + '/api/v1/ws/connect?channel=general';
  
  const {
    shouldReconnect = true,
    reconnectAttempts = 10,
    reconnectInterval = 3000,
    onOpen,
    onClose,
    onError,
  } = options;

  const subscriptionsRef = useRef<Set<string>>(new Set());
  const messageHandlersRef = useRef<Map<string, (message: WebSocketMessage) => void>>(new Map());

  const {
    sendMessage,
    lastMessage,
    readyState,
    getWebSocket
  } = useWebSocket(
    wsUrl,
    {
      shouldReconnect: () => shouldReconnect,
      reconnectAttempts,
      reconnectInterval,
      share: true, // Key: This enables connection sharing across components
      onOpen: () => {
        console.log('WebSocket connected');
        onOpen?.();
        
        // Re-subscribe to all channels after reconnection
        subscriptionsRef.current.forEach(channel => {
          sendMessage(JSON.stringify({ type: 'subscribe', channel }));
        });
      },
      onClose: () => {
        console.log('WebSocket disconnected');
        onClose?.();
      },
      onError: (error) => {
        console.warn('WebSocket error:', error);
        onError?.(error);
      },
      onMessage: (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          
          // Route message to appropriate handler based on type or channel
          const channel = message.channel || message.type;
          const handler = messageHandlersRef.current.get(channel);
          
          if (handler) {
            handler(message);
          }
        } catch (error) {
          console.warn('Failed to parse WebSocket message:', error);
        }
      }
    }
  );

  const subscribe = useCallback((channel: string, handler: (message: WebSocketMessage) => void) => {
    // Add to subscriptions
    subscriptionsRef.current.add(channel);
    messageHandlersRef.current.set(channel, handler);
    
    // Send subscription message if connected
    if (readyState === ReadyState.OPEN) {
      sendMessage(JSON.stringify({ type: 'subscribe', channel }));
    }
  }, [readyState, sendMessage]);

  const unsubscribe = useCallback((channel: string) => {
    // Remove from subscriptions
    subscriptionsRef.current.delete(channel);
    messageHandlersRef.current.delete(channel);
    
    // Send unsubscription message if connected
    if (readyState === ReadyState.OPEN) {
      sendMessage(JSON.stringify({ type: 'unsubscribe', channel }));
    }
  }, [readyState, sendMessage]);

  const send = useCallback((message: any) => {
    if (readyState === ReadyState.OPEN) {
      sendMessage(JSON.stringify(message));
    } else {
      console.warn('Cannot send message: WebSocket not connected');
    }
  }, [readyState, sendMessage]);

  return {
    subscribe,
    unsubscribe,
    send,
    lastMessage,
    readyState: mapReadyState(readyState),
    isConnected: readyState === ReadyState.OPEN,
    getWebSocket
  };
}