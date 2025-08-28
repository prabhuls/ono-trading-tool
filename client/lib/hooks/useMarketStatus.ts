import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import { ApiMarketSidebarStatusResponse, MarketStatus } from '@/types/overnight-options';

interface UseMarketStatusResult {
  marketStatus: MarketStatus;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

// Transform API response to component-expected format
function transformMarketStatus(apiResponse: ApiMarketSidebarStatusResponse): MarketStatus {
  return {
    isOpen: apiResponse.isOpen ?? false,
    nextExpiration: apiResponse.next_expiration ?? '',
  };
}

// Default fallback data
const DEFAULT_MARKET_STATUS: MarketStatus = {
  isOpen: false,
  nextExpiration: '',
};

export function useMarketStatus(): UseMarketStatusResult {
  const [marketStatus, setMarketStatus] = useState<MarketStatus>(DEFAULT_MARKET_STATUS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMarketStatus = useCallback(async () => {
    try {
      setError(null);
      const response = await api.market.sidebarStatus();
      
      if (response.success && response.data) {
        const apiData = response.data as ApiMarketSidebarStatusResponse;
        const transformedData = transformMarketStatus(apiData);
        setMarketStatus(transformedData);
      } else {
        throw new Error('Invalid API response format');
      }
    } catch (err: any) {
      const errorMessage = err?.message || err?.standardizedError?.message || 'Failed to fetch market status';
      setError(errorMessage);
      console.error('Failed to fetch market status:', err);
      
      // Keep the previous data or use default on error
      // This ensures the UI doesn't break completely
    } finally {
      setLoading(false);
    }
  }, []);

  const refetch = useCallback(async () => {
    setLoading(true);
    await fetchMarketStatus();
  }, [fetchMarketStatus]);

  useEffect(() => {
    // Initial fetch
    fetchMarketStatus();

    // Set up polling interval (every 30 seconds)
    const interval = setInterval(() => {
      fetchMarketStatus();
    }, 30000);

    return () => clearInterval(interval);
  }, [fetchMarketStatus]);

  return {
    marketStatus,
    loading,
    error,
    refetch,
  };
}