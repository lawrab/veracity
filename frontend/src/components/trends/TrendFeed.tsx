'use client';

import React, { useState, useEffect } from 'react';
import { Trend } from '@/types/trend';
import { apiService } from '@/services/api';
import TrendCard from './TrendCard';
import { ArrowPathIcon } from '@heroicons/react/24/outline';

export default function TrendFeed() {
  const [trends, setTrends] = useState<Trend[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    fetchTrends();
    
    if (autoRefresh) {
      const interval = setInterval(fetchTrends, 300000); // Refresh every 5 minutes as fallback only
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const fetchTrends = async () => {
    try {
      const response = await apiService.get('/trends/live');
      // Transform API response to match Trend type
      const transformedTrends = (response || []).slice(0, 10).map((trend: any) => ({
        ...trend,
        name: trend.keywords?.[0] || trend.hashtags?.[0] || 'Unknown Trend',
        description: `${trend.mention_count || 0} mentions across ${trend.platforms?.join(', ') || 'platforms'}`,
        confidence_score: Math.round((trend.sentiment_score || 0) * 50 + 50), // Convert -1 to 1 to 0 to 100
        story_count: 1, // Since each trend has a story_id
        peak_velocity: trend.velocity || 0,
        platform_distribution: trend.platforms?.reduce((acc: any, p: string) => {
          acc[p] = Math.round(100 / (trend.platforms?.length || 1));
          return acc;
        }, {}) || {}
      }));
      setTrends(transformedTrends);
      setError(null);
    } catch (err) {
      setError('Failed to fetch trends');
      console.error('Error fetching trends:', err);
      setTrends([]); // Reset to empty array on error
    } finally {
      setLoading(false);
    }
  };

  if (loading && trends.length === 0) {
    return (
      <div className="flex justify-center items-center min-h-[200px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (error && trends.length === 0) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
        <p className="text-red-600 dark:text-red-400 text-sm">{error}</p>
        <button 
          onClick={fetchTrends}
          className="mt-2 text-xs text-red-600 dark:text-red-400 underline hover:no-underline"
        >
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex items-center justify-between">
        <button
          onClick={fetchTrends}
          className="flex items-center text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
        >
          <ArrowPathIcon className="h-4 w-4 mr-1" />
          Refresh
        </button>
        <label className="flex items-center text-sm">
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
            className="mr-2 rounded border-gray-300 dark:border-gray-600"
          />
          <span className="text-gray-600 dark:text-gray-400">Auto-refresh</span>
        </label>
      </div>

      {/* Trend List */}
      <div className="space-y-3 max-h-[600px] overflow-y-auto">
        {trends.map((trend) => (
          <TrendCard key={trend.id} trend={trend} compact />
        ))}
      </div>

      {trends.length === 0 && (
        <div className="text-center py-8">
          <p className="text-gray-500 dark:text-gray-400 text-sm">
            No active trends at the moment
          </p>
        </div>
      )}
    </div>
  );
}