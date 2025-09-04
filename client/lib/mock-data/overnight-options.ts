import { DashboardData, OptionChainData, StatusBarInfo } from '@/types/overnight-options';

// Mock data matching the screenshot exactly
export const mockDashboardData: DashboardData = {
  currentSpyPrice: 585.27,
  lastUpdated: '12:23:07 AM',
  spreadRecommendation: {
    strategy: 'BUY 580 / SELL 581 CALL',
    spreadCost: 0.73,
    profitTarget: 0.88,
    expiration: '8/28/2025',
    maxValue: 1.00,
    maxReward: 0.27,
    maxRisk: 0.73,
    roiPotential: 36.1,
    targetRoi: 19.7,
    buyStrike: 580,
    sellStrike: 581,
  },
  marketStatus: {
    isOpen: true,
    nextExpiration: '8/28/2025',
    volume: '142.5M',
    ivRank: 23.4,
  },
  optionChain: [
    { strike: 575, bid: 10.85, ask: 11.15, volume: 1203, openInterest: 4521, impliedVolatility: 18.2 },
    { strike: 576, bid: 10.05, ask: 10.35, volume: 892, openInterest: 3214, impliedVolatility: 18.5 },
    { strike: 577, bid: 9.25, ask: 9.55, volume: 1456, openInterest: 2987, impliedVolatility: 18.8 },
    { strike: 578, bid: 8.45, ask: 8.75, volume: 2103, openInterest: 5431, impliedVolatility: 19.1 },
    { strike: 579, bid: 7.65, ask: 7.95, volume: 3254, openInterest: 7234, impliedVolatility: 19.4 },
    { strike: 580, bid: 6.85, ask: 7.15, volume: 5621, openInterest: 12453, impliedVolatility: 19.7, isHighlighted: 'buy' },
    { strike: 581, bid: 6.05, ask: 6.35, volume: 4892, openInterest: 9876, impliedVolatility: 20.0, isHighlighted: 'sell' },
    { strike: 582, bid: 5.25, ask: 5.55, volume: 3456, openInterest: 6789, impliedVolatility: 20.3 },
    { strike: 583, bid: 4.45, ask: 4.75, volume: 2341, openInterest: 4532, impliedVolatility: 20.6 },
    { strike: 584, bid: 3.65, ask: 3.95, volume: 1789, openInterest: 3421, impliedVolatility: 20.9 },
    { strike: 585, bid: 2.85, ask: 3.15, volume: 1234, openInterest: 2567, impliedVolatility: 21.2 },
    { strike: 586, bid: 2.15, ask: 2.45, volume: 987, openInterest: 1876, impliedVolatility: 21.5 },
    { strike: 587, bid: 1.55, ask: 1.85, volume: 654, openInterest: 1234, impliedVolatility: 21.8 },
    { strike: 588, bid: 1.05, ask: 1.35, volume: 432, openInterest: 876, impliedVolatility: 22.1 },
    { strike: 589, bid: 0.65, ask: 0.95, volume: 298, openInterest: 543, impliedVolatility: 22.4 },
    { strike: 590, bid: 0.35, ask: 0.65, volume: 187, openInterest: 321, impliedVolatility: 22.7 },
    { strike: 591, bid: 0.15, ask: 0.45, volume: 123, openInterest: 198, impliedVolatility: 23.0 },
    { strike: 592, bid: 0.05, ask: 0.35, volume: 87, openInterest: 134, impliedVolatility: 23.3 },
    { strike: 593, bid: 0.02, ask: 0.28, volume: 54, openInterest: 87, impliedVolatility: 23.6 },
    { strike: 594, bid: 0.01, ask: 0.23, volume: 32, openInterest: 56, impliedVolatility: 23.9 },
    { strike: 595, bid: 0.01, ask: 0.19, volume: 21, openInterest: 34, impliedVolatility: 24.2 },
  ],
  chartIntervals: [
    { label: '1min', value: '1m', isActive: false },
    { label: '5min', value: '5m', isActive: true },
    { label: '15min', value: '15m', isActive: false },
  ],
  isLive: true,
  activeTimeRange: '3:00 PM - 4:00 PM ET',
};

export const mockStatusBars: StatusBarInfo = {
  scannerActive: "Active 3:00-4:00 PM ET daily for optimal spread scanning.",
};

// Helper function to format currency
export const formatCurrency = (value: number | null | undefined): string => {
  if (value === null || value === undefined) {
    return '$0.00';
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
};

// Helper function to format percentage (for IV - converts decimal to percentage)
export const formatPercentage = (value: number | null | undefined): string => {
  if (value === null || value === undefined) {
    return 'N/A';
  }
  // Convert decimal to percentage (e.g., 0.143 -> 14.3%)
  return `${(value * 100).toFixed(1)}%`;
};

// Helper function to format ROI values (already in percentage form)
export const formatROI = (value: number | null | undefined): string => {
  if (value === null || value === undefined) {
    return '0.0%';
  }
  // ROI values are already percentages (e.g., 85.2 -> 85.2%)
  return `${value.toFixed(1)}%`;
};

// Helper function to format volume
export const formatVolume = (value: number | null | undefined): string => {
  if (value === null || value === undefined) {
    return '0';
  }
  if (value >= 1000) {
    return (value / 1000).toFixed(0) + 'K';
  }
  return value.toString();
};