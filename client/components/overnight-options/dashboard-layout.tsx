'use client';

import { useState, useEffect } from 'react';
import { DashboardHeader } from './dashboard-header';
import { TopRankedTrade } from './top-ranked-trade';
import { MarketStatus } from './market-status';
import { SpyIntradayChart } from './spy-intraday-chart';
import { OptionChainOptimizer } from './option-chain-optimizer';
import { StatusBars } from './status-bars';
import { mockDashboardData, mockStatusBars } from '@/lib/mock-data/overnight-options';

export function DashboardLayout() {
  const [dashboardData, setDashboardData] = useState(mockDashboardData);
  const [activeTicker, setActiveTicker] = useState('SPY');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Simulate data loading
    const loadData = async () => {
      try {
        // Simulate loading delay
        await new Promise(resolve => setTimeout(resolve, 500));
        setIsLoading(false);
      } catch (err) {
        setError('Failed to load dashboard data');
        setIsLoading(false);
      }
    };
    loadData();
  }, []);

  const handleRefresh = (): void => {
    try {
      // In a real app, this would fetch fresh data
      // For now, just prevent any errors
    } catch (error) {
      // Silent fail for now (no monitoring setup)
    }
  };

  const handleScanForNewSpreads = (): void => {
    try {
      // In a real app, this would trigger spread scanning
      // For now, just prevent any errors
    } catch (error) {
      // Silent fail for now (no monitoring setup)
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

  if (isLoading) {
    return (
      <div className="min-h-screen dashboard-bg flex items-center justify-center">
        <div className="text-white">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen dashboard-bg flex items-center justify-center">
        <div className="text-red-400">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen dashboard-bg">
      <div className="container mx-auto px-6 py-6">
        {/* Header */}
        <DashboardHeader
          isLive={dashboardData.isLive}
          activeTimeRange={dashboardData.activeTimeRange}
          onRefresh={handleRefresh}
        />

        {/* Main Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-6">
          {/* Left Sidebar */}
          <div className="lg:col-span-4 space-y-6">
            <TopRankedTrade
              currentSpyPrice={dashboardData.currentSpyPrice}
              spreadRecommendation={dashboardData.spreadRecommendation}
              activeTicker={activeTicker}
              onScanForNewSpreads={handleScanForNewSpreads}
              onAdjustMaxCost={handleAdjustMaxCost}
              onTickerChange={handleTickerChange}
            />
            <MarketStatus marketStatus={dashboardData.marketStatus} />
          </div>

          {/* Main Content */}
          <div className="lg:col-span-8 space-y-6">
            <SpyIntradayChart
              buyStrike={dashboardData.spreadRecommendation.buyStrike}
              sellStrike={dashboardData.spreadRecommendation.sellStrike}
              currentPrice={dashboardData.currentSpyPrice}
              chartIntervals={dashboardData.chartIntervals}
              lastUpdated={dashboardData.lastUpdated}
              onIntervalChange={handleIntervalChange}
            />
            <OptionChainOptimizer
              optionChain={dashboardData.optionChain}
              expiration={dashboardData.spreadRecommendation.expiration}
            />
          </div>
        </div>

        {/* Bottom Status Bars */}
        <StatusBars statusBars={mockStatusBars} />
      </div>
    </div>
  );
}