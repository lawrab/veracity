'use client';

import { useState, useEffect } from 'react';
import SystemHealth from '@/components/SystemHealth';
import IngestionStatus from '@/components/IngestionStatus';
import DataStatistics from '@/components/DataStatistics';
import { useDarkMode } from '@/hooks/useDarkMode';
import { useDashboardStore } from '@/store/dashboardStore';

export default function AdminDashboard() {
  const [currentTime, setCurrentTime] = useState<Date | null>(null);
  const { isDark, toggleDarkMode } = useDarkMode();
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
    const interval = setInterval(() => setCurrentTime(new Date()), 60000); // Update every minute instead of every second
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow dark:shadow-gray-700/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center mr-3">
                <span className="text-white font-bold text-sm">V</span>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Veracity Admin</h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">System monitoring and data management</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={refreshAll}
                className="px-3 py-2 bg-primary-600 hover:bg-primary-700 text-white text-sm rounded-md transition-colors"
              >
                🔄 Refresh All
              </button>
              <button
                onClick={toggleDarkMode}
                className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
              >
                {isDark ? (
                  <span className="text-yellow-500">☀️</span>
                ) : (
                  <span className="text-gray-600">🌙</span>
                )}
              </button>
              <div className="text-right">
                <p className="text-sm font-medium text-gray-900 dark:text-white">Admin Dashboard</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {currentTime ? `${currentTime.toLocaleDateString()} ${currentTime.toLocaleTimeString()}` : '--'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column */}
          <div className="space-y-8">
            <SystemHealth />
            <IngestionStatus />
          </div>

          {/* Right Column */}
          <div className="space-y-8">
            <DataStatistics />
          </div>
        </div>

        {/* Footer */}
        <footer className="mt-16 py-8 border-t border-gray-200 dark:border-gray-700">
          <div className="text-center">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Veracity Platform - Social Media Trend & News Trustability Analysis
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
              Real-time monitoring and data collection system
            </p>
          </div>
        </footer>
      </main>
    </div>
  );
}