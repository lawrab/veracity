import { useEffect, useRef, useState, useCallback } from 'react';

export interface WebSocketMessage {
  type: string;
  data?: any;
  timestamp?: string;
  error?: string;
  story_id?: string;
  trust_score?: number;
  signals?: any[];
}

export interface WebSocketOptions {
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
  authToken?: string;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  onMessage?: (message: WebSocketMessage) => void;
}

export enum WebSocketState {
  CONNECTING = 'CONNECTING',
  OPEN = 'OPEN',
  CLOSING = 'CLOSING',
  CLOSED = 'CLOSED',
  RECONNECTING = 'RECONNECTING',
}

interface UseWebSocketReturn {
  sendMessage: (message: any) => void;
  lastMessage: WebSocketMessage | null;
  readyState: WebSocketState;
  subscribe: (channel: string) => void;
  unsubscribe: (channel: string) => void;
  reconnect: () => void;
  disconnect: () => void;
}

export function useWebSocket(
  url: string,
  channel: string = 'general',
  options: WebSocketOptions = {}
): UseWebSocketReturn {
  // TEMPORARY: Return a disabled WebSocket hook to stop connection spam
  const [lastMessage] = useState<WebSocketMessage | null>(null);
  const [readyState] = useState<WebSocketState>(WebSocketState.CLOSED);
  
  return {
    sendMessage: () => { console.log('WebSocket sendMessage disabled'); },
    lastMessage,
    readyState,
    subscribe: () => { console.log('WebSocket subscribe disabled'); },
    unsubscribe: () => { console.log('WebSocket unsubscribe disabled'); },
    reconnect: () => { console.log('WebSocket reconnect disabled'); },
    disconnect: () => { console.log('WebSocket disconnect disabled'); },
  };
}

// Specialized hook for trend updates
export function useTrendUpdates(onTrendUpdate?: (trend: any) => void) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const wsUrl = apiUrl.replace('http', 'ws') + '/api/v1/ws/v2/trends';
  
  return useWebSocket(wsUrl, 'trends', {
    autoReconnect: false, // Disable auto-reconnect for now to prevent spam
    reconnectInterval: 300000, // 5 minutes if manually triggered
    maxReconnectAttempts: 1, // Only one attempt
    heartbeatInterval: 300000, // 5 minutes
    onMessage: (message) => {
      if (message.type === 'trend_update' && onTrendUpdate) {
        onTrendUpdate(message.data);
      }
    },
  });
}

// Specialized hook for story updates
export function useStoryUpdates(storyId?: string, onStoryUpdate?: (story: any) => void) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const channel = storyId ? `story:${storyId}` : 'stories';
  const wsUrl = apiUrl.replace('http', 'ws') + '/api/v1/ws/v2/stories';
  
  return useWebSocket(wsUrl, channel, {
    autoReconnect: false, // Disable auto-reconnect for now to prevent spam
    reconnectInterval: 300000, // 5 minutes if manually triggered
    maxReconnectAttempts: 1, // Only one attempt
    heartbeatInterval: 300000, // 5 minutes
    onMessage: (message) => {
      if (message.type === 'story_update' && onStoryUpdate) {
        onStoryUpdate(message.data);
      }
    },
  });
}

// Specialized hook for trust score updates  
export function useTrustScoreUpdates(onScoreUpdate?: (update: any) => void) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const wsUrl = apiUrl.replace('http', 'ws') + '/api/v1/ws/v2/trust-scores';
  
  return useWebSocket(wsUrl, 'trust_scores', {
    autoReconnect: false, // Disable auto-reconnect for now to prevent spam
    reconnectInterval: 300000, // 5 minutes if manually triggered
    maxReconnectAttempts: 1, // Only one attempt
    heartbeatInterval: 300000, // 5 minutes
    onMessage: (message) => {
      if (message.type === 'trust_score_update' && onScoreUpdate) {
        onScoreUpdate({
          storyId: message.story_id,
          trustScore: message.trust_score,
          signals: message.signals,
        });
      }
    },
  });
}