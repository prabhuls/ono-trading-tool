'use client';

import { Card } from '@/components/ui/card';
import { useMarketStatus } from '@/lib/hooks/useMarketStatus';

export function MarketStatus() {
  const { marketStatus, loading, error } = useMarketStatus();
  if (loading) {
    return (
      <Card className="p-4" style={{ borderColor: '#616266' }}>
        <h3 className="text-lg font-semibold text-foreground mb-4">Market Status</h3>
        <div className="space-y-3">
          <div className="animate-pulse">
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Market Hours:</span>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-gray-500"></div>
                <span className="bg-gray-300 h-4 w-12 rounded"></span>
              </div>
            </div>
            <div className="mt-3 space-y-3">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Next Expiration:</span>
                <div className="bg-gray-300 h-4 w-20 rounded"></div>
              </div>
            </div>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-4" style={{ borderColor: '#616266' }}>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-foreground">Market Status</h3>
        {error && (
          <span className="text-xs text-red-400" title={error}>
            ⚠
          </span>
        )}
      </div>
      
      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <span className="text-muted-foreground">Market Hours:</span>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${
              marketStatus.isOpen ? 'bg-green-500' : 'bg-red-500'
            }`}></div>
            <span className={`font-medium ${
              marketStatus.isOpen ? 'text-green-400' : 'text-red-400'
            }`}>
              {marketStatus.isOpen ? 'Open' : 'Closed'}
            </span>
          </div>
        </div>

        <div className="flex justify-between">
          <span className="text-muted-foreground">Next Expiration:</span>
          <span className="text-foreground font-medium">
            {marketStatus.nextExpiration}
          </span>
        </div>
      </div>
    </Card>
  );
}