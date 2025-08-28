/**
 * Example usage of CurrentPrice components
 * This file demonstrates different ways to use the stock price components
 * Remove this file after reviewing the examples
 */

'use client';

import { CurrentPrice, TickerSelector, CompactPriceDisplay } from './current-price';
import type { SupportedTicker } from '@/types/stock-price';

export function CurrentPriceExamples() {
  return (
    <div className="space-y-8 p-6">
      {/* Example 1: Full CurrentPrice component with all features */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Full Current Price Component</h3>
        <CurrentPrice
          defaultTicker="SPY"
          showTickerSelector={true}
          showRefreshButton={true}
          onTickerChange={(ticker) => console.log('Ticker changed to:', ticker)}
        />
      </div>

      {/* Example 2: Minimal CurrentPrice component */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Minimal Current Price (No Selector/Refresh)</h3>
        <CurrentPrice
          defaultTicker="XSP"
          showTickerSelector={false}
          showRefreshButton={false}
        />
      </div>

      {/* Example 3: Standalone TickerSelector */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Standalone Ticker Selector</h3>
        <TickerSelector
          selectedTicker="SPX"
          onTickerChange={(ticker: SupportedTicker) => console.log('Selected:', ticker)}
        />
      </div>

      {/* Example 4: Compact Price Display for inline use */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Compact Price Display</h3>
        <div className="space-y-2">
          <CompactPriceDisplay ticker="SPY" showChange={true} />
          <CompactPriceDisplay ticker="XSP" showChange={true} />
          <CompactPriceDisplay ticker="SPX" showChange={false} />
        </div>
      </div>

      {/* Example 5: Multiple compact displays in a row */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Inline Multiple Prices</h3>
        <div className="flex flex-wrap gap-4">
          <CompactPriceDisplay ticker="SPY" />
          <CompactPriceDisplay ticker="XSP" />
          <CompactPriceDisplay ticker="SPX" />
        </div>
      </div>
    </div>
  );
}

/**
 * Example integration in a header or navigation
 */
export function HeaderPriceExample() {
  return (
    <div className="flex items-center justify-between p-4 bg-gray-900 text-white">
      <div className="text-lg font-bold">Trading Dashboard</div>
      <div className="flex items-center gap-6">
        <CompactPriceDisplay ticker="SPY" showChange={true} />
        <CompactPriceDisplay ticker="XSP" showChange={true} />
        <CompactPriceDisplay ticker="SPX" showChange={true} />
      </div>
    </div>
  );
}

/**
 * Example widget for sidebar or dashboard
 */
export function PriceWidgetExample() {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-md">
      <h4 className="text-md font-semibold mb-3">Market Prices</h4>
      <div className="space-y-2">
        <CompactPriceDisplay ticker="SPY" showChange={true} />
        <CompactPriceDisplay ticker="XSP" showChange={true} />
        <CompactPriceDisplay ticker="SPX" showChange={true} />
      </div>
    </div>
  );
}