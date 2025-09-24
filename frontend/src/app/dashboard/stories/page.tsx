'use client';

import React from 'react';
import StoryList from '@/components/stories/StoryList';

export default function StoriesPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          All Stories
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Browse and analyze all tracked stories with trust scores
        </p>
      </div>

      {/* Story List */}
      <StoryList />
    </div>
  );
}