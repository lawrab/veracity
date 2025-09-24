'use client';

import { useEffect } from 'react';
import { useDashboardStore } from '@/store/dashboardStore';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function DataStatistics() {
  const { dataSummary, loadingSummary, fetchDataSummary } = useDashboardStore();

  useEffect(() => {
    fetchDataSummary();
  }, []);

  const getTotalCount = () => dataSummary.reduce((sum, item) => sum + item.count, 0);

  const getPlatformColor = (platform: string) => {
    switch (platform.toLowerCase()) {
      case 'reddit':
        return '#FF5722';
      case 'twitter':
        return '#1DA1F2';
      case 'news':
        return '#4CAF50';
      default:
        return '#9E9E9E';
    }
  };

  if (loadingSummary) {
    return (
      <div className="bg-white dark:bg-gray-800 shadow dark:shadow-gray-700/20 rounded-lg p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 bg-gray-200 rounded"></div>
            ))}
          </div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 shadow dark:shadow-gray-700/20 rounded-lg p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Data Statistics</h2>
        <button
          onClick={fetchDataSummary}
          disabled={loadingSummary}
          className="px-3 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 text-sm rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 transition-colors"
        >
          {loadingSummary ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
          <div className="flex items-center">
            <div className="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center mr-3">
              <span className="text-white text-sm font-bold">#</span>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-300">Total Documents</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{getTotalCount().toLocaleString()}</p>
            </div>
          </div>
        </div>

        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
          <div className="flex items-center">
            <div className="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center mr-3">
              <span className="text-white text-sm font-bold">📊</span>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-300">Platforms</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{dataSummary.length}</p>
            </div>
          </div>
        </div>

        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
          <div className="flex items-center">
            <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center mr-3">
              <span className="text-white text-sm font-bold">🔄</span>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-300">Active Collectors</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{dataSummary.filter(s => s.count > 0).length}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Platform Breakdown */}
      {dataSummary.length > 0 ? (
        <>
          <div className="mb-6">
            <h3 className="text-md font-medium text-gray-900 dark:text-white mb-3">Platform Breakdown</h3>
            <div className="space-y-3">
              {dataSummary.map((summary) => (
                <div key={summary.platform} className="flex items-center justify-between p-3 border dark:border-gray-600 rounded-lg">
                  <div className="flex items-center">
                    <div 
                      className="w-4 h-4 rounded-full mr-3"
                      style={{ backgroundColor: getPlatformColor(summary.platform) }}
                    ></div>
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-white capitalize">{summary.platform}</p>
                      {summary.topics.length > 0 && (
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          Topics: {summary.topics.slice(0, 3).join(', ')}
                          {summary.topics.length > 3 && '...'}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-semibold text-gray-900 dark:text-white">{summary.count.toLocaleString()}</p>
                    <div className="w-20 bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                      <div
                        className="h-2 rounded-full"
                        style={{
                          backgroundColor: getPlatformColor(summary.platform),
                          width: `${Math.min((summary.count / Math.max(getTotalCount(), 1)) * 100, 100)}%`,
                        }}
                      ></div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Chart */}
          <div>
            <h3 className="text-md font-medium text-gray-900 dark:text-white mb-3">Collection Overview</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={dataSummary}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="platform" 
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => value.charAt(0).toUpperCase() + value.slice(1)}
                  />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip 
                    formatter={(value) => [value.toLocaleString(), 'Documents']}
                    labelFormatter={(label) => `Platform: ${label.charAt(0).toUpperCase() + label.slice(1)}`}
                  />
                  <Bar 
                    dataKey="count" 
                    fill="#3B82F6"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      ) : (
        <div className="text-center py-8">
          <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-gray-400 text-2xl">📊</span>
          </div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No Data Available</h3>
          <p className="text-gray-500 dark:text-gray-400 mb-4">Start collecting data to see statistics here.</p>
          <button
            onClick={fetchDataSummary}
            className="px-4 py-2 bg-primary-600 text-white text-sm rounded-md hover:bg-primary-700 transition-colors"
          >
            Refresh Data
          </button>
        </div>
      )}
    </div>
  );
}