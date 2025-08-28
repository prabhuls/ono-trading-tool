// Stock Price Data Types
export interface StockPriceData {
  ticker: string;
  price: number;
  change: number;
  change_percent: number;
  timestamp: string;
}

// API Response Types
export interface StockPriceResponse {
  success: boolean;
  data: StockPriceData;
  message?: string;
  timestamp: string;
}

export interface MultipleStockPricesResponse {
  success: boolean;
  data: StockPriceData[];
  message?: string;
  timestamp: string;
}

// Supported tickers
export type SupportedTicker = 'SPY' | 'XSP' | 'SPX';

// UI-specific types
export interface StockPriceDisplayData extends StockPriceData {
  isPositive: boolean;
  formattedPrice: string;
  formattedChange: string;
  formattedChangePercent: string;
}

// Hook return types
export interface UseStockPriceResult {
  priceData: StockPriceDisplayData | null;
  loading: boolean;
  refreshing: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  lastUpdated: Date | null;
}

export interface UseMultipleStockPricesResult {
  pricesData: Record<SupportedTicker, StockPriceDisplayData | null>;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  lastUpdated: Date | null;
}

// Component prop types
export interface CurrentPriceProps {
  defaultTicker?: SupportedTicker;
  showTickerSelector?: boolean;
  showRefreshButton?: boolean;
  onTickerChange?: (ticker: SupportedTicker) => void;
  className?: string;
}

export interface TickerSelectorProps {
  selectedTicker: SupportedTicker;
  onTickerChange: (ticker: SupportedTicker) => void;
  disabled?: boolean;
  className?: string;
}

export interface PriceDisplayProps {
  priceData: StockPriceDisplayData;
  showChange?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}