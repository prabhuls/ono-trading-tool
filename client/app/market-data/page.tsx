'use client';

import { useState, useEffect } from 'react';
import { SpyIntradayChart } from '@/components/overnight-options/spy-intraday-chart';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ChartTimeInterval } from '@/types/overnight-options';
import { api } from '@/lib/api';
import Navbar from '@/components/layout/Navbar';

export default function MarketDataPage() {
  const [selectedTicker, setSelectedTicker] = useState<'SPY' | 'SPX'>('SPY');
  const [currentPrice, setCurrentPrice] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chartIntervals, setChartIntervals] = useState<ChartTimeInterval[]>([
    { label: '1D', value: '1d', isActive: false },
    { label: '5M', value: '5m', isActive: true },
    { label: '15M', value: '15m', isActive: false },
    { label: '30M', value: '30m', isActive: false },
    { label: '1H', value: '1h', isActive: false },
  ]);

  // Fetch current price for the selected ticker
  const fetchCurrentPrice = async (ticker: string) => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.market.currentPrice(ticker);
      
      if (response.success && response.data) {
        const priceData = response.data as { price: number };
        setCurrentPrice(priceData.price);
      } else {
        setError('Failed to fetch current price');
      }
    } catch (err: any) {
      console.error('Error fetching current price:', err);
      setError(err.message || 'Failed to fetch current price');
    } finally {
      setLoading(false);
    }
  };

  // Fetch price when ticker changes
  useEffect(() => {
    fetchCurrentPrice(selectedTicker);
  }, [selectedTicker]);

  // Handle interval change
  const handleIntervalChange = (interval: string) => {
    setChartIntervals(prev => prev.map(item => ({
      ...item,
      isActive: item.value === interval
    })));
  };

  // Format last updated time
  const getLastUpdated = () => {
    return new Date().toISOString();
  };

  return (
    <>
      <Navbar />
      <div className="min-h-screen bg-background p-4 md:p-8">
        <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground mb-2">Market Data Dashboard</h1>
          <p className="text-muted-foreground">View real-time market data for SPY and SPX</p>
        </div>

        {/* Ticker Selection */}
        <Card className="mb-6 p-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold mb-2">Select Index</h2>
              <p className="text-sm text-muted-foreground">Choose between SPY ETF or SPX Index</p>
            </div>
            <Tabs value={selectedTicker} onValueChange={(value) => setSelectedTicker(value as 'SPY' | 'SPX')}>
              <TabsList className="grid w-[200px] grid-cols-2">
                <TabsTrigger value="SPY">SPY</TabsTrigger>
                <TabsTrigger value="SPX">SPX</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </Card>

        {/* Current Price Display */}
        <Card className="mb-6 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-muted-foreground">
                {selectedTicker} Current Price
              </h3>
              <div className="flex items-baseline gap-2 mt-1">
                {loading ? (
                  <div className="animate-pulse bg-muted h-8 w-32 rounded"></div>
                ) : error ? (
                  <span className="text-red-500 text-sm">{error}</span>
                ) : (
                  <>
                    <span className="text-3xl font-bold text-foreground">
                      ${currentPrice.toFixed(2)}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      Last updated: {new Date().toLocaleTimeString()}
                    </span>
                  </>
                )}
              </div>
            </div>
            <Button 
              size="sm" 
              variant="outline"
              onClick={() => fetchCurrentPrice(selectedTicker)}
              disabled={loading}
            >
              Refresh
            </Button>
          </div>
        </Card>

        {/* Chart Display */}
        <div className="mb-6">
          <SpyIntradayChart
            ticker={selectedTicker}
            buyStrike={0} // No strikes for simple market data view
            sellStrike={0}
            currentPrice={currentPrice}
            chartIntervals={chartIntervals}
            lastUpdated={getLastUpdated()}
            onIntervalChange={handleIntervalChange}
            hasAlgorithmResult={false}
          />
        </div>

        {/* Additional Information */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">About {selectedTicker}</h3>
          <div className="space-y-3 text-sm text-muted-foreground">
            {selectedTicker === 'SPY' ? (
              <>
                <p>
                  <strong>SPDR S&P 500 ETF Trust (SPY)</strong> is an exchange-traded fund that tracks 
                  the S&P 500 index. It provides intraday liquidity and is one of the most actively 
                  traded ETFs in the world.
                </p>
                <p>
                  SPY data includes multiple intraday data points, allowing for detailed price movement 
                  analysis throughout the trading day.
                </p>
              </>
            ) : (
              <>
                <p>
                  <strong>S&P 500 Index (SPX)</strong> is the underlying index that represents 500 of 
                  the largest U.S. publicly traded companies. It&apos;s a market-capitalization-weighted index.
                </p>
                <p>
                  SPX data typically provides daily values as it&apos;s an index rather than a tradeable security. 
                  The chart may show limited intraday data points compared to SPY.
                </p>
              </>
            )}
          </div>
        </Card>

        {/* Data Source Notice */}
        <div className="mt-6 text-center text-xs text-muted-foreground">
          <p>Data provided by market data API. Prices may be delayed.</p>
          <p className="mt-1">
            {selectedTicker === 'SPX' && 'SPX data is sourced from ISIN endpoint with daily granularity.'}
          </p>
        </div>
      </div>
    </div>
    </>
  );
}