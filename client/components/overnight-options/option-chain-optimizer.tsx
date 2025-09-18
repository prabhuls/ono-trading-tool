import { Card } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { OptionChainData, AlgorithmResult } from '@/types/overnight-options';
import { formatCurrency, formatPercentage, formatVolume } from '@/lib/utils/formatters';

interface OptionChainOptimizerProps {
  ticker: string; // The ticker symbol (SPY, SPX, etc.)
  optionChain: OptionChainData[];
  expiration: string | null;
  isLoading?: boolean;
  error?: string | null;
  algorithmResult?: AlgorithmResult | null;
}

export function OptionChainOptimizer({ 
  ticker,
  optionChain, 
  expiration, 
  isLoading = false, 
  error = null, 
  algorithmResult = null 
}: OptionChainOptimizerProps) {
  if (error) {
    return (
      <Card className="p-4" style={{ borderColor: '#616266' }}>
        <h3 className="text-lg font-semibold text-foreground mb-4">
{ticker} Option Chain Optimizer ({expiration})
        </h3>
        <Alert variant="destructive">
          <AlertDescription>
            {error}
          </AlertDescription>
        </Alert>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card className="p-4" style={{ borderColor: '#616266' }}>
        <h3 className="text-lg font-semibold text-foreground mb-4">
{ticker} Option Chain Optimizer ({expiration})
        </h3>
        {ticker === 'SPX' && (
          <div className="mb-4 p-3 bg-blue-900/20 border border-blue-700/30 rounded-lg">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
              <span className="text-sm text-blue-400">
                Loading {ticker} option data and calculating implied volatility... This may take a moment.
              </span>
            </div>
          </div>
        )}
        <div className="space-y-2">
          {/* Table header */}
          <div className="grid grid-cols-6 gap-4 pb-2 border-b border-border">
            <div className="text-sm text-muted-foreground">Strike</div>
            <div className="text-sm text-muted-foreground text-right">Bid</div>
            <div className="text-sm text-muted-foreground text-right">Ask</div>
            <div className="text-sm text-muted-foreground text-right">Volume</div>
            <div className="text-sm text-muted-foreground text-right">OI</div>
            <div className="text-sm text-muted-foreground text-right">IV</div>
          </div>
          {/* Skeleton rows */}
          {[...Array(10)].map((_, i) => (
            <div key={i} className="grid grid-cols-6 gap-4 py-2">
              <div className="h-5 bg-muted/20 rounded animate-pulse" />
              <div className="h-5 bg-muted/20 rounded animate-pulse" />
              <div className="h-5 bg-muted/20 rounded animate-pulse" />
              <div className="h-5 bg-muted/20 rounded animate-pulse" />
              <div className="h-5 bg-muted/20 rounded animate-pulse" />
              <div className="h-5 bg-muted/20 rounded animate-pulse" />
            </div>
          ))}
        </div>
      </Card>
    );
  }

  const buyStrike = algorithmResult?.buy_strike;
  const sellStrike = algorithmResult?.sell_strike;

  return (
    <Card className="p-4" style={{ borderColor: '#616266' }}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-foreground">
{ticker} Option Chain Optimizer ({expiration})
        </h3>
        
        {algorithmResult && (
          <div className="text-sm text-muted-foreground">
            {algorithmResult.qualified_spreads_count} qualified spreads found
          </div>
        )}
      </div>

      {/* Algorithm Results Summary */}
      {algorithmResult && algorithmResult.buy_strike && algorithmResult.sell_strike && (
        <div className="mb-4 p-3 bg-muted/30 rounded-lg">
          <div className="text-sm font-medium text-foreground mb-2">Algorithm Selection:</div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div>
              <span className="text-muted-foreground">Spread Cost:</span>
              <div className="font-medium text-foreground">
                {algorithmResult.spread_cost ? formatCurrency(algorithmResult.spread_cost) : 'N/A'}
              </div>
            </div>
            <div>
              <span className="text-muted-foreground">Max Reward:</span>
              <div className="font-medium text-green-400">
                {algorithmResult.max_reward ? formatCurrency(algorithmResult.max_reward) : 'N/A'}
              </div>
            </div>
            <div>
              <span className="text-muted-foreground">ROI Potential:</span>
              <div className="font-medium text-blue-400">
                {algorithmResult.roi_potential ? `${algorithmResult.roi_potential.toFixed(1)}%` : 'N/A'}
              </div>
            </div>
            <div>
              <span className="text-muted-foreground">Profit Target:</span>
              <div className="font-medium text-foreground">
                {algorithmResult.profit_target ? formatCurrency(algorithmResult.profit_target) : 'N/A'}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 text-muted-foreground font-medium">Strike</th>
              <th className="text-right py-2 text-muted-foreground font-medium">Bid</th>
              <th className="text-right py-2 text-muted-foreground font-medium">Ask</th>
              <th className="text-right py-2 text-muted-foreground font-medium">Volume</th>
              <th className="text-right py-2 text-muted-foreground font-medium">OI</th>
              <th className="text-right py-2 text-muted-foreground font-medium">IV</th>
            </tr>
          </thead>
          <tbody>
            {optionChain.map((option, index) => (
              <tr
                key={option.contract_ticker || `${option.strike}_${index}`}
                className={`
                  ${option.isHighlighted === 'buy' ? 'option-chain-row-buy' : ''}
                  ${option.isHighlighted === 'sell' ? 'option-chain-row-sell' : ''}
                  hover:bg-muted/50 transition-colors
                `}
              >
                <td className="py-2 font-medium text-foreground">
                  <div className="flex items-center gap-2">
                    {option.strike}
                    {option.isHighlighted === 'buy' && (
                      <span className="bg-orange-500 text-white text-xs px-2 py-1 rounded-full font-medium">
                        BUY
                      </span>
                    )}
                    {option.isHighlighted === 'sell' && (
                      <span className="bg-red-500 text-white text-xs px-2 py-1 rounded-full font-medium">
                        SELL
                      </span>
                    )}
                  </div>
                </td>
                <td className="py-2 text-right text-green-400">
                  {formatCurrency(option.bid)}
                </td>
                <td className="py-2 text-right text-red-400">
                  {formatCurrency(option.ask)}
                </td>
                <td className="py-2 text-right text-foreground">
                  {formatVolume(option.volume)}
                </td>
                <td className="py-2 text-right text-foreground">
                  {formatVolume(option.openInterest)}
                </td>
                <td className="py-2 text-right text-blue-400">
                  {formatPercentage(option.impliedVolatility)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Highlighted rows legend */}
      <div className="flex gap-4 mt-4 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-orange-500 opacity-20 border-l-2 border-orange-500"></div>
          <span className="text-muted-foreground">
            BUY {buyStrike || '580'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-red-500 opacity-20 border-l-2 border-red-500"></div>
          <span className="text-muted-foreground">
            SELL {sellStrike || '581'}
          </span>
        </div>
      </div>
    </Card>
  );
}