'use client';

import { useState, useEffect } from 'react';
import { DashboardHeader } from './dashboard-header';
import { TopRankedTrade } from './top-ranked-trade';
import { MarketStatus } from './market-status';
import { SpyIntradayChart } from './spy-intraday-chart';
import { OptionChainOptimizer } from './option-chain-optimizer';
import { StatusBars } from './status-bars';
import { OutsideHoursMessage } from './outside-hours-message';
import { mockDashboardData, mockStatusBars } from '@/lib/mock-data/overnight-options';
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
      return 0.74; // Default for SPY
    case 'SPX':
      return 20.0; // Higher default for SPX options (typically 10-20x more expensive)
    default:
      return 0.74;
  }
};

export function DashboardLayout() {
  const [dashboardData, setDashboardData] = useState(mockDashboardData);
  const [activeTicker, setActiveTicker] = useState('SPY');
  const [isLoading, setIsLoading] = useState(false); // Don't block initial render
  const [error, setError] = useState<string | null>(null);
  const [marketStatusError, setMarketStatusError] = useState<string | null>(null);
  
  // Option chain specific state
  const [optionChainData, setOptionChainData] = useState<OptionChainData[]>([]);
  const [algorithmResult, setAlgorithmResult] = useState<AlgorithmResult | null>(null);
  const [optionChainLoading, setOptionChainLoading] = useState(true); // Show loading for option chain initially
  const [optionChainError, setOptionChainError] = useState<string | null>(null);
  const [currentSpyPrice, setCurrentSpyPrice] = useState<number>(585.27);
  const [maxCost, setMaxCost] = useState<number>(getDefaultMaxCost(activeTicker)); // Default max cost for algorithm
  
  // Active hours state
  const [isActiveHours, setIsActiveHours] = useState<boolean | null>(null); // null = loading
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
      }
    } catch (error) {
      console.error('Failed to fetch market status:', error);
      setMarketStatusError('Unable to fetch real-time market status');
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
      // Don't block initial render - show layout immediately
      setIsLoading(false);
      
      // Load data in the background
      try {
        // Fetch data without blocking
        fetchMarketStatus();
        fetchOptionChainData();
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
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
      
      // Update max cost to ticker-specific default
      const newMaxCost = getDefaultMaxCost(ticker);
      setMaxCost(newMaxCost);
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

        {/* Main Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-6">
          {/* Left Sidebar */}
          <div className="lg:col-span-4 space-y-6">
            <TopRankedTrade
              currentSpyPrice={currentSpyPrice}
              algorithmResult={algorithmResult}
              algorithmLoading={optionChainLoading}
              algorithmError={optionChainError}
              expiration={optionChainData.length > 0 ? dashboardData.spreadRecommendation.expiration : undefined}
              activeTicker={activeTicker}
              onScanForNewSpreads={handleScanForNewSpreads}
              maxCost={maxCost}
              onMaxCostChange={handleMaxCostChange}
              onTickerChange={handleTickerChange}
            />
            <MarketStatus />
          </div>

          {/* Main Content */}
          <div className="lg:col-span-8 space-y-6">
            <SpyIntradayChart
              ticker={activeTicker}
              buyStrike={algorithmResult?.buy_strike || dashboardData.spreadRecommendation.buyStrike}
              sellStrike={algorithmResult?.sell_strike || dashboardData.spreadRecommendation.sellStrike}
              currentPrice={currentSpyPrice}
              chartIntervals={dashboardData.chartIntervals}
              lastUpdated={dashboardData.lastUpdated}
              onIntervalChange={handleIntervalChange}
              hasAlgorithmResult={algorithmResult !== null && algorithmResult.buy_strike !== null && algorithmResult.sell_strike !== null}
            />
            <OptionChainOptimizer
              ticker={activeTicker}
              optionChain={optionChainData.length > 0 ? optionChainData : dashboardData.optionChain}
              expiration={dashboardData.spreadRecommendation.expiration}
              isLoading={optionChainLoading}
              error={optionChainError}
              algorithmResult={algorithmResult}
            />
          </div>
        </div>

        {/* Bottom Status Bars */}
        <StatusBars statusBars={mockStatusBars} />
      </div>
    </div>
  );
}