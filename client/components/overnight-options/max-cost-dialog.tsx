'use client';

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

interface MaxCostDialogProps {
  open: boolean;
  currentMaxCost: number;
  onClose: () => void;
  onSave: (newMaxCost: number) => void;
}

export function MaxCostDialog({ 
  open, 
  currentMaxCost, 
  onClose, 
  onSave 
}: MaxCostDialogProps) {
  const [inputValue, setInputValue] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isValid, setIsValid] = useState(false);

  // Initialize input value when dialog opens
  useEffect(() => {
    if (open) {
      setInputValue(currentMaxCost.toFixed(2));
      setError(null);
      setIsValid(true);
    }
  }, [open, currentMaxCost]);

  // Validate input value
  useEffect(() => {
    const validate = () => {
      if (!inputValue.trim()) {
        setError('Max cost is required');
        setIsValid(false);
        return;
      }

      // Remove dollar sign if present and parse
      const cleanValue = inputValue.replace(/^\$/, '');
      const numValue = parseFloat(cleanValue);

      if (isNaN(numValue)) {
        setError('Please enter a valid number');
        setIsValid(false);
        return;
      }

      if (numValue < 0.01) {
        setError('Minimum max cost is $0.01');
        setIsValid(false);
        return;
      }

      if (numValue > 2.00) {
        setError('Maximum max cost is $2.00');
        setIsValid(false);
        return;
      }

      setError(null);
      setIsValid(true);
    };

    validate();
  }, [inputValue]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let value = e.target.value;
    
    // Allow dollar sign at the beginning
    if (value.startsWith('$')) {
      value = value.substring(1);
    }
    
    // Only allow numbers and decimal point
    if (value && !/^\d*\.?\d*$/.test(value)) {
      return;
    }
    
    setInputValue(value);
  };

  const handleSave = () => {
    if (!isValid) return;
    
    const cleanValue = inputValue.replace(/^\$/, '');
    const numValue = parseFloat(cleanValue);
    
    if (!isNaN(numValue) && numValue >= 0.01 && numValue <= 2.00) {
      onSave(numValue);
      onClose();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && isValid) {
      handleSave();
    } else if (e.key === 'Escape') {
      onClose();
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Adjust Max Cost</DialogTitle>
          <DialogDescription>
            Set the maximum cost threshold for spread recommendations. 
            The algorithm will only suggest spreads within this cost limit.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="maxCost" className="text-sm font-medium text-foreground">
              Max Cost (USD)
            </label>
            <div className="relative">
              <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground">
                $
              </div>
              <Input
                id="maxCost"
                type="text"
                value={inputValue}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder="0.74"
                className={`pl-8 ${error ? 'border-red-500 focus-visible:ring-red-500' : ''}`}
                autoFocus
              />
            </div>
            {error && (
              <p className="text-sm text-red-500 mt-1">{error}</p>
            )}
            <p className="text-xs text-muted-foreground">
              Valid range: $0.01 - $2.00
            </p>
          </div>

          <div className="bg-muted/50 p-3 rounded-lg">
            <p className="text-sm text-muted-foreground">
              <strong>Current:</strong> ${currentMaxCost.toFixed(2)}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Lower values find cheaper spreads with potentially lower profits. 
              Higher values allow more expensive spreads with potentially higher profits.
            </p>
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button
            variant="outline"
            onClick={onClose}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={!isValid}
            className="bg-blue-600 hover:bg-blue-700 text-white disabled:bg-gray-600 disabled:cursor-not-allowed"
          >
            Apply
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}