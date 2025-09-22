import { create } from 'zustand';
import { 
  IngestionStatus, 
  CollectedDataSummary,
  CollectorStatus 
} from '@/types/ingestion';
import { apiService } from '@/services/api';

interface DashboardState {
  // System health
  apiHealthy: boolean;
  checkingHealth: boolean;
  
  // Ingestion status
  ingestionStatus: IngestionStatus | null;
  loadingStatus: boolean;
  
  // Data summary
  dataSummary: CollectedDataSummary[];
  loadingSummary: boolean;
  
  // Actions
  checkApiHealth: () => Promise<void>;
  fetchIngestionStatus: () => Promise<void>;
  fetchDataSummary: () => Promise<void>;
  triggerIngestion: (platform: 'reddit' | 'twitter' | 'news' | 'test') => Promise<void>;
  startPolling: () => void;
  stopPolling: () => void;
}

let pollingInterval: NodeJS.Timer | null = null;

export const useDashboardStore = create<DashboardState>((set, get) => ({
  // Initial state
  apiHealthy: false,
  checkingHealth: false,
  ingestionStatus: null,
  loadingStatus: false,
  dataSummary: [],
  loadingSummary: false,

  // Actions
  checkApiHealth: async () => {
    set({ checkingHealth: true });
    try {
      const healthy = await apiService.checkHealth();
      set({ apiHealthy: healthy });
    } catch (error) {
      console.error('Health check failed:', error);
      set({ apiHealthy: false });
    } finally {
      set({ checkingHealth: false });
    }
  },

  fetchIngestionStatus: async () => {
    set({ loadingStatus: true });
    try {
      const status = await apiService.getIngestionStatus();
      set({ ingestionStatus: status });
    } catch (error) {
      console.error('Failed to fetch ingestion status:', error);
    } finally {
      set({ loadingStatus: false });
    }
  },

  fetchDataSummary: async () => {
    set({ loadingSummary: true });
    try {
      const summary = await apiService.getDataSummary();
      set({ dataSummary: summary });
    } catch (error) {
      console.error('Failed to fetch data summary:', error);
    } finally {
      set({ loadingSummary: false });
    }
  },

  triggerIngestion: async (platform) => {
    try {
      await apiService.triggerIngestion(platform);
      // Immediately update status to running
      set((state) => ({
        ingestionStatus: state.ingestionStatus
          ? {
              ...state.ingestionStatus,
              collectors: {
                ...state.ingestionStatus.collectors,
                [platform === 'test' ? 'reddit' : platform]: CollectorStatus.RUNNING,
              },
            }
          : null,
      }));
      // Fetch updated status after a delay
      setTimeout(() => get().fetchIngestionStatus(), 2000);
    } catch (error) {
      console.error(`Failed to trigger ${platform} ingestion:`, error);
      // Update status to error
      set((state) => ({
        ingestionStatus: state.ingestionStatus
          ? {
              ...state.ingestionStatus,
              collectors: {
                ...state.ingestionStatus.collectors,
                [platform === 'test' ? 'reddit' : platform]: CollectorStatus.ERROR,
              },
            }
          : null,
      }));
    }
  },

  startPolling: () => {
    // Stop any existing polling
    get().stopPolling();
    
    // Start new polling
    pollingInterval = setInterval(() => {
      get().fetchIngestionStatus();
      get().fetchDataSummary();
    }, 10000); // Poll every 10 seconds instead of 5
  },

  stopPolling: () => {
    if (pollingInterval) {
      clearInterval(pollingInterval);
      pollingInterval = null;
    }
  },
}));