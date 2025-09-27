'use client';

import { useEffect, useRef } from 'react';
import { useSharedWebSocket, WebSocketMessage } from './useSharedWebSocket';

// Specialized hook for trend updates using shared connection
export function useTrendUpdates(onTrendUpdate?: (trend: any) => void) {
  const { subscribe, unsubscribe, isConnected } = useSharedWebSocket();
  const handlerRef = useRef(onTrendUpdate);
  
  // Update handler ref when callback changes
  useEffect(() => {
    handlerRef.current = onTrendUpdate;
  }, [onTrendUpdate]);

  useEffect(() => {
    const handleMessage = (message: WebSocketMessage) => {
      if (message.type === 'trend_update' && handlerRef.current) {
        handlerRef.current(message.data);
      }
    };

    subscribe('trends', handleMessage);
    
    return () => {
      unsubscribe('trends');
    };
  }, [subscribe, unsubscribe]);

  return { isConnected };
}

// Specialized hook for story updates using shared connection
export function useStoryUpdates(storyId?: string, onStoryUpdate?: (story: any) => void) {
  const { subscribe, unsubscribe, isConnected } = useSharedWebSocket();
  const handlerRef = useRef(onStoryUpdate);
  const storyIdRef = useRef(storyId);
  
  // Update refs when props change
  useEffect(() => {
    handlerRef.current = onStoryUpdate;
    storyIdRef.current = storyId;
  }, [onStoryUpdate, storyId]);

  useEffect(() => {
    const handleMessage = (message: WebSocketMessage) => {
      if (message.type === 'story_update' && handlerRef.current) {
        // Filter by story ID if specified
        if (storyIdRef.current && message.story_id !== storyIdRef.current) {
          return;
        }
        handlerRef.current(message.data);
      }
    };

    const channel = storyId ? `story:${storyId}` : 'stories';
    subscribe(channel, handleMessage);
    
    return () => {
      unsubscribe(channel);
    };
  }, [subscribe, unsubscribe, storyId]);

  return { isConnected };
}

// Specialized hook for trust score updates using shared connection
export function useTrustScoreUpdates(onScoreUpdate?: (update: any) => void) {
  const { subscribe, unsubscribe, isConnected } = useSharedWebSocket();
  const handlerRef = useRef(onScoreUpdate);
  
  // Update handler ref when callback changes
  useEffect(() => {
    handlerRef.current = onScoreUpdate;
  }, [onScoreUpdate]);

  useEffect(() => {
    const handleMessage = (message: WebSocketMessage) => {
      if (message.type === 'trust_score_update' && handlerRef.current) {
        handlerRef.current({
          storyId: message.story_id,
          trustScore: message.trust_score,
          signals: message.signals,
        });
      }
    };

    subscribe('trust_scores', handleMessage);
    
    return () => {
      unsubscribe('trust_scores');
    };
  }, [subscribe, unsubscribe]);

  return { isConnected };
}

// Generic hook for custom channel subscriptions
export function useChannelSubscription(
  channel: string,
  messageHandler: (message: WebSocketMessage) => void
) {
  const { subscribe, unsubscribe, isConnected } = useSharedWebSocket();
  const handlerRef = useRef(messageHandler);
  
  // Update handler ref when callback changes
  useEffect(() => {
    handlerRef.current = messageHandler;
  }, [messageHandler]);

  useEffect(() => {
    const handleMessage = (message: WebSocketMessage) => {
      handlerRef.current(message);
    };

    subscribe(channel, handleMessage);
    
    return () => {
      unsubscribe(channel);
    };
  }, [subscribe, unsubscribe, channel]);

  return { isConnected };
}