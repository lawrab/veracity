'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { useTrendUpdates, useStoryUpdates, useTrustScoreUpdates } from '@/hooks/useWebSocket';
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
  const [isConnected, setIsConnected] = useState(false);
  const [latestTrend, setLatestTrend] = useState<any | null>(null);
  const [latestStory, setLatestStory] = useState<any | null>(null);
  const [latestTrustScore, setLatestTrustScore] = useState<any | null>(null);

  // Connect to trend updates
  const trendsWs = useTrendUpdates((trend) => {
    setLatestTrend(trend);
    
    // Show toast notification for high-velocity trends
    if (trend.velocity > 1000) {
      toast.success(`New trending topic: ${trend.name}`, {
        duration: 5000,
        position: 'top-right',
      });
    }
  });

  // Connect to story updates
  const storiesWs = useStoryUpdates(undefined, (story) => {
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

  // Connect to trust score updates
  const trustWs = useTrustScoreUpdates((update) => {
    setLatestTrustScore(update);
    
    // Alert for low trust scores
    if (update.trustScore < 30) {
      toast.error(`Low trust score detected: ${update.trustScore}%`, {
        duration: 5000,
        position: 'bottom-right',
      });
    }
  });

  // Track connection status
  useEffect(() => {
    const checkConnection = () => {
      const connected = 
        trendsWs.readyState === 'OPEN' ||
        storiesWs.readyState === 'OPEN' ||
        trustWs.readyState === 'OPEN';
      setIsConnected(connected);
    };

    checkConnection();
    const interval = setInterval(checkConnection, 1000);

    return () => clearInterval(interval);
  }, [trendsWs.readyState, storiesWs.readyState, trustWs.readyState]);

  const subscribeToStory = (storyId: string) => {
    storiesWs.subscribe(`story:${storyId}`);
  };

  const unsubscribeFromStory = (storyId: string) => {
    storiesWs.unsubscribe(`story:${storyId}`);
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