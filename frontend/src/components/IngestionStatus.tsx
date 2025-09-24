'use client';

import { useEffect } from 'react';
import { useDashboardStore } from '@/store/dashboardStore';
import { CollectorStatus } from '@/types/ingestion';

const StatusBadge = ({ status }: { status: CollectorStatus }) => {
  const getStatusColor = () => {
    switch (status) {
      case CollectorStatus.IDLE:
        return 'bg-gray-100 text-gray-800';
      case CollectorStatus.RUNNING:
        return 'bg-blue-100 text-blue-800 animate-pulse';
      case CollectorStatus.ERROR:
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case CollectorStatus.IDLE:
        return '⭘';
      case CollectorStatus.RUNNING:
        return '↻';
      case CollectorStatus.ERROR:
        return '✕';
      default:
        return '?';
    }
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor()}`}>
      <span className="mr-1">{getStatusIcon()}</span>
      {status}
    </span>
  );
};

export default function IngestionStatus() {
  const { 
    ingestionStatus, 
    loadingStatus, 
    fetchIngestionStatus, 
    triggerIngestion,
    startPolling,
    stopPolling
  } = useDashboardStore();

  useEffect(() => {
    fetchIngestionStatus();
  }, []);

  const handleTrigger = async (platform: 'reddit' | 'twitter' | 'news' | 'test') => {
    await triggerIngestion(platform);
  };

  if (loadingStatus && !ingestionStatus) {
    return (
      <div className="bg-white shadow rounded-lg p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-2">
            <div className="h-8 bg-gray-200 rounded"></div>
            <div className="h-8 bg-gray-200 rounded"></div>
            <div className="h-8 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 shadow dark:shadow-gray-700/20 rounded-lg p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Data Collectors</h2>
        <div className="flex space-x-2">
          <button
            onClick={fetchIngestionStatus}
            disabled={loadingStatus}
            className="px-3 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 text-sm rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 transition-colors"
          >
            {loadingStatus ? 'Refreshing...' : 'Refresh'}
          </button>
          <button
            onClick={() => handleTrigger('test')}
            className="px-4 py-2 bg-primary-600 text-white text-sm rounded-md hover:bg-primary-700 transition-colors"
          >
            Run Test Collection
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {/* Reddit Collector */}
        <div className="flex items-center justify-between p-4 border dark:border-gray-600 rounded-lg">
          <div className="flex items-center">
            <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center mr-3">
              <span className="text-orange-600 font-bold">R</span>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-900 dark:text-white">Reddit</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">Collecting from subreddits</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <StatusBadge status={ingestionStatus?.collectors.reddit || CollectorStatus.IDLE} />
            <button
              onClick={() => handleTrigger('reddit')}
              disabled={ingestionStatus?.collectors.reddit === CollectorStatus.RUNNING}
              className="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 text-xs rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Trigger
            </button>
          </div>
        </div>

        {/* Twitter Collector */}
        <div className="flex items-center justify-between p-4 border dark:border-gray-600 rounded-lg">
          <div className="flex items-center">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center mr-3">
              <span className="text-blue-600 font-bold">T</span>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-900 dark:text-white">Twitter</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">Collecting tweets</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <StatusBadge status={ingestionStatus?.collectors.twitter || CollectorStatus.IDLE} />
            <button
              onClick={() => handleTrigger('twitter')}
              disabled={ingestionStatus?.collectors.twitter === CollectorStatus.RUNNING}
              className="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 text-xs rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Trigger
            </button>
          </div>
        </div>

        {/* News Collector */}
        <div className="flex items-center justify-between p-4 border dark:border-gray-600 rounded-lg">
          <div className="flex items-center">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center mr-3">
              <span className="text-green-600 font-bold">N</span>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-900 dark:text-white">News</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">Collecting articles</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <StatusBadge status={ingestionStatus?.collectors.news || CollectorStatus.IDLE} />
            <button
              onClick={() => handleTrigger('news')}
              disabled={ingestionStatus?.collectors.news === CollectorStatus.RUNNING}
              className="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 text-xs rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Trigger
            </button>
          </div>
        </div>
      </div>

      {ingestionStatus?.last_update && (
        <div className="mt-4 text-xs text-gray-500 dark:text-gray-400 text-center">
          Last updated: {new Date(ingestionStatus.last_update).toLocaleTimeString()}
        </div>
      )}
    </div>
  );
}