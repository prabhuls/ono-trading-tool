import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlgorithmResult } from '@/types/overnight-options';
import { formatCurrency, formatPercentage, formatROI } from '@/lib/mock-data/overnight-options';
import { useStockPrice } from '@/lib/hooks/useStockPrice';
import { RefreshCw } from 'lucide-react';
import type { SupportedTicker } from '@/types/stock-price';
import { MaxCostDialog } from './max-cost-dialog';

interface TopRankedTradeProps {
  currentSpyPrice: number;
  algorithmResult: AlgorithmResult | null;
  algorithmLoading: boolean;
  algorithmError: string | null;
  expiration?: string;
  activeTicker?: string;
  onScanForNewSpreads?: () => void;
  maxCost: number;
  onMaxCostChange: (newMaxCost: number) => void;
  onTickerChange?: (ticker: string) => void;
}

export function TopRankedTrade({ 
  currentSpyPrice, 
  algorithmResult,
  algorithmLoading,
  algorithmError,
  expiration,
  activeTicker = 'SPY',
  onScanForNewSpreads,
  maxCost,
  onMaxCostChange,
  onTickerChange 
}: TopRankedTradeProps) {
  const [isMaxCostDialogOpen, setIsMaxCostDialogOpen] = useState(false);
  const tickers: SupportedTicker[] = ['SPY', 'SPX'];
  
  // Use real price data from our API
  const { 
    priceData, 
    loading: priceLoading, 
    refreshing: priceRefreshing,
    error: priceError,
    refresh: refreshPrice 
  } = useStockPrice(activeTicker as SupportedTicker);
  
  const handleMaxCostSave = (newMaxCost: number) => {
    onMaxCostChange(newMaxCost);
  };
  
  // Use only real API price data, no hardcoded fallback
  const displayPrice = priceData?.price;
  const priceChange = priceData?.change;
  const priceChangePercent = priceData?.change_percent;
  const isPositive = (priceChange ?? 0) >= 0;
  return (
    <div className="space-y-4">
      {/* Current Price */}
      <div className="text-center">
        <div className="flex items-center justify-center gap-2 mb-2">
          <div className="text-4xl font-bold text-foreground">
            {priceError ? (
              <div className="text-red-400 text-lg">
                Price Unavailable
              </div>
            ) : !displayPrice ? (
              <div className="animate-pulse text-muted-foreground">
                Loading...
              </div>
            ) : (
              formatCurrency(displayPrice)
            )}
          </div>
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={refreshPrice}
            className="ml-2 text-muted-foreground"
            disabled={priceLoading || priceRefreshing}
          >
            <RefreshCw className={`h-4 w-4 ${(priceLoading || priceRefreshing) ? 'animate-spin' : ''}`} />
          </Button>
        </div>
        
        {/* Price Change Info */}
        {priceData && !priceError && priceChange !== undefined && priceChangePercent !== undefined && (
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
      <Card className="p-4" style={{ borderColor: '#616266' }}>
        <div className="space-y-3">
          <div className="text-center">
            <div className="text-lg font-semibold text-foreground mb-2">
              Recommended Spread
            </div>
            
            {algorithmLoading ? (
              <div className="space-y-2">
                <div className="h-6 bg-gray-800 rounded animate-pulse"></div>
                <div className="h-4 bg-gray-800 rounded animate-pulse mx-8"></div>
              </div>
            ) : algorithmError ? (
              <div className="text-red-400 text-sm">
                Error loading spread data
              </div>
            ) : !algorithmResult || !algorithmResult.buy_strike || !algorithmResult.sell_strike ? (
              <div className="text-muted-foreground">
                <div className="text-yellow-400 font-medium mb-1">
                  No qualifying spreads found
                </div>
                <div className="text-sm">
                  No spreads found within cost threshold
                </div>
              </div>
            ) : (
              <>
                <div className="text-blue-400 font-medium">
                  BUY {algorithmResult.buy_strike} / SELL {algorithmResult.sell_strike} CALL
                </div>
                {expiration && (
                  <div className="text-sm text-muted-foreground mt-1">
                    Expires {expiration}
                  </div>
                )}
              </>
            )}
          </div>

          {algorithmLoading ? (
            <div className="space-y-2">
              <div className="flex justify-between">
                <div className="h-4 bg-gray-800 rounded animate-pulse w-20"></div>
                <div className="h-4 bg-gray-800 rounded animate-pulse w-16"></div>
              </div>
              <div className="flex justify-between">
                <div className="h-4 bg-gray-800 rounded animate-pulse w-24"></div>
                <div className="h-4 bg-gray-800 rounded animate-pulse w-16"></div>
              </div>
            </div>
          ) : algorithmResult && algorithmResult.buy_strike && algorithmResult.sell_strike ? (
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Spread Cost:</span>
                <span className="text-foreground font-medium">
                  {algorithmResult.spread_cost ? formatCurrency(algorithmResult.spread_cost) : 'N/A'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Profit Target:</span>
                <span className="text-green-400 font-medium">
                  {algorithmResult.profit_target ? formatCurrency(algorithmResult.profit_target) : 'N/A'}
                </span>
              </div>
            </div>
          ) : null}

          {/* Metrics Grid */}
          {algorithmLoading ? (
            <div className="grid grid-cols-2 gap-3 pt-2 border-t border-border">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="text-center">
                  <div className="h-5 bg-gray-800 rounded animate-pulse mb-1"></div>
                  <div className="h-3 bg-gray-800 rounded animate-pulse mx-2"></div>
                </div>
              ))}
            </div>
          ) : algorithmResult && algorithmResult.buy_strike && algorithmResult.sell_strike ? (
            <div className="grid grid-cols-2 gap-3 pt-2 border-t border-border">
              <div className="text-center">
                <div className="text-foreground font-medium">
                  {algorithmResult.spread_cost ? formatCurrency(1.0) : 'N/A'}
                </div>
                <div className="text-xs text-muted-foreground">Max Value</div>
              </div>
              <div className="text-center">
                <div className="text-green-400 font-medium">
                  {algorithmResult.max_reward ? formatCurrency(algorithmResult.max_reward) : 'N/A'}
                </div>
                <div className="text-xs text-muted-foreground">Max Reward</div>
              </div>
              <div className="text-center">
                <div className="text-red-400 font-medium">
                  {algorithmResult.max_risk ? formatCurrency(algorithmResult.max_risk) : 'N/A'}
                </div>
                <div className="text-xs text-muted-foreground">Max Risk</div>
              </div>
              <div className="text-center">
                <div className="text-green-400 font-medium">
                  {algorithmResult.roi_potential ? formatROI(algorithmResult.roi_potential) : 'N/A'}
                </div>
                <div className="text-xs text-muted-foreground">ROI Potential</div>
              </div>
            </div>
          ) : null}

          {algorithmResult && algorithmResult.buy_strike && algorithmResult.sell_strike && (
            <div className="text-center pt-2 border-t border-border">
              <div className="text-lg font-semibold text-blue-400">
                Target ROI: {algorithmResult.target_roi ? formatROI(algorithmResult.target_roi) : 
                            algorithmResult.roi_potential ? formatROI(algorithmResult.roi_potential) : 'N/A'}
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* Action Buttons */}
      <div className="space-y-2">
        <Button 
          className="w-full bg-blue-600 hover:bg-blue-700 text-white disabled:bg-gray-600 disabled:cursor-not-allowed"
          onClick={onScanForNewSpreads}
          disabled={algorithmLoading}
        >
          {algorithmLoading ? 'Scanning...' : 'Scan for New Spreads'}
        </Button>
        <Button 
          variant="outline" 
          className="w-full"
          onClick={() => setIsMaxCostDialogOpen(true)}
        >
          Adjust Max Cost ({formatCurrency(maxCost)})
        </Button>
      </div>
      
      <MaxCostDialog
        open={isMaxCostDialogOpen}
        currentMaxCost={maxCost}
        onClose={() => setIsMaxCostDialogOpen(false)}
        onSave={handleMaxCostSave}
      />
    </div>
  );
}