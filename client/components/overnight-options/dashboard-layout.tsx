'use client';

import { useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { DashboardHeader } from './dashboard-header';
import { TopRankedTrade } from './top-ranked-trade';
import { MarketStatus } from './market-status';
import { SpyIntradayChart } from './spy-intraday-chart';
import { OptionChainOptimizer } from './option-chain-optimizer';
import { StatusBars } from './status-bars';
import { OutsideHoursMessage } from './outside-hours-message';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';
// Removed mock data import - using real API data only
import { api } from '@/lib/api';
import type {
  ApiMarketStatusResponse,
  OptionChainWithAlgorithm,
  OptionChainData,
  AlgorithmResult
} from '@/types/overnight-options';

// Helper function to get default max cost based on ticker
const getDefaultMaxCost = (ticker: string): number => {
  switch (ticker) {
    case 'SPY':
      return 0.74; // Default for SPY ($1-wide spreads)
    case 'SPX':
      return 3.75; // Default for SPX ($5-wide spreads, scaled proportionally)
    default:
      return 0.74;
  }
};

// Standard chart intervals for all tickers (SPY and SPX both use true 1m data now)
const standardChartIntervals = [
  { label: '1min', value: '1m', isActive: false },
  { label: '5min', value: '5m', isActive: true },
  { label: '15min', value: '15m', isActive: false },
];

interface DashboardLayoutProps {
  initialTicker?: string;
}

export function DashboardLayout({ initialTicker }: DashboardLayoutProps = {}) {
  const router = useRouter();
  const pathname = usePathname();
  // Initialize with empty states instead of mock data
  const [dashboardData, setDashboardData] = useState({
    currentSpyPrice: null as number | null,
    lastUpdated: null as string | null,
    spreadRecommendation: {
      strategy: null as string | null,
      spreadCost: null as number | null,
      profitTarget: null as number | null,
      expiration: null as string | null,
      maxValue: null as number | null,
      maxReward: null as number | null,
      maxRisk: null as number | null,
      roiPotential: null as number | null,
      targetRoi: null as number | null,
      buyStrike: null as number | null,
      sellStrike: null as number | null,
    },
    marketStatus: {
      isOpen: false,
      nextExpiration: null as string | null,
      volume: null as string | null,
      ivRank: null as number | null,
    },
    optionChain: [] as any[],
    chartIntervals: standardChartIntervals,
    isLive: false,
    activeTimeRange: null as string | null,
  });
  // Initialize ticker from prop or default to SPY
  const validTickers = ['SPY', 'SPX'];
  const defaultTicker = initialTicker && validTickers.includes(initialTicker) ? initialTicker : 'SPY';
  const [activeTicker, setActiveTicker] = useState(defaultTicker);
  const [isLoading, setIsLoading] = useState(true); // Start with loading state
  const [error, setError] = useState<string | null>(null);
  const [marketStatusError, setMarketStatusError] = useState<string | null>(null);
  
  // Option chain specific state
  const [optionChainData, setOptionChainData] = useState<OptionChainData[]>([]);
  const [algorithmResult, setAlgorithmResult] = useState<AlgorithmResult | null>(null);
  const [optionChainLoading, setOptionChainLoading] = useState(true);
  const [optionChainError, setOptionChainError] = useState<string | null>(null);
  const [currentSpyPrice, setCurrentSpyPrice] = useState<number | null>(null);
  const [maxCost, setMaxCost] = useState<number>(getDefaultMaxCost(activeTicker)); // Default max cost for algorithm
  
  // Active hours state
  const [isActiveHours, setIsActiveHours] = useState<boolean | null>(null); // null = loading
  
  // Status bars state
  const [statusBarsData, setStatusBarsData] = useState({
    scannerActive: null as string | null
  });
  const showScansOutsideHours = process.env.NEXT_PUBLIC_SHOW_SCANS_OUTSIDE_ACTIVE_HOURS === 'true';

  // Fetch market status from API
  const fetchMarketStatus = async (): Promise<void> => {
    try {
      setMarketStatusError(null);
      const response = await api.market.status();
      
      if (response.success && response.data) {
        const marketStatus = response.data as ApiMarketStatusResponse;
        
        // Update dashboard data with API response
        setDashboardData(prev => ({
          ...prev,
          isLive: marketStatus.is_live,
          activeTimeRange: marketStatus.active_time_range
        }));
        
        // Update active hours state
        setIsActiveHours(marketStatus.is_live);
        
        // Update status bars with dynamic data
        setStatusBarsData({
          scannerActive: marketStatus.is_live 
            ? `Active ${marketStatus.active_time_range} daily for optimal spread scanning.`
            : `Scanner inactive - next active period: ${marketStatus.active_time_range}.`
        });
      }
    } catch (error) {
      console.error('Failed to fetch market status:', error);
      setMarketStatusError('Unable to fetch real-time market status');
      
      // Set fallback status bar message when API fails
      setStatusBarsData({
        scannerActive: 'Scanner status unavailable - please check connection and try refreshing.'
      });
    }
  };

  // Fetch option chain data with algorithm
  const fetchOptionChainData = async (): Promise<void> => {
    try {
      setOptionChainLoading(true);
      setOptionChainError(null);
      
      const response = await api.optionChain.getWithAlgorithm(activeTicker, {
        max_cost: maxCost
      });
      
      if (response.success && response.data) {
        const optionChainResponse = response.data as any;
        
        // Map snake_case API response to camelCase frontend format
        const optionChainArray = optionChainResponse.data || [];
        const mappedOptionChain: OptionChainData[] = optionChainArray.map((item: any) => ({
          strike: item.strike,
          bid: item.bid,
          ask: item.ask,
          volume: item.volume,
          openInterest: item.open_interest || item.openInterest || 0,
          impliedVolatility: item.implied_volatility ?? item.impliedVolatility ?? null,
          isHighlighted: item.is_highlighted || item.isHighlighted || null
        }));
        
        // Update option chain data
        setOptionChainData(mappedOptionChain);
        setAlgorithmResult(optionChainResponse.algorithm_result || null);
        setCurrentSpyPrice(optionChainResponse.metadata?.current_price || 0);
        
        // Update dashboard data with basic chart info only
        setDashboardData(prev => ({
          ...prev,
          currentSpyPrice: optionChainResponse.metadata?.current_price || prev.currentSpyPrice,
          optionChain: mappedOptionChain,
          spreadRecommendation: {
            ...prev.spreadRecommendation,
            expiration: optionChainResponse.metadata?.expiration_date || prev.spreadRecommendation.expiration
          }
        }));
      }
    } catch (error) {
      console.error('Failed to fetch option chain data:', error);
      setOptionChainError('Unable to fetch option chain data');
    } finally {
      setOptionChainLoading(false);
    }
  };

  useEffect(() => {
    const loadData = async () => {
      try {
        // Start loading
        setIsLoading(true);
        
        // Fetch data in parallel
        await Promise.all([
          fetchMarketStatus(),
          fetchOptionChainData()
        ]);
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
        setError('Failed to load dashboard data');
      } finally {
        // Stop loading once data is fetched (success or failure)
        setIsLoading(false);
      }
    };
    
    loadData();

    // Set up periodic polling for market status during potential active hours
    const interval = setInterval(() => {
      fetchMarketStatus();
    }, 30000); // Poll every 30 seconds

    return () => clearInterval(interval);
  }, [activeTicker, maxCost]); // Refetch when ticker or maxCost changes

  const handleRefresh = async (): Promise<void> => {
    try {
      // Fetch fresh market status and option chain data
      await Promise.all([
        fetchMarketStatus(),
        fetchOptionChainData()
      ]);
    } catch (error) {
      console.error('Failed to refresh data:', error);
    }
  };

  const handleScanForNewSpreads = async (): Promise<void> => {
    try {
      // Refresh option chain data to scan for new spreads
      await fetchOptionChainData();
    } catch (error) {
      console.error('Failed to scan for new spreads:', error);
    }
  };

  const handleMaxCostChange = (newMaxCost: number): void => {
    try {
      setMaxCost(newMaxCost);
    } catch (error) {
      console.error('Failed to update max cost:', error);
    }
  };

  const handleIntervalChange = (interval: string): void => {
    try {
      // In a real app, this would change the chart data
      setDashboardData(prev => ({
        ...prev,
        chartIntervals: prev.chartIntervals.map(int => ({
          ...int,
          isActive: int.value === interval
        }))
      }));
    } catch (error) {
      // Silent fail for now (no monitoring setup)
    }
  };

  const handleTickerChange = (ticker: string): void => {
    try {
      // Update the active ticker
      setActiveTicker(ticker);

      // Immediately clear algorithm result to remove old strikes
      setAlgorithmResult(null);

      // Reset current price to avoid showing old ticker's price with new ticker's name
      setCurrentSpyPrice(0); // Will be updated when new data loads

      // Both SPY and SPX use the same intervals now - no need to update chartIntervals

      // Update max cost to ticker-specific default
      const newMaxCost = getDefaultMaxCost(ticker);
      setMaxCost(newMaxCost);

      // Update the URL to reflect the new ticker
      router.push(`/${ticker}`);
    } catch (error) {
      // Silent fail for now (no monitoring setup)
    }
  };

  // Don't block render - show layout immediately
  // Individual components will handle their own loading states
  
  // Show outside hours message if not in active hours and environment variable is not set
  if (isActiveHours === false && !showScansOutsideHours) {
    return <OutsideHoursMessage />;
  }

  return (
    <div className="min-h-screen dashboard-bg">
      <div className="container mx-auto px-6 py-6">
        {/* Header */}
        <DashboardHeader
          isLive={dashboardData.isLive}
          activeTimeRange={dashboardData.activeTimeRange}
          onRefresh={handleRefresh}
          marketStatusError={marketStatusError}
        />

        {/* Spread Pricing Warning */}
        <Alert className="mb-6 border-yellow-600/50 bg-yellow-950/20">
          <AlertCircle className="h-4 w-4 text-yellow-600" />
          <AlertTitle className="text-yellow-600">Important Note on Spread Pricing</AlertTitle>
          <AlertDescription className="text-yellow-100/90">
            Spread prices on these assets can move rapidly. Always confirm current pricing directly with your broker
            and be sure to place orders using limit orders (not market orders). If the spread cost shown in the scanner
            appears off or not tradeable, refresh the scanner to update the pricing.
          </AlertDescription>
        </Alert>

        {/* Main Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-6">
          {/* Left Sidebar */}
          <div className="lg:col-span-4 space-y-6">
            <TopRankedTrade
              algorithmResult={algorithmResult}
              algorithmLoading={optionChainLoading}
              algorithmError={optionChainError}
              expiration={dashboardData.spreadRecommendation.expiration}
              activeTicker={activeTicker}
              onScanForNewSpreads={handleScanForNewSpreads}
              maxCost={maxCost}
              onMaxCostChange={handleMaxCostChange}
              onTickerChange={handleTickerChange}
              currentPrice={currentSpyPrice}
            />
            <MarketStatus />
          </div>

          {/* Main Content */}
          <div className="lg:col-span-8 space-y-6">
            <SpyIntradayChart
              ticker={activeTicker}
              buyStrike={algorithmResult?.buy_strike || null}
              sellStrike={algorithmResult?.sell_strike || null}
              currentPrice={currentSpyPrice}
              chartIntervals={dashboardData.chartIntervals}
              lastUpdated={dashboardData.lastUpdated}
              onIntervalChange={handleIntervalChange}
              hasAlgorithmResult={algorithmResult !== null && algorithmResult.buy_strike !== null && algorithmResult.sell_strike !== null}
            />
            <OptionChainOptimizer
              ticker={activeTicker}
              optionChain={optionChainData}
              expiration={dashboardData.spreadRecommendation.expiration}
              isLoading={optionChainLoading}
              error={optionChainError}
              algorithmResult={algorithmResult}
            />
          </div>
        </div>

        {/* Bottom Status Bars */}
        <StatusBars statusBars={statusBarsData} />
      </div>
    </div>
  );
}