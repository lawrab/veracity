'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { useTrendUpdates, useStoryUpdates, useTrustScoreUpdates } from '@/hooks/useRealtimeData';
import { useSharedWebSocket } from '@/hooks/useSharedWebSocket';
import { toast } from 'react-hot-toast';

interface WebSocketContextType {
  isConnected: boolean;
  latestTrend: any | null;
  latestStory: any | null;
  latestTrustScore: any | null;
  subscribeToStory: (storyId: string) => void;
  unsubscribeFromStory: (storyId: string) => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const [latestTrend, setLatestTrend] = useState<any | null>(null);
  const [latestStory, setLatestStory] = useState<any | null>(null);
  const [latestTrustScore, setLatestTrustScore] = useState<any | null>(null);
  const [hasMounted, setHasMounted] = useState(false);

  // Use the shared WebSocket connection
  const { isConnected } = useSharedWebSocket({
    shouldReconnect: true,
    reconnectAttempts: 10,
    reconnectInterval: 3000,
    onOpen: () => {
      console.log('WebSocket connected successfully');
    },
    onClose: () => {
      console.log('WebSocket disconnected');
    },
    onError: (error) => {
      console.error('WebSocket error:', error);
    },
  });

  useEffect(() => {
    setHasMounted(true);
  }, []);

  // Subscribe to trend updates using shared connection
  useTrendUpdates((trend) => {
    setLatestTrend(trend);
    
    // Show toast notification for high-velocity trends
    if (trend.velocity > 1000) {
      toast.success(`New trending topic: ${trend.name}`, {
        duration: 5000,
        position: 'top-right',
      });
    }
  });

  // Subscribe to story updates using shared connection
  useStoryUpdates(undefined, (story) => {
    setLatestStory(story);
    
    // Show toast for breaking news
    if (story.is_breaking) {
      toast.error(`BREAKING: ${story.title}`, {
        duration: 7000,
        position: 'top-center',
        style: {
          background: '#ef4444',
          color: '#fff',
        },
      });
    }
  });

  // Subscribe to trust score updates using shared connection
  useTrustScoreUpdates((update) => {
    setLatestTrustScore(update);
    
    // Alert for low trust scores
    if (update.trustScore < 30) {
      toast.error(`Low trust score detected: ${update.trustScore}%`, {
        duration: 5000,
        position: 'bottom-right',
      });
    }
  });

  // These functions are now handled by the individual hooks
  const subscribeToStory = (storyId: string) => {
    console.log(`Subscribe to story ${storyId} handled by useStoryUpdates hook`);
  };

  const unsubscribeFromStory = (storyId: string) => {
    console.log(`Unsubscribe from story ${storyId} handled by useStoryUpdates hook`);
  };

  return (
    <WebSocketContext.Provider
      value={{
        isConnected,
        latestTrend,
        latestStory,
        latestTrustScore,
        subscribeToStory,
        unsubscribeFromStory,
      }}
    >
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocketContext() {
  const context = useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
}