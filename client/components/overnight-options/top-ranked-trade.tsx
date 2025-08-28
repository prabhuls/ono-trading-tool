import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { SpreadRecommendation } from '@/types/overnight-options';
import { formatCurrency, formatPercentage } from '@/lib/mock-data/overnight-options';
import { useStockPrice } from '@/lib/hooks/useStockPrice';
import { RefreshCw } from 'lucide-react';
import type { SupportedTicker } from '@/types/stock-price';

interface TopRankedTradeProps {
  currentSpyPrice: number;
  spreadRecommendation: SpreadRecommendation;
  activeTicker?: string;
  onScanForNewSpreads?: () => void;
  onAdjustMaxCost?: () => void;
  onTickerChange?: (ticker: string) => void;
}

export function TopRankedTrade({ 
  currentSpyPrice, 
  spreadRecommendation,
  activeTicker = 'SPY',
  onScanForNewSpreads,
  onAdjustMaxCost,
  onTickerChange 
}: TopRankedTradeProps) {
  const tickers: SupportedTicker[] = ['SPY', 'XSP', 'SPX'];
  
  // Use real price data from our API
  const { 
    priceData, 
    loading: priceLoading, 
    error: priceError,
    refresh: refreshPrice 
  } = useStockPrice(activeTicker as SupportedTicker);
  
  // Use API price if available, fallback to prop
  const displayPrice = priceData?.price || currentSpyPrice;
  const priceChange = priceData?.change || 0;
  const priceChangePercent = priceData?.change_percent || 0;
  const isPositive = priceChange >= 0;
  return (
    <div className="space-y-4">
      {/* Current Price */}
      <div className="text-center">
        <div className="flex items-center justify-center gap-2 mb-2">
          <div className="text-4xl font-bold text-foreground">
            {priceLoading ? (
              <div className="animate-pulse">
                {formatCurrency(currentSpyPrice)}
              </div>
            ) : priceError ? (
              <div className="text-red-400 text-lg">
                Price Unavailable
              </div>
            ) : (
              formatCurrency(displayPrice)
            )}
          </div>
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={refreshPrice}
            className="ml-2 text-muted-foreground hover:text-foreground"
            disabled={priceLoading}
          >
            <RefreshCw className={`h-4 w-4 ${priceLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
        
        {/* Price Change Info */}
        {priceData && !priceError && (
          <div className={`text-sm font-medium mb-1 ${
            isPositive ? 'text-green-400' : 'text-red-400'
          }`}>
            {isPositive ? '+' : ''}{priceChange.toFixed(2)} 
            ({isPositive ? '+' : ''}{priceChangePercent.toFixed(2)}%)
          </div>
        )}
        
        <div className="text-sm text-muted-foreground">
          Current {activeTicker} Price
          {priceError && (
            <div className="text-xs text-red-400 mt-1">
              {activeTicker === 'SPY' ? 'Connection error' : 'Ticker not available'}
            </div>
          )}
        </div>
      </div>

      {/* Ticker Switcher */}
      <div className="flex justify-center">
        <div className="flex gap-1 bg-gray-800 rounded-lg p-1 w-fit" role="tablist">
          {tickers.map((ticker) => (
            <button
              key={ticker}
              onClick={() => onTickerChange?.(ticker)}
              className={`px-3 py-2 rounded-md text-sm font-medium transition-all ${
                activeTicker === ticker
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-gray-300 hover:text-white hover:bg-gray-700'
              }`}
              role="tab"
              aria-label={`Select ${ticker} ticker`}
              aria-pressed={activeTicker === ticker}
              aria-selected={activeTicker === ticker}
            >
              {ticker}
            </button>
          ))}
        </div>
      </div>

      {/* Recommended Spread Card */}
      <Card className="p-4">
        <div className="space-y-3">
          <div className="text-center">
            <div className="text-lg font-semibold text-foreground mb-2">
              Recommended Spread
            </div>
            <div className="text-blue-400 font-medium">
              {spreadRecommendation.strategy}
            </div>
            <div className="text-sm text-muted-foreground mt-1">
              Expires {spreadRecommendation.expiration}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Spread Cost:</span>
              <span className="text-foreground font-medium">
                {formatCurrency(spreadRecommendation.spreadCost)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Profit Target:</span>
              <span className="text-green-400 font-medium">
                {formatCurrency(spreadRecommendation.profitTarget)}
              </span>
            </div>
          </div>

          {/* Metrics Grid */}
          <div className="grid grid-cols-2 gap-3 pt-2 border-t border-border">
            <div className="text-center">
              <div className="text-foreground font-medium">
                {formatCurrency(spreadRecommendation.maxValue)}
              </div>
              <div className="text-xs text-muted-foreground">Max Value</div>
            </div>
            <div className="text-center">
              <div className="text-green-400 font-medium">
                {formatCurrency(spreadRecommendation.maxReward)}
              </div>
              <div className="text-xs text-muted-foreground">Max Reward</div>
            </div>
            <div className="text-center">
              <div className="text-red-400 font-medium">
                {formatCurrency(spreadRecommendation.maxRisk)}
              </div>
              <div className="text-xs text-muted-foreground">Max Risk</div>
            </div>
            <div className="text-center">
              <div className="text-green-400 font-medium">
                {formatPercentage(spreadRecommendation.roiPotential)}
              </div>
              <div className="text-xs text-muted-foreground">ROI Potential</div>
            </div>
          </div>

          <div className="text-center pt-2 border-t border-border">
            <div className="text-lg font-semibold text-blue-400">
              Target ROI: {formatPercentage(spreadRecommendation.targetRoi)}
            </div>
          </div>
        </div>
      </Card>

      {/* Action Buttons */}
      <div className="space-y-2">
        <Button 
          className="w-full bg-blue-600 hover:bg-blue-700 text-white"
          onClick={onScanForNewSpreads}
        >
          Scan for New Spreads
        </Button>
        <Button 
          variant="outline" 
          className="w-full border-border text-muted-foreground hover:text-foreground hover:border-border/80"
          onClick={onAdjustMaxCost}
        >
          Adjust Max Cost ({formatCurrency(spreadRecommendation.spreadCost + 0.01)})
        </Button>
      </div>
    </div>
  );
}