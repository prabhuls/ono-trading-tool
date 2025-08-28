import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ChartTimeInterval } from '@/types/overnight-options';

interface SpyIntradayChartProps {
  buyStrike: number;
  sellStrike: number;
  currentPrice: number;
  chartIntervals: ChartTimeInterval[];
  lastUpdated: string;
  onIntervalChange?: (interval: string) => void;
}

export function SpyIntradayChart({ 
  buyStrike, 
  sellStrike, 
  currentPrice,
  chartIntervals,
  lastUpdated,
  onIntervalChange 
}: SpyIntradayChartProps) {
  return (
    <Card className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-foreground">SPY Intraday Chart</h3>
        <div className="flex gap-2">
          {chartIntervals.map((interval) => (
            <Button
              key={interval.value}
              size="sm"
              variant={interval.isActive ? "default" : "outline"}
              className={interval.isActive 
                ? "bg-blue-600 hover:bg-blue-700 text-white" 
                : ""
              }
              onClick={() => onIntervalChange?.(interval.value)}
            >
              {interval.label}
            </Button>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="flex gap-4 mb-4 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-3 h-0.5 bg-orange-500"></div>
          <span className="text-muted-foreground">Buy Strike ({buyStrike})</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-0.5 bg-red-500"></div>
          <span className="text-muted-foreground">Sell Strike ({sellStrike})</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-0.5 bg-blue-400"></div>
          <span className="text-muted-foreground">Current Price</span>
        </div>
      </div>

      {/* Chart Placeholder */}
      <div className="relative bg-gray-900 rounded-lg h-64 flex items-center justify-center mb-4">
        {/* Horizontal lines representing strikes */}
        <div className="absolute inset-0 flex flex-col justify-around p-4">
          {/* Buy Strike Line */}
          <div className="relative">
            <div className="h-px bg-orange-500 opacity-50 border-dashed"></div>
            <span className="absolute -left-2 -top-3 text-xs text-orange-500">
              {buyStrike}
            </span>
          </div>
          
          {/* Current Price Line */}
          <div className="relative">
            <div className="h-px bg-blue-400 opacity-75"></div>
            <span className="absolute -left-2 -top-3 text-xs text-blue-400">
              {currentPrice}
            </span>
          </div>
          
          {/* Sell Strike Line */}
          <div className="relative">
            <div className="h-px bg-red-500 opacity-50 border-dashed"></div>
            <span className="absolute -left-2 -top-3 text-xs text-red-500">
              {sellStrike}
            </span>
          </div>
        </div>

        {/* Placeholder content */}
        <div className="text-center text-muted-foreground">
          <div className="text-4xl mb-2">📈</div>
          <div className="text-sm">Chart visualization would appear here</div>
        </div>
      </div>

      {/* Last Updated */}
      <div className="text-right text-sm text-muted-foreground">
        Last updated: {lastUpdated}
      </div>
    </Card>
  );
}