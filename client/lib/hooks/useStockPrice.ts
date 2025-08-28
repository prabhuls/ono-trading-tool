import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import { captureException, addBreadcrumb, handleApiError } from '@/lib/monitoring';
import type {
  StockPriceData,
  StockPriceResponse,
  StockPriceDisplayData,
  UseStockPriceResult,
  SupportedTicker,
} from '@/types/stock-price';

// Utility function to format price data for display
function formatPriceData(data: StockPriceData): StockPriceDisplayData {
  const isPositive = data.change >= 0;
  
  return {
    ...data,
    isPositive,
    formattedPrice: `$${data.price.toFixed(2)}`,
    formattedChange: `${isPositive ? '+' : ''}${data.change.toFixed(2)}`,
    formattedChangePercent: `${isPositive ? '+' : ''}${data.change_percent.toFixed(2)}%`,
  };
}

// Default fallback data
const createDefaultPriceData = (ticker: SupportedTicker): StockPriceDisplayData => ({
  ticker,
  price: 0,
  change: 0,
  change_percent: 0,
  timestamp: new Date().toISOString(),
  isPositive: true,
  formattedPrice: '$0.00',
  formattedChange: '+0.00',
  formattedChangePercent: '+0.00%',
});

/**
 * Custom hook for managing single stock price data
 * Provides manual refresh functionality with no automatic polling
 */
export function useStockPrice(ticker: SupportedTicker): UseStockPriceResult {
  const [priceData, setPriceData] = useState<StockPriceDisplayData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchStockPrice = useCallback(async () => {
    try {
      setError(null);
      
      // Add breadcrumb for debugging
      addBreadcrumb({
        message: `Fetching stock price for ${ticker}`,
        category: 'api.request',
        level: 'info',
        data: { ticker },
      });

      // Use dedicated SPY endpoint for SPY ticker, otherwise use generic endpoint
      const response = ticker === 'SPY' 
        ? await api.market.spyPrice()
        : await api.market.currentPrice(ticker);
      
      if (response.success && response.data) {
        const apiData = response.data as StockPriceData;
        const formattedData = formatPriceData(apiData);
        setPriceData(formattedData);
        setLastUpdated(new Date());
        
        // Add success breadcrumb
        addBreadcrumb({
          message: `Successfully fetched ${ticker} price: $${apiData.price}`,
          category: 'api.response',
          level: 'info',
          data: { 
            ticker,
            price: apiData.price,
            change: apiData.change 
          },
        });
      } else {
        throw new Error('Invalid API response format');
      }
    } catch (err: any) {
      const errorData = handleApiError(err);
      const errorMessage = errorData.message || `Failed to fetch ${ticker} price`;
      
      setError(errorMessage);
      
      // Capture exception with context
      captureException(err, {
        tags: {
          component: 'useStockPrice',
          ticker,
          action: 'fetchStockPrice',
        },
        extra: {
          ticker,
          errorMessage,
          statusCode: errorData.statusCode,
        },
      });
      
      console.error(`Failed to fetch ${ticker} price:`, err);
      
      // Set fallback data to prevent UI breaking
      if (!priceData) {
        setPriceData(createDefaultPriceData(ticker));
      }
    } finally {
      setLoading(false);
    }
  }, [ticker]);

  const refresh = useCallback(async () => {
    setLoading(true);
    await fetchStockPrice();
  }, [fetchStockPrice]);

  useEffect(() => {
    // Initial fetch when ticker changes
    fetchStockPrice();
  }, [fetchStockPrice]);

  return {
    priceData,
    loading,
    error,
    refresh,
    lastUpdated,
  };
}

/**
 * Custom hook for managing multiple stock prices
 * Useful for displaying multiple tickers simultaneously
 */
export function useMultipleStockPrices(tickers: SupportedTicker[]) {
  const [pricesData, setPricesData] = useState<Record<SupportedTicker, StockPriceDisplayData | null>>({
    SPY: null,
    XSP: null,
    SPX: null,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchMultiplePrices = useCallback(async () => {
    try {
      setError(null);
      
      // Add breadcrumb for debugging
      addBreadcrumb({
        message: `Fetching prices for multiple tickers`,
        category: 'api.request',
        level: 'info',
        data: { tickers },
      });

      const response = await api.market.currentPrices(tickers);
      
      if (response.success && response.data) {
        const apiData = response.data as StockPriceData[];
        const newPricesData = { ...pricesData };
        
        // Update each ticker's data
        apiData.forEach((priceData) => {
          if (tickers.includes(priceData.ticker as SupportedTicker)) {
            newPricesData[priceData.ticker as SupportedTicker] = formatPriceData(priceData);
          }
        });
        
        setPricesData(newPricesData);
        setLastUpdated(new Date());
        
        // Add success breadcrumb
        addBreadcrumb({
          message: `Successfully fetched prices for ${apiData.length} tickers`,
          category: 'api.response',
          level: 'info',
          data: { 
            tickerCount: apiData.length,
            tickers: apiData.map(d => d.ticker),
          },
        });
      } else {
        throw new Error('Invalid API response format');
      }
    } catch (err: any) {
      const errorData = handleApiError(err);
      const errorMessage = errorData.message || 'Failed to fetch stock prices';
      
      setError(errorMessage);
      
      // Capture exception with context
      captureException(err, {
        tags: {
          component: 'useMultipleStockPrices',
          action: 'fetchMultiplePrices',
        },
        extra: {
          tickers,
          errorMessage,
          statusCode: errorData.statusCode,
        },
      });
      
      console.error('Failed to fetch multiple stock prices:', err);
      
      // Set fallback data for any missing tickers
      const newPricesData = { ...pricesData };
      tickers.forEach((ticker) => {
        if (!newPricesData[ticker]) {
          newPricesData[ticker] = createDefaultPriceData(ticker);
        }
      });
      setPricesData(newPricesData);
    } finally {
      setLoading(false);
    }
  }, [tickers]);

  const refresh = useCallback(async () => {
    setLoading(true);
    await fetchMultiplePrices();
  }, [fetchMultiplePrices]);

  useEffect(() => {
    // Initial fetch when tickers change
    fetchMultiplePrices();
  }, [fetchMultiplePrices]);

  return {
    pricesData,
    loading,
    error,
    refresh,
    lastUpdated,
  };
}