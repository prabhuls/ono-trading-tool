import { Button } from '@/components/ui/button';
import { RefreshCw } from 'lucide-react';

interface DashboardHeaderProps {
  isLive: boolean;
  activeTimeRange: string;
  onRefresh?: () => void;
}

export function DashboardHeader({ isLive, activeTimeRange, onRefresh }: DashboardHeaderProps) {
  return (
    <div className="flex justify-between items-center mb-6">
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
          aria-label="Refresh dashboard data"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>
    </div>
  );
}