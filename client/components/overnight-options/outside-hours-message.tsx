import { Card } from '@/components/ui/card';

export function OutsideHoursMessage() {
  return (
    <div className="min-h-screen dashboard-bg flex items-center justify-center px-6">
      <Card className="p-8 text-center max-w-md w-full" style={{ borderColor: '#616266' }}>
        <div className="space-y-4">
          <div className="text-6xl mb-4">🕒</div>
          <h2 className="text-2xl font-bold text-foreground">
            Scanner Outside Active Hours
          </h2>
          <p className="text-muted-foreground text-lg leading-relaxed">
            The Overnight Option Scanner is LIVE during the last hour of the market. 
            Please check back between <span className="font-semibold text-blue-400">3:00pm and 4:00pm ET</span>
          </p>
          <div className="pt-4">
            <div className="text-sm text-muted-foreground">
              Scanner will be active during market hours
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}