'use client';

import { useState, useEffect } from 'react';
import { DashboardHeader } from './dashboard-header';
import { TopRankedTrade } from './top-ranked-trade';
import { MarketStatus } from './market-status';
import { SpyIntradayChart } from './spy-intraday-chart';
import { OptionChainOptimizer } from './option-chain-optimizer';
import { StatusBars } from './status-bars';
import { mockDashboardData, mockStatusBars } from '@/lib/mock-data/overnight-options';
import { api } from '@/lib/api';
import type { 
  ApiMarketStatusResponse, 
  OptionChainWithAlgorithm, 
  OptionChainData,
  AlgorithmResult 
} from '@/types/overnight-options';

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
      
      const response = await api.optionChain.getWithAlgorithm(activeTicker);
      
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
          impliedVolatility: item.implied_volatility || item.impliedVolatility || 0,
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
  }, [activeTicker]); // Refetch when ticker changes

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

  const handleAdjustMaxCost = (): void => {
    try {
      // In a real app, this would open a dialog to adjust max cost
      // For now, just prevent any errors
    } catch (error) {
      // Silent fail for now (no monitoring setup)
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
      // In a real app, this would change the data source
      setActiveTicker(ticker);
    } catch (error) {
      // Silent fail for now (no monitoring setup)
    }
  };

  // Don't block render - show layout immediately
  // Individual components will handle their own loading states

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
              onAdjustMaxCost={handleAdjustMaxCost}
              onTickerChange={handleTickerChange}
            />
            <MarketStatus />
          </div>

          {/* Main Content */}
          <div className="lg:col-span-8 space-y-6">
            <SpyIntradayChart
              buyStrike={algorithmResult?.buy_strike || dashboardData.spreadRecommendation.buyStrike}
              sellStrike={algorithmResult?.sell_strike || dashboardData.spreadRecommendation.sellStrike}
              currentPrice={currentSpyPrice}
              chartIntervals={dashboardData.chartIntervals}
              lastUpdated={dashboardData.lastUpdated}
              onIntervalChange={handleIntervalChange}
            />
            <OptionChainOptimizer
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