'use client';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Crown, Lock, CheckCircle } from 'lucide-react';

interface VipSubscriptionModalProps {
  isOpen: boolean;
  ticker: string;
  onClose: () => void;
  onSwitchToDefault: () => void;
}

export function VipSubscriptionModal({
  isOpen,
  ticker,
  onClose,
  onSwitchToDefault,
}: VipSubscriptionModalProps) {
  const vipSymbols = ['QQQ', 'IWM', 'GLD'];

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex justify-center mb-4">
            <div className="relative">
              <Crown className="h-16 w-16 text-yellow-400 fill-yellow-400" />
              <Lock className="h-6 w-6 text-yellow-600 absolute -bottom-1 -right-1 bg-background rounded-full p-0.5" />
            </div>
          </div>
          <DialogTitle className="text-center text-2xl">
            VIP Subscription Required
          </DialogTitle>
          <DialogDescription className="text-center text-base pt-2">
            <span className="font-semibold text-foreground">{ticker}</span> is a VIP symbol that requires an{' '}
            <span className="font-semibold text-yellow-500">ONO1 (VIP)</span> subscription to access.
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          <div className="bg-gradient-to-r from-yellow-50 to-amber-50 dark:from-yellow-950/20 dark:to-amber-950/20 rounded-lg p-4 border border-yellow-200 dark:border-yellow-800">
            <h4 className="font-semibold text-sm mb-3 flex items-center gap-2">
              <Crown className="h-4 w-4 text-yellow-500" />
              VIP Access Includes:
            </h4>
            <ul className="space-y-2">
              {vipSymbols.map((symbol) => (
                <li key={symbol} className="flex items-center gap-2 text-sm">
                  <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
                  <span className="font-mono font-semibold">{symbol}</span>
                  <span className="text-muted-foreground">
                    {symbol === 'QQQ' && '- Nasdaq-100 ETF'}
                    {symbol === 'IWM' && '- Russell 2000 ETF'}
                    {symbol === 'GLD' && '- Gold ETF'}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2">
          <Button
            onClick={onSwitchToDefault}
            className="w-full sm:w-auto bg-blue-600 hover:bg-blue-700"
          >
            Switch to SPY
          </Button>
          <Button
            onClick={onClose}
            variant="outline"
            className="w-full sm:w-auto"
          >
            Close
          </Button>
        </DialogFooter>

        <div className="text-center text-xs text-muted-foreground pt-2 border-t">
          Contact your administrator to upgrade to VIP subscription
        </div>
      </DialogContent>
    </Dialog>
  );
}
