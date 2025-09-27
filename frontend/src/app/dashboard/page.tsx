'use client';

import React, { useEffect } from 'react';
import StoryList from '@/components/stories/StoryList';
import TrendFeed from '@/components/trends/TrendFeed';
import ConnectionStatus from '@/components/ConnectionStatus';
import { useDashboardStore } from '@/store/dashboardStore';
import { 
  ChartBarIcon,
  NewspaperIcon,
  ArrowTrendingUpIcon,
  ShieldCheckIcon 
} from '@heroicons/react/24/outline';

export default function DashboardPage() {
  const { 
    dataSummary, 
    trustStats, 
    loadingTrustStats,
    fetchDataSummary, 
    fetchTrustStats,
    startPolling, 
    stopPolling 
  } = useDashboardStore();

  useEffect(() => {
    fetchDataSummary();
    fetchTrustStats();
    startPolling();
    return () => stopPolling();
  }, []);

  // Calculate dynamic statistics from real data
  const totalDataPoints = dataSummary.reduce((sum, item) => sum + item.count, 0);
  const activePlatforms = dataSummary.filter(s => s.count > 0).length;
  const totalTopics = [...new Set(dataSummary.flatMap(s => s.topics))].length;

  return (
    <div className="space-y-6">
        <ConnectionStatus />
        {/* Page Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Dashboard
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Real-time social media trends and news trustability analysis
          </p>
        </div>

        {/* Stats Overview - Now with real data */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Total Data Points"
            value={totalDataPoints.toLocaleString()}
            change={totalDataPoints > 0 ? "+100%" : "0%"}
            icon={ChartBarIcon}
            color="blue"
            loading={!dataSummary.length}
          />
          <StatCard
            title="Active Platforms"
            value={activePlatforms.toString()}
            change={activePlatforms > 0 ? `+${activePlatforms}` : "0"}
            icon={NewspaperIcon}
            color="green"
            loading={!dataSummary.length}
          />
          <StatCard
            title="Trending Topics"
            value={totalTopics.toString()}
            change={totalTopics > 0 ? `+${Math.min(totalTopics, 99)}` : "0"}
            icon={ArrowTrendingUpIcon}
            color="purple"
            loading={!dataSummary.length}
          />
          <StatCard
            title="Avg Trust Score"
            value={trustStats ? `${trustStats.average_score}%` : "0%"}
            change={trustStats ? `${trustStats.score_trend >= 0 ? '+' : ''}${trustStats.score_trend.toFixed(1)}%` : "0%"}
            icon={ShieldCheckIcon}
            color="indigo"
            loading={loadingTrustStats}
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Trending Stories - Takes up 2 columns */}
          <div className="lg:col-span-2">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
                Trending Stories
              </h2>
              <StoryList />
            </div>
          </div>

          {/* Live Trend Feed - Takes up 1 column */}
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
                Live Trends
              </h2>
              <TrendFeed />
            </div>
          </div>
        </div>
      </div>
  );
}

interface StatCardProps {
  title: string;
  value: string;
  change: string;
  icon: React.ComponentType<{ className?: string }>;
  color: 'blue' | 'green' | 'indigo' | 'purple';
  loading?: boolean;
}

function StatCard({ title, value, change, icon: Icon, color, loading = false }: StatCardProps) {
  const colorClasses = {
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    indigo: 'bg-indigo-500',
    purple: 'bg-purple-500'
  };

  const isPositive = change.startsWith('+');

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center">
          <div className="bg-gray-300 dark:bg-gray-600 p-3 rounded-lg animate-pulse">
            <div className="h-6 w-6 bg-gray-400 dark:bg-gray-500 rounded"></div>
          </div>
          <div className="ml-4 flex-1">
            <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-20 mb-2 animate-pulse"></div>
            <div className="flex items-baseline">
              <div className="h-8 bg-gray-300 dark:bg-gray-600 rounded w-16 animate-pulse"></div>
              <div className="ml-2 h-4 bg-gray-300 dark:bg-gray-600 rounded w-12 animate-pulse"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex items-center">
        <div className={`${colorClasses[color]} p-3 rounded-lg`}>
          <Icon className="h-6 w-6 text-white" />
        </div>
        <div className="ml-4 flex-1">
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
            {title}
          </p>
          <div className="flex items-baseline">
            <p className="text-2xl font-semibold text-gray-900 dark:text-white">
              {value}
            </p>
            <span className={`ml-2 text-sm ${
              isPositive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
            }`}>
              {change}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}