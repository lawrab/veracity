'use client';

import React from 'react';
import Link from 'next/link';
import { Trend } from '@/types/trend';
import { 
  FireIcon,
  HashtagIcon,
  ChartBarIcon 
} from '@heroicons/react/24/outline';

interface TrendCardProps {
  trend: Trend;
  compact?: boolean;
}

export default function TrendCard({ trend, compact = false }: TrendCardProps) {
  const getConfidenceColor = (score: number) => {
    if (score >= 80) return 'text-green-600 dark:text-green-400';
    if (score >= 60) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-orange-600 dark:text-orange-400';
  };

  const formatVelocity = (velocity: number) => {
    if (velocity >= 10) return `${velocity.toFixed(0)}x 🔥`;
    if (velocity >= 5) return `${velocity.toFixed(1)}x`;
    return `${velocity.toFixed(1)}x`;
  };

  if (compact) {
    return (
      <Link href={`/dashboard/trends/${trend.id}`}>
        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3 hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors cursor-pointer">
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-medium text-gray-900 dark:text-white truncate">
                {trend.name}
              </h4>
              <div className="flex items-center mt-1 space-x-3 text-xs text-gray-500 dark:text-gray-400">
                <span className="flex items-center">
                  <FireIcon className="h-3 w-3 mr-1" />
                  {formatVelocity(trend.peak_velocity)}
                </span>
                <span className="flex items-center">
                  <ChartBarIcon className="h-3 w-3 mr-1" />
                  {trend.story_count} stories
                </span>
              </div>
              {trend.keywords && trend.keywords.length > 0 && (
                <div className="flex items-center mt-1">
                  <HashtagIcon className="h-3 w-3 mr-1 text-gray-400" />
                  <span className="text-xs text-gray-600 dark:text-gray-400 truncate">
                    {trend.keywords.slice(0, 3).join(', ')}
                  </span>
                </div>
              )}
            </div>
            <div className={`ml-2 text-xs font-medium ${getConfidenceColor(trend.confidence_score)}`}>
              {trend.confidence_score}%
            </div>
          </div>
        </div>
      </Link>
    );
  }

  return (
    <Link href={`/dashboard/trends/${trend.id}`}>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm hover:shadow-md transition-shadow border border-gray-200 dark:border-gray-700 p-6 cursor-pointer">
        <div className="flex justify-between items-start mb-3">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {trend.name}
          </h3>
          <div className={`ml-4 text-sm font-medium ${getConfidenceColor(trend.confidence_score)}`}>
            {trend.confidence_score}% confidence
          </div>
        </div>

        {trend.description && (
          <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">
            {trend.description}
          </p>
        )}

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Peak Velocity</p>
            <p className="text-lg font-semibold text-gray-900 dark:text-white">
              {formatVelocity(trend.peak_velocity)}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Story Count</p>
            <p className="text-lg font-semibold text-gray-900 dark:text-white">
              {trend.story_count}
            </p>
          </div>
        </div>

        {trend.platform_distribution && (
          <div className="space-y-2">
            <p className="text-xs text-gray-500 dark:text-gray-400">Platform Distribution</p>
            <div className="flex gap-2">
              {Object.entries(trend.platform_distribution)
                .sort(([, a], [, b]) => b - a)
                .slice(0, 3)
                .map(([platform, percentage]) => (
                  <span 
                    key={platform}
                    className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs"
                  >
                    {platform}: {percentage}%
                  </span>
                ))}
            </div>
          </div>
        )}

        {trend.keywords && trend.keywords.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-1">
            {trend.keywords.slice(0, 5).map((keyword) => (
              <span 
                key={keyword}
                className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200"
              >
                <HashtagIcon className="h-3 w-3 mr-1" />
                {keyword}
              </span>
            ))}
          </div>
        )}
      </div>
    </Link>
  );
}