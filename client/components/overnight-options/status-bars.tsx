import { StatusBarInfo } from '@/types/overnight-options';

interface StatusBarsProps {
  statusBars: StatusBarInfo;
}

export function StatusBars({ statusBars }: StatusBarsProps) {
  return (
    <div className="space-y-2">
      {/* Scanner Active Status */}
      <div className="bg-green-600 bg-opacity-20 border border-green-600 rounded-lg px-4 py-2">
        <div className="flex items-center gap-2">
          <span className="text-green-400 font-medium">Scanner Active:</span>
          <span className="text-green-200 text-sm">{statusBars.scannerActive}</span>
        </div>
      </div>
    </div>
  );
}