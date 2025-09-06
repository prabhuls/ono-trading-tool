import { StatusBarInfo } from '@/types/overnight-options';

interface StatusBarsProps {
  statusBars: StatusBarInfo;
}

export function StatusBars({ statusBars }: StatusBarsProps) {
  const hasValidStatus = statusBars?.scannerActive !== null && statusBars?.scannerActive !== undefined;
  
  return (
    <div className="space-y-2">
      {/* Scanner Active Status */}
      <div className="bg-green-600 bg-opacity-20 border border-green-600 rounded-lg px-4 py-2">
        <div className="flex items-center gap-2">
          <span className="text-green-400 font-medium">Scanner Status:</span>
          {hasValidStatus ? (
            <span className="text-green-200 text-sm">{statusBars.scannerActive}</span>
          ) : (
            <span className="text-gray-400 text-sm animate-pulse">Loading scanner status...</span>
          )}
        </div>
      </div>
    </div>
  );
}