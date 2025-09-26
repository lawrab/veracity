import { useEffect, useRef, useState, useCallback } from 'react';

export interface WebSocketMessage {
  type: string;
  data?: any;
  timestamp?: string;
  error?: string;
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
  const {
    autoReconnect = true,
    reconnectInterval = 5000,
    maxReconnectAttempts = 10,
    heartbeatInterval = 30000,
    authToken,
    onOpen,
    onClose,
    onError,
    onMessage,
  } = options;

  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [readyState, setReadyState] = useState<WebSocketState>(WebSocketState.CONNECTING);
  
  const ws = useRef<WebSocket | null>(null);
  const reconnectCount = useRef(0);
  const reconnectTimeout = useRef<NodeJS.Timeout>();
  const heartbeatInterval = useRef<NodeJS.Timeout>();
  const messageQueue = useRef<any[]>([]);
  const subscribedChannels = useRef<Set<string>>(new Set([channel]));

  const startHeartbeat = useCallback(() => {
    if (heartbeatInterval.current) {
      clearInterval(heartbeatInterval.current);
    }

    heartbeatInterval.current = setInterval(() => {
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({ type: 'pong' }));
      }
    }, heartbeatInterval);
  }, [heartbeatInterval]);

  const stopHeartbeat = useCallback(() => {
    if (heartbeatInterval.current) {
      clearInterval(heartbeatInterval.current);
    }
  }, []);

  const processMessageQueue = useCallback(() => {
    while (messageQueue.current.length > 0 && ws.current?.readyState === WebSocket.OPEN) {
      const message = messageQueue.current.shift();
      ws.current.send(JSON.stringify(message));
    }
  }, []);

  const connect = useCallback(() => {
    try {
      // Build connection URL with parameters
      const wsUrl = new URL(url);
      wsUrl.searchParams.append('channel', channel);
      if (authToken) {
        wsUrl.searchParams.append('token', authToken);
      }

      ws.current = new WebSocket(wsUrl.toString());
      setReadyState(WebSocketState.CONNECTING);

      ws.current.onopen = () => {
        console.log('WebSocket connected');
        setReadyState(WebSocketState.OPEN);
        reconnectCount.current = 0;
        
        // Subscribe to all channels
        subscribedChannels.current.forEach(ch => {
          if (ch !== channel) {
            ws.current?.send(JSON.stringify({
              type: 'subscribe',
              channel: ch
            }));
          }
        });

        // Process queued messages
        processMessageQueue();
        
        // Start heartbeat
        startHeartbeat();
        
        onOpen?.();
      };

      ws.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage;
          
          // Handle ping messages
          if (message.type === 'ping') {
            ws.current?.send(JSON.stringify({ type: 'pong' }));
            return;
          }

          setLastMessage(message);
          onMessage?.(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        onError?.(error);
      };

      ws.current.onclose = () => {
        console.log('WebSocket disconnected');
        setReadyState(WebSocketState.CLOSED);
        stopHeartbeat();
        onClose?.();

        // Auto-reconnect if enabled
        if (autoReconnect && reconnectCount.current < maxReconnectAttempts) {
          setReadyState(WebSocketState.RECONNECTING);
          reconnectTimeout.current = setTimeout(() => {
            reconnectCount.current++;
            console.log(`Reconnecting... (attempt ${reconnectCount.current})`);
            connect();
          }, reconnectInterval);
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setReadyState(WebSocketState.CLOSED);
    }
  }, [
    url,
    channel,
    authToken,
    autoReconnect,
    reconnectInterval,
    maxReconnectAttempts,
    onOpen,
    onClose,
    onError,
    onMessage,
    processMessageQueue,
    startHeartbeat,
    stopHeartbeat,
  ]);

  const sendMessage = useCallback((message: any) => {
    const data = typeof message === 'string' ? { data: message } : message;
    
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data));
    } else {
      // Queue message for later delivery
      messageQueue.current.push(data);
    }
  }, []);

  const subscribe = useCallback((newChannel: string) => {
    subscribedChannels.current.add(newChannel);
    
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        type: 'subscribe',
        channel: newChannel
      }));
    }
  }, []);

  const unsubscribe = useCallback((channelToRemove: string) => {
    subscribedChannels.current.delete(channelToRemove);
    
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        type: 'unsubscribe',
        channel: channelToRemove
      }));
    }
  }, []);

  const reconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
    }
    
    if (ws.current) {
      ws.current.close();
    }
    
    reconnectCount.current = 0;
    connect();
  }, [connect]);

  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
    }
    
    stopHeartbeat();
    
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }
  }, [stopHeartbeat]);

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    sendMessage,
    lastMessage,
    readyState,
    subscribe,
    unsubscribe,
    reconnect,
    disconnect,
  };
}

// Specialized hook for trend updates
export function useTrendUpdates(onTrendUpdate?: (trend: any) => void) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const wsUrl = apiUrl.replace('http', 'ws') + '/api/v1/ws/v2/trends';
  
  return useWebSocket(wsUrl, 'trends', {
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