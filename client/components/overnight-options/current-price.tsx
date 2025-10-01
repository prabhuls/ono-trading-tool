'use client';

import { useState } from 'react';
import { RefreshCw, TrendingUp, TrendingDown } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useStockPrice } from '@/lib/hooks/useStockPrice';
import { cn, formatDateTime } from '@/lib/utils';
import type { CurrentPriceProps, SupportedTicker } from '@/types/stock-price';

// Ticker display names and descriptions
const TICKER_INFO: Record<SupportedTicker, { name: string; description: string }> = {
  SPY: { name: 'SPDR S&P 500 ETF', description: 'S&P 500 Index Fund' },
  XSP: { name: 'SPDR S&P 500 Mini-SPX', description: 'Mini S&P 500 Options' },
  SPX: { name: 'S&P 500 Index', description: 'Cash-settled Index Options' },
  QQQ: { name: 'Invesco QQQ Trust', description: 'Nasdaq-100 Index Fund' },
  IWM: { name: 'iShares Russell 2000 ETF', description: 'Small-cap Index Fund' },
  GLD: { name: 'SPDR Gold Shares', description: 'Gold Trust ETF' },
};

export function CurrentPrice({
  defaultTicker = 'SPY',
  showTickerSelector = true,
  showRefreshButton = true,
  onTickerChange,
  className,
}: CurrentPriceProps) {
  const [selectedTicker, setSelectedTicker] = useState<SupportedTicker>(defaultTicker);
  
  const {
    priceData,
    loading,
    error,
    refresh,
    lastUpdated,
  } = useStockPrice(selectedTicker);

  const handleTickerChange = (ticker: string) => {
    const supportedTicker = ticker as SupportedTicker;
    setSelectedTicker(supportedTicker);
    onTickerChange?.(supportedTicker);
  };

  const handleRefresh = async () => {
    await refresh();
  };

  // Loading state
  if (loading && !priceData) {
    return (
      <Card className={cn('p-6', className)}>
        <div className="space-y-4">
          <div className="flex justify-center">
            <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
          <div className="text-center">
            <div className="text-sm text-muted-foreground">
              Loading {selectedTicker} price data...
            </div>
          </div>
        </div>
      </Card>
    );
  }

  // Error state (with fallback UI)
  if (error && !priceData) {
    return (
      <Card className={cn('p-6 border-destructive', className)}>
        <div className="space-y-4">
          <div className="text-center">
            <div className="text-sm text-destructive mb-2">
              Failed to load price data
            </div>
            <div className="text-xs text-muted-foreground mb-4">
              {error}
            </div>
            {showRefreshButton && (
              <Button
                size="sm"
                variant="outline"
                onClick={handleRefresh}
                disabled={loading}
              >
                <RefreshCw className={cn('h-4 w-4 mr-2', loading && 'animate-spin')} />
                Try Again
              </Button>
            )}
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className={cn('p-6', className)}>
      <div className="space-y-4">
        {/* Header with ticker selector */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {showTickerSelector ? (
              <Select
                value={selectedTicker}
                onValueChange={handleTickerChange}
                disabled={loading}
              >
                <SelectTrigger className="w-[120px]">
                  <SelectValue placeholder="Select ticker" />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(TICKER_INFO).map(([ticker, info]) => (
                    <SelectItem key={ticker} value={ticker}>
                      <div className="flex flex-col">
                        <span className="font-medium">{ticker}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <div className="text-lg font-semibold text-foreground">
                {selectedTicker}
              </div>
            )}
            
            {showRefreshButton && (
              <Button
                size="sm"
                variant="ghost"
                onClick={handleRefresh}
                disabled={loading}
                className="h-8 w-8 p-0"
              >
                <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
                <span className="sr-only">Refresh price data</span>
              </Button>
            )}
          </div>
          
          {/* Trend indicator */}
          {priceData && (
            <div className={cn('flex items-center gap-1', priceData.isPositive ? 'text-green-500' : 'text-red-500')}>
              {priceData.isPositive ? (
                <TrendingUp className="h-4 w-4" />
              ) : (
                <TrendingDown className="h-4 w-4" />
              )}
            </div>
          )}
        </div>

        {/* Ticker description */}
        <div className="text-sm text-muted-foreground">
          {TICKER_INFO[selectedTicker].name}
          <div className="text-xs opacity-75">
            {TICKER_INFO[selectedTicker].description}
          </div>
        </div>

        {/* Price display */}
        {priceData && (
          <div className="space-y-3">
            {/* Main price */}
            <div className="text-center">
              <div className="text-3xl font-bold text-foreground">
                {priceData.formattedPrice}
              </div>
            </div>

            {/* Change indicators */}
            <div className="flex justify-center gap-4">
              <div className={cn(
                'flex items-center gap-1 text-sm font-medium',
                priceData.isPositive ? 'text-green-500' : 'text-red-500'
              )}>
                <span>{priceData.formattedChange}</span>
              </div>
              <div className={cn(
                'flex items-center gap-1 text-sm font-medium',
                priceData.isPositive ? 'text-green-500' : 'text-red-500'
              )}>
                <span>{priceData.formattedChangePercent}</span>
              </div>
            </div>

            {/* Last updated */}
            {lastUpdated && (
              <div className="text-xs text-muted-foreground text-center pt-2 border-t border-border">
                Last updated: {formatDateTime(lastUpdated)}
              </div>
            )}
          </div>
        )}

        {/* Error message (if error but we have cached data) */}
        {error && priceData && (
          <div className="text-xs text-amber-500 text-center">
            Warning: Using cached data. {error}
          </div>
        )}
      </div>
    </Card>
  );
}

// Ticker selector component for advanced use cases
interface TickerSelectorProps {
  selectedTicker: SupportedTicker;
  onTickerChange: (ticker: SupportedTicker) => void;
  disabled?: boolean;
  className?: string;
}

export function TickerSelector({
  selectedTicker,
  onTickerChange,
  disabled = false,
  className,
}: TickerSelectorProps) {
  return (
    <div className={cn('flex gap-1 bg-gray-800 rounded-lg p-1 w-fit', className)} role="tablist">
      {(Object.keys(TICKER_INFO) as SupportedTicker[]).map((ticker) => (
        <button
          key={ticker}
          onClick={() => onTickerChange(ticker)}
          disabled={disabled}
          className={cn(
            'px-3 py-2 rounded-md text-sm font-medium transition-all',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            selectedTicker === ticker
              ? 'bg-blue-600 text-white shadow-sm'
              : 'text-gray-300 hover:text-white hover:bg-gray-700'
          )}
          role="tab"
          aria-label={`Select ${ticker} ticker`}
          aria-pressed={selectedTicker === ticker}
          aria-selected={selectedTicker === ticker}
        >
          {ticker}
        </button>
      ))}
    </div>
  );
}

// Compact price display for inline use
interface CompactPriceDisplayProps {
  ticker: SupportedTicker;
  showChange?: boolean;
  className?: string;
}

export function CompactPriceDisplay({
  ticker,
  showChange = true,
  className,
}: CompactPriceDisplayProps) {
  const { priceData, loading, error } = useStockPrice(ticker);

  if (loading && !priceData) {
    return (
      <div className={cn('flex items-center gap-2', className)}>
        <RefreshCw className="h-3 w-3 animate-spin text-muted-foreground" />
        <span className="text-sm text-muted-foreground">Loading {ticker}...</span>
      </div>
    );
  }

  if (error && !priceData) {
    return (
      <div className={cn('flex items-center gap-2 text-destructive', className)}>
        <span className="text-sm">Error loading {ticker}</span>
      </div>
    );
  }

  if (!priceData) return null;

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <span className="text-sm font-medium text-foreground">
        {ticker}: {priceData.formattedPrice}
      </span>
      {showChange && (
        <span className={cn(
          'text-xs font-medium',
          priceData.isPositive ? 'text-green-500' : 'text-red-500'
        )}>
          {priceData.formattedChange} ({priceData.formattedChangePercent})
        </span>
      )}
    </div>
  );
}