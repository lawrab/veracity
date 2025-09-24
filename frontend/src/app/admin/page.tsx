'use client';

import { useState, useEffect } from 'react';
import SystemHealth from '@/components/SystemHealth';
import IngestionStatus from '@/components/IngestionStatus';
import DataStatistics from '@/components/DataStatistics';
import { useDashboardStore } from '@/store/dashboardStore';

export default function AdminPage() {
  const [currentTime, setCurrentTime] = useState<Date | null>(null);
  const { fetchIngestionStatus, fetchDataSummary, checkApiHealth } = useDashboardStore();

  const refreshAll = async () => {
    await Promise.all([
      fetchIngestionStatus(),
      fetchDataSummary(),
      checkApiHealth()
    ]);
  };

  useEffect(() => {
    setCurrentTime(new Date());
    const interval = setInterval(() => setCurrentTime(new Date()), 60000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Admin Dashboard
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            System monitoring and data management
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <button
            onClick={refreshAll}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm rounded-lg transition-colors"
          >
            🔄 Refresh All
          </button>
          <div className="text-right">
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              {currentTime ? currentTime.toLocaleDateString() : '--'}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {currentTime ? currentTime.toLocaleTimeString() : '--'}
            </p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column */}
        <div className="space-y-6">
          <SystemHealth />
          <IngestionStatus />
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          <DataStatistics />
        </div>
      </div>
    </div>
  );
}