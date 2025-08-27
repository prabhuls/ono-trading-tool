'use client';

import { useState } from 'react';
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

  const handleRefresh = () => {
    // In a real app, this would fetch fresh data
    console.log('Refreshing dashboard data...');
  };

  const handleScanForNewSpreads = () => {
    // In a real app, this would trigger spread scanning
    console.log('Scanning for new spreads...');
  };

  const handleAdjustMaxCost = () => {
    // In a real app, this would open a dialog to adjust max cost
    console.log('Adjusting max cost...');
  };

  const handleIntervalChange = (interval: string) => {
    // In a real app, this would change the chart data
    console.log('Changing interval to:', interval);
    setDashboardData(prev => ({
      ...prev,
      chartIntervals: prev.chartIntervals.map(int => ({
        ...int,
        isActive: int.value === interval
      }))
    }));
  };

  const handleTickerChange = (ticker: string) => {
    // In a real app, this would change the data source
    console.log('Changing ticker to:', ticker);
    setActiveTicker(ticker);
  };

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