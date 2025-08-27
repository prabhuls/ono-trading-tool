export interface SpreadRecommendation {
  strategy: string;
  spreadCost: number;
  profitTarget: number;
  expiration: string;
  maxValue: number;
  maxReward: number;
  maxRisk: number;
  roiPotential: number;
  targetRoi: number;
  buyStrike: number;
  sellStrike: number;
}

export interface MarketStatus {
  isOpen: boolean;
  nextExpiration: string;
  volume: string;
  ivRank: number;
}

export interface OptionChainData {
  strike: number;
  bid: number;
  ask: number;
  volume: number;
  openInterest: number;
  impliedVolatility: number;
  isHighlighted?: 'buy' | 'sell' | null;
}

export interface ChartTimeInterval {
  label: string;
  value: string;
  isActive: boolean;
}

export interface DashboardData {
  currentSpyPrice: number;
  lastUpdated: string;
  spreadRecommendation: SpreadRecommendation;
  marketStatus: MarketStatus;
  optionChain: OptionChainData[];
  chartIntervals: ChartTimeInterval[];
  isLive: boolean;
  activeTimeRange: string;
}

export interface StatusBarInfo {
  demoMode: string;
  scannerActive: string;
}