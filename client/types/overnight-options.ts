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
  volume?: string;
  ivRank?: number;
}

export interface ApiMarketSidebarStatusResponse {
  isOpen: boolean;
  market_session: string;
  next_expiration: string;
  last_updated: string;
}

export interface OptionChainData {
  strike: number;
  bid: number;
  ask: number;
  volume: number;
  openInterest: number;
  impliedVolatility: number;
  isHighlighted?: 'buy' | 'sell' | null;
  contract_ticker?: string;  // Unique contract ticker for React key
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
  scannerActive: string | null;
}

export interface ApiMarketStatusResponse {
  is_live: boolean;
  active_time_range: string;
  current_time_et: string;
  session_start_utc: string;
  session_end_utc: string;
  next_active_session: string | null;
}

// Option Chain API Response Types (matching backend schemas)
export interface OptionChainMetadata {
  ticker: string;
  expiration_date: string;
  current_price: number;
  total_contracts: number;
  algorithm_applied: boolean;
  max_cost_threshold: number;
  timestamp: string;
}

export interface AlgorithmResult {
  selected_spread?: {
    buy_strike: number;
    sell_strike: number;
    cost: number;
  } | null;
  buy_strike?: number | null;
  sell_strike?: number | null;
  spread_cost?: number | null;
  max_reward?: number | null;
  max_risk?: number | null;
  roi_potential?: number | null;
  profit_target?: number | null;
  target_roi?: number | null;
  qualified_spreads_count: number;
}

export interface OptionChainResponse {
  success: boolean;
  data: OptionChainData[];
  metadata: OptionChainMetadata;
  message: string;
}

export interface OptionChainWithAlgorithm {
  success: boolean;
  data: OptionChainData[];
  metadata: OptionChainMetadata;
  algorithm_result: AlgorithmResult;
  message: string;
}

export interface AlgorithmHealthResponse {
  success: boolean;
  data: {
    is_healthy: boolean;
    version: string;
    last_run: string | null;
    status: string;
  };
  message: string;
}

// Chart Data Types for Intraday API
export interface IntradayDataPoint {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface BenchmarkLines {
  current_price: number;
  buy_strike?: number | null;
  sell_strike?: number | null;
}

export interface IntradayChartMetadata {
  total_candles: number;
  market_hours: string;
  last_updated: string;
}

export interface IntradayChartData {
  ticker: string;
  interval: string;
  current_price: number;
  price_data: IntradayDataPoint[];
  benchmark_lines: BenchmarkLines;
  metadata: IntradayChartMetadata;
}

export interface IntradayChartResponse {
  success: boolean;
  data: IntradayChartData;
  message: string;
}