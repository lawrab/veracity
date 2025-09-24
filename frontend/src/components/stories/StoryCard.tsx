'use client';

import React from 'react';
import Link from 'next/link';
import { Story } from '@/types/story';
import { 
  ArrowTrendingUpIcon, 
  GlobeAltIcon,
  ClockIcon 
} from '@heroicons/react/24/outline';

interface StoryCardProps {
  story: Story;
}

export default function StoryCard({ story }: StoryCardProps) {
  const getTrustScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900';
    if (score >= 60) return 'text-yellow-600 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900';
    if (score >= 40) return 'text-orange-600 bg-orange-100 dark:text-orange-400 dark:bg-orange-900';
    return 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900';
  };

  const getTrustScoreLabel = (score: number) => {
    if (score >= 80) return 'High Trust';
    if (score >= 60) return 'Moderate';
    if (score >= 40) return 'Low Trust';
    return 'Unverified';
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    
    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString();
  };

  return (
    <Link href={`/dashboard/stories/${story.id}`}>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm hover:shadow-md transition-shadow border border-gray-200 dark:border-gray-700 p-6 cursor-pointer">
        <div className="flex justify-between items-start mb-3">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white line-clamp-2 flex-1">
            {story.title}
          </h3>
          <div className={`ml-4 px-3 py-1 rounded-full text-sm font-medium ${getTrustScoreColor(story.trust_score)}`}>
            {story.trust_score.toFixed(0)}%
          </div>
        </div>

        {story.description && (
          <p className="text-gray-600 dark:text-gray-400 text-sm mb-4 line-clamp-2">
            {story.description}
          </p>
        )}

        <div className="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
          <div className="flex items-center space-x-4">
            {story.category && (
              <span className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">
                {story.category}
              </span>
            )}
            
            <div className="flex items-center">
              <ArrowTrendingUpIcon className="h-4 w-4 mr-1" />
              <span>{story.velocity.toFixed(1)}x</span>
            </div>

            {story.geographic_spread && (
              <div className="flex items-center">
                <GlobeAltIcon className="h-4 w-4 mr-1" />
                <span>{Object.keys(story.geographic_spread).length} regions</span>
              </div>
            )}
          </div>

          <div className="flex items-center">
            <ClockIcon className="h-4 w-4 mr-1" />
            <span>{formatDate(story.first_seen_at)}</span>
          </div>
        </div>

        <div className="mt-3 flex items-center justify-between">
          <span className={`text-xs font-medium ${getTrustScoreColor(story.trust_score)}`}>
            {getTrustScoreLabel(story.trust_score)}
          </span>
        </div>
      </div>
    </Link>
  );
}