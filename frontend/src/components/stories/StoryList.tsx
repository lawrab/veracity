'use client';

import React, { useState, useEffect } from 'react';
import StoryCard from './StoryCard';
import { Story } from '@/types/story';
import { apiService } from '@/services/api';
import { MagnifyingGlassIcon, FunnelIcon } from '@heroicons/react/24/outline';

export default function StoryList() {
  const [stories, setStories] = useState<Story[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'trust_score' | 'velocity' | 'recent'>('recent');

  useEffect(() => {
    fetchStories();
  }, []);

  const fetchStories = async () => {
    try {
      setLoading(true);
      const response = await apiService.get('/stories/trending');
      setStories(response || []);
      setError(null);
    } catch (err) {
      setError('Failed to fetch stories');
      console.error('Error fetching stories:', err);
      setStories([]); // Reset to empty array on error
    } finally {
      setLoading(false);
    }
  };

  const filteredStories = (stories || [])
    .filter(story => {
      const matchesSearch = story.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          story.description?.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesCategory = selectedCategory === 'all' || story.category === selectedCategory;
      return matchesSearch && matchesCategory;
    })
    .sort((a, b) => {
      switch (sortBy) {
        case 'trust_score':
          return b.trust_score - a.trust_score;
        case 'velocity':
          return b.velocity - a.velocity;
        case 'recent':
        default:
          return new Date(b.first_seen_at).getTime() - new Date(a.first_seen_at).getTime();
      }
    });

  const categories = Array.from(new Set(stories.map(s => s.category).filter(Boolean)));

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
        <p className="text-red-600 dark:text-red-400">{error}</p>
        <button 
          onClick={fetchStories}
          className="mt-2 text-sm text-red-600 dark:text-red-400 underline hover:no-underline"
        >
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Search and Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="flex-1">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search stories..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-700 dark:text-white"
              />
            </div>
          </div>

          {/* Category Filter */}
          <div className="flex items-center gap-2">
            <FunnelIcon className="h-5 w-5 text-gray-400" />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-700 dark:text-white"
            >
              <option value="all">All Categories</option>
              {categories.map(cat => cat && (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>

          {/* Sort */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-700 dark:text-white"
          >
            <option value="recent">Most Recent</option>
            <option value="trust_score">Highest Trust</option>
            <option value="velocity">Trending</option>
          </select>
        </div>
      </div>

      {/* Story Cards */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {filteredStories.length > 0 ? (
          filteredStories.map(story => (
            <StoryCard key={story.id} story={story} />
          ))
        ) : (
          <div className="col-span-full text-center py-12">
            <p className="text-gray-500 dark:text-gray-400">No stories found matching your criteria.</p>
          </div>
        )}
      </div>

      {/* Story Count */}
      <div className="text-sm text-gray-600 dark:text-gray-400 text-center">
        Showing {filteredStories.length} of {stories.length} stories
      </div>
    </div>
  );
}