'use client';

import React, { useEffect, useState } from 'react';
import { useWebSocketContext } from '@/contexts/WebSocketContext';
import { WifiIcon, XCircleIcon } from '@heroicons/react/24/outline';

export default function ConnectionStatus() {
  const { isConnected } = useWebSocketContext();
  const [showStatus, setShowStatus] = useState(false);

  // Only show status after mount to prevent hydration issues
  useEffect(() => {
    setShowStatus(true);
  }, []);

  if (!showStatus) {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 z-50">
      <div
        className={`flex items-center space-x-2 px-3 py-2 rounded-full shadow-lg transition-all duration-300 ${
          isConnected
            ? 'bg-green-500 text-white'
            : 'bg-yellow-500 text-white animate-pulse'
        }`}
      >
        {isConnected ? (
          <>
            <WifiIcon className="h-4 w-4" />
            <span className="text-xs font-medium">Live</span>
          </>
        ) : (
          <>
            <XCircleIcon className="h-4 w-4" />
            <span className="text-xs font-medium">Connecting...</span>
          </>
        )}
      </div>
    </div>
  );
}