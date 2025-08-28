import { Button } from '@/components/ui/button';
import { RefreshCw } from 'lucide-react';

interface DashboardHeaderProps {
  isLive: boolean;
  activeTimeRange: string;
  onRefresh?: () => void;
  marketStatusError?: string | null;
}

export function DashboardHeader({ isLive, activeTimeRange, onRefresh, marketStatusError }: DashboardHeaderProps) {
  return (
    <div className="flex justify-between items-center mb-6">
      <h1 className="text-2xl font-bold text-foreground">Overnight Options Assistant</h1>
      
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">Status:</span>
          {marketStatusError ? (
            <span className="text-red-400 text-sm" title={marketStatusError}>
              Status Unavailable
            </span>
          ) : isLive ? (
            <>
              <span className="text-foreground">Active: {activeTimeRange}</span>
              <div className="live-indicator ml-2"></div>
              <span className="text-sm text-green-500">Live</span>
            </>
          ) : (
            <span className="text-muted-foreground">Offline</span>
          )}
        </div>
        
        <Button
          variant="outline"
          size="sm"
          onClick={onRefresh}
          aria-label="Refresh dashboard data"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>
    </div>
  );
}