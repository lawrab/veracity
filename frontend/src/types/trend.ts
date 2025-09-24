export interface Trend {
  id: string;
  name: string;
  description: string | null;
  category: string | null;
  confidence_score: number;
  story_count: number;
  platform_distribution: Record<string, number>;
  peak_velocity: number;
  keywords: string[];
  detected_at: string;
  last_updated_at: string;
  created_at: string;
}

export interface TrendDetails extends Trend {
  stories: TrendStory[];
  evolution: TrendEvolution[];
  sources: TrendSource[];
}

export interface TrendStory {
  id: string;
  title: string;
  trust_score: number;
  velocity: number;
  first_seen_at: string;
}

export interface TrendEvolution {
  timestamp: string;
  story_count: number;
  velocity: number;
  confidence: number;
}

export interface TrendSource {
  platform: string;
  post_count: number;
  engagement_rate: number;
  top_influencers: string[];
}