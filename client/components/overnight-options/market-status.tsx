import { Card } from '@/components/ui/card';
import { MarketStatus as MarketStatusType } from '@/types/overnight-options';
import { formatPercentage } from '@/lib/mock-data/overnight-options';

interface MarketStatusProps {
  marketStatus: MarketStatusType;
}

export function MarketStatus({ marketStatus }: MarketStatusProps) {
  return (
    <Card className="p-4">
      <h3 className="text-lg font-semibold text-foreground mb-4">Market Status</h3>
      
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

        <div className="flex justify-between">
          <span className="text-muted-foreground">Volume:</span>
          <span className="text-foreground font-medium">
            {marketStatus.volume}
          </span>
        </div>

        <div className="flex justify-between">
          <span className="text-muted-foreground">IV Rank:</span>
          <span className="text-blue-400 font-medium">
            {formatPercentage(marketStatus.ivRank)}
          </span>
        </div>
      </div>
    </Card>
  );
}