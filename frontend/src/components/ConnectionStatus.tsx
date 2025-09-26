'use client';

import { useWebSocketContext } from '@/contexts/WebSocketContext';
import { WifiIcon, XCircleIcon } from '@heroicons/react/24/outline';

export default function ConnectionStatus() {
  const { isConnected } = useWebSocketContext();

  return (
    <div className="fixed bottom-4 right-4 z-50">
      <div
        className={`flex items-center space-x-2 px-3 py-2 rounded-full shadow-lg transition-all ${
          isConnected
            ? 'bg-green-500 text-white'
            : 'bg-red-500 text-white animate-pulse'
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
            <span className="text-xs font-medium">Reconnecting...</span>
          </>
        )}
      </div>
    </div>
  );
}