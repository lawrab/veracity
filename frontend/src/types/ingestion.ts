export enum CollectorStatus {
  IDLE = 'idle',
  RUNNING = 'running',
  ERROR = 'error',
}

export interface IngestionStatus {
  collectors: {
    reddit: CollectorStatus;
    twitter: CollectorStatus;
    news: CollectorStatus;
  };
  last_update: string;
}

export interface IngestionRequest {
  sources: string[];
  limit?: number;
}

export interface IngestionResponse {
  message: string;
  job_id: string;
  status: string;
}

export interface CollectedDataSummary {
  platform: string;
  count: number;
  oldest?: string;
  newest?: string;
  topics: string[];
}