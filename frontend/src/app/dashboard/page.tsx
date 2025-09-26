'use client';

import React from 'react';
import StoryList from '@/components/stories/StoryList';
import TrendFeed from '@/components/trends/TrendFeed';
import { 
  ChartBarIcon,
  NewspaperIcon,
  ArrowTrendingUpIcon,
  ShieldCheckIcon 
} from '@heroicons/react/24/outline';

export default function DashboardPage() {
  return (
    <div className="space-y-6">
        {/* Page Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Dashboard
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Real-time social media trends and news trustability analysis
          </p>
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Active Stories"
            value="247"
            change="+12%"
            icon={NewspaperIcon}
            color="blue"
          />
          <StatCard
            title="Trending Topics"
            value="42"
            change="+5"
            icon={ArrowTrendingUpIcon}
            color="green"
          />
          <StatCard
            title="Avg Trust Score"
            value="72.3%"
            change="+2.1%"
            icon={ShieldCheckIcon}
            color="indigo"
          />
          <StatCard
            title="Data Points/hr"
            value="1.2M"
            change="+18%"
            icon={ChartBarIcon}
            color="purple"
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
}

function StatCard({ title, value, change, icon: Icon, color }: StatCardProps) {
  const colorClasses = {
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    indigo: 'bg-indigo-500',
    purple: 'bg-purple-500'
  };

  const isPositive = change.startsWith('+');

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