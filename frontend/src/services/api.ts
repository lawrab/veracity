import { 
  IngestionStatus, 
  IngestionRequest, 
  IngestionResponse, 
  CollectedDataSummary 
} from '@/types/ingestion';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  private async fetchWithTimeout(
    url: string,
    options: RequestInit = {},
    timeout = 10000
  ): Promise<Response> {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
      });
      clearTimeout(id);
      return response;
    } catch (error) {
      clearTimeout(id);
      throw error;
    }
  }

  // Ingestion endpoints
  async getIngestionStatus(): Promise<IngestionStatus> {
    const response = await this.fetchWithTimeout(
      `${this.baseUrl}/api/v1/ingestion/status`
    );
    if (!response.ok) throw new Error('Failed to fetch ingestion status');
    return response.json();
  }

  async triggerIngestion(
    platform: 'reddit' | 'twitter' | 'news' | 'test',
    request?: IngestionRequest
  ): Promise<IngestionResponse> {
    const response = await this.fetchWithTimeout(
      `${this.baseUrl}/api/v1/ingestion/${platform}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: request ? JSON.stringify(request) : undefined,
      }
    );
    if (!response.ok) throw new Error(`Failed to trigger ${platform} ingestion`);
    return response.json();
  }

  async getDataSummary(): Promise<CollectedDataSummary[]> {
    const response = await this.fetchWithTimeout(
      `${this.baseUrl}/api/v1/ingestion/data-summary`
    );
    if (!response.ok) throw new Error('Failed to fetch data summary');
    return response.json();
  }

  // Health check
  async checkHealth(): Promise<boolean> {
    try {
      const response = await this.fetchWithTimeout(
        `${this.baseUrl}/docs`,
        { 
          method: 'HEAD',
          mode: 'cors',
          headers: {
            'Accept': 'application/json',
          }
        },
        5000
      );
      console.log('Health check response:', response.status, response.ok);
      return response.ok;
    } catch (error) {
      console.error('Health check failed:', error);
      return false;
    }
  }

  // Generic REST methods
  async get(endpoint: string): Promise<any> {
    const response = await this.fetchWithTimeout(
      `${this.baseUrl}/api/v1${endpoint}`
    );
    if (!response.ok) throw new Error(`Failed to fetch ${endpoint}`);
    return response.json();
  }

  async post(endpoint: string, data?: any): Promise<any> {
    const response = await this.fetchWithTimeout(
      `${this.baseUrl}/api/v1${endpoint}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: data ? JSON.stringify(data) : undefined,
      }
    );
    if (!response.ok) throw new Error(`Failed to post to ${endpoint}`);
    return response.json();
  }
}

export const apiService = new ApiService();