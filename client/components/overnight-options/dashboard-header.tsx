import { Button } from '@/components/ui/button';
import { RefreshCw } from 'lucide-react';

interface DashboardHeaderProps {
  isLive: boolean;
  activeTimeRange: string;
  activeTicker?: string;
  onRefresh?: () => void;
  onTickerChange?: (ticker: string) => void;
}

export function DashboardHeader({ isLive, activeTimeRange, activeTicker = 'SPY', onRefresh, onTickerChange }: DashboardHeaderProps) {
  const tickers = ['SPY', 'XSP', 'SPX'];
  return (
    <div className="mb-6">
      {/* Top row with title and status/refresh */}
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold text-foreground">Overnight Options Assistant</h1>
        
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Status:</span>
            <span className="text-foreground">Active: {activeTimeRange}</span>
            {isLive && (
              <>
                <div className="live-indicator ml-2"></div>
                <span className="text-sm text-green-500">Live</span>
              </>
            )}
          </div>
          
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            className="border-border text-muted-foreground hover:text-foreground hover:border-border/80"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Ticker tabs */}
      <div className="flex gap-1 bg-gray-800 rounded-lg p-1 w-fit">
        {tickers.map((ticker) => (
          <button
            key={ticker}
            onClick={() => onTickerChange?.(ticker)}
            className={`px-3 py-2 rounded-md text-sm font-medium transition-all ${
              activeTicker === ticker
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-gray-300 hover:text-white hover:bg-gray-700'
            }`}
          >
            {ticker}
          </button>
        ))}
      </div>
    </div>
  );
}