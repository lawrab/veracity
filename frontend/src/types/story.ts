export interface Story {
  id: string;
  title: string;
  description: string | null;
  category: string | null;
  trust_score: number;
  velocity: number;
  geographic_spread: Record<string, number> | null;
  first_seen_at: string;
  last_updated_at: string;
  created_at: string;
}

export interface StoryDetails extends Story {
  sources: SourceReference[];
  trust_signals: TrustSignal[];
  correlations: StoryCorrelation[];
  evolution: TrustScoreEvolution[];
}

export interface SourceReference {
  id: string;
  name: string;
  credibility_score: number;
  platform: string;
  url: string;
}

export interface TrustSignal {
  signal_type: string;
  value: number;
  confidence: number;
  timestamp: string;
  description: string;
}

export interface StoryCorrelation {
  related_story_id: string;
  related_story_title: string;
  correlation_score: number;
  correlation_type: string;
}

export interface TrustScoreEvolution {
  timestamp: string;
  score: number;
  delta: number;
  reason: string;
}