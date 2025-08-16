import { useQuery } from '@tanstack/react-query';
import { useEffect, useState, lazy, Suspense } from 'react';

// Fix ApexCharts SSR issue - lazy loading for client-side only
const Chart = lazy(() => import('react-apexcharts'));

interface BreakevenChartProps {
  ticker: string;
  currentPrice: number;
  breakevenPrice: number;
  scenarios?: any[];
  trend?: 'uptrend' | 'downtrend' | 'neutral';
}

interface CandleData {
  x: Date;
  y: [number, number, number, number]; // [open, high, low, close]
}

interface StockData {
  symbol: string;
  name: string;
  description: string;
  price: number;
  change: number;
  changePercent: number;
  open: number;
  high: number;
  low: number;
  volume: number;
  yearRange: string;
  updated: string;
  trendType: 'uptrend' | 'downtrend' | 'neutral';
  trendStrength: number;
  priceData: CandleData[];
}

export function BreakevenChart({ 
  ticker, 
  currentPrice, 
  breakevenPrice, 
  scenarios,
  trend = 'neutral'
}: BreakevenChartProps) {
  
  const [isClient, setIsClient] = useState(false);

  // Ensure we're on client side for ApexCharts
  useEffect(() => {
    setIsClient(true);
  }, []);

  // Enhanced debugging
  console.log('🚨 BreakevenChart COMPONENT MOUNTED');
  console.log('🚨 Props received:', {
    ticker,
    currentPrice,
    breakevenPrice,
    tickerType: typeof ticker,
    tickerLength: ticker?.length,
    enabled: !!ticker
  });
  
  // Validate ticker prop
  if (!ticker || typeof ticker !== 'string' || ticker.trim() === '') {
    console.error('❌ BreakevenChart: Invalid ticker prop:', ticker);
    return (
      <div className="h-[500px] flex items-center justify-center bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="text-center">
          <p className="text-red-600 font-medium">Chart Error</p>
          <p className="text-gray-600 text-sm">Invalid ticker: {JSON.stringify(ticker)}</p>
        </div>
      </div>
    );
  }

  const cleanTicker = ticker.trim().toUpperCase();
  console.log('🚨 Clean ticker for API call:', cleanTicker);
  
  // FIXED: Use stable query key instead of Date.now() to prevent infinite loops
  const queryKey = `breakeven-chart-${cleanTicker}`;
  console.log('🚨 Stable query key:', queryKey);
  
  const { data: stockData, isLoading, error } = useQuery<StockData>({
    queryKey: [queryKey],
    enabled: !!cleanTicker && isClient,
    // FIXED: Reasonable caching instead of aggressive cache-busting
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 5 * 60 * 1000, // 5 minutes (was cacheTime in v4)
    refetchOnWindowFocus: false,
    retry: 2,
    queryFn: async () => {
      console.log('🌐 BreakevenChart - queryFn STARTED for ticker:', cleanTicker);
      console.log('🌐 API call timestamp:', new Date().toISOString());
      
      // Call backend endpoint for chart data
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const url = `${backendUrl}/api/v1/stocks/${cleanTicker}`;
      console.log('🌐 Fetching URL:', url);
      
      // Get auth token from localStorage/sessionStorage
      const token = localStorage.getItem('auth_token') || sessionStorage.getItem('token');
      
      try {
        const response = await fetch(url, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
          },
        });
        
        console.log('📡 Response status:', response.status);
        console.log('📡 Response ok:', response.ok);
        
        if (!response.ok) {
          const errorText = await response.text();
          console.error('❌ API Error:', response.status, errorText);
          throw new Error(`API Error: ${response.status} - ${errorText}`);
        }
        
        const data = await response.json();
        console.log('✅ API Success - data keys:', Object.keys(data));
        console.log('✅ Price data length:', data.priceData?.length || 0);
        
        return data;
      } catch (fetchError) {
        console.error('💥 Fetch error:', fetchError);
        throw fetchError;
      }
    }
  });

  console.log('📊 Query state:', { 
    isLoading, 
    hasError: !!error, 
    hasData: !!stockData,
    isClient,
    enabled: !!cleanTicker && isClient
  });

  // Loading state
  if (!isClient || isLoading) {
    console.log('⏳ Showing loading state - isClient:', isClient, 'isLoading:', isLoading);
    return (
      <div className="h-[500px] flex items-center justify-center bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500 mx-auto mb-2"></div>
          <p className="text-gray-600">Loading chart data for {cleanTicker}...</p>
          <p className="text-xs text-gray-400 mt-1">Client: {isClient ? 'Ready' : 'Loading'}</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    console.error('❌ Query error:', error);
    return (
      <div className="h-[500px] flex items-center justify-center bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="text-center">
          <p className="text-red-600 font-medium">Failed to load chart data</p>
          <p className="text-gray-600 text-sm">{error.message}</p>
          <p className="text-xs text-gray-400 mt-1">Ticker: {cleanTicker}</p>
        </div>
      </div>
    );
  }

  // No data state
  if (!stockData?.priceData || stockData.priceData.length === 0) {
    console.log('❌ No price data available:', stockData);
    return (
      <div className="h-[500px] flex items-center justify-center bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="text-center">
          <p className="text-gray-600">No chart data available for {cleanTicker}</p>
          <p className="text-xs text-gray-400 mt-1">
            {stockData ? 'Data received but no price history' : 'No data received'}
          </p>
        </div>
      </div>
    );
  }

  // Filter to only include trading days (exclude weekends)
  const tradingDaysOnly = stockData.priceData.filter(candle => {
    const date = new Date(candle.x);
    const dayOfWeek = date.getDay();
    return dayOfWeek !== 0 && dayOfWeek !== 6;
  });

  // Get last 14 trading days
  const last14TradingDays = tradingDaysOnly.slice(-14);
  
  // Calculate Trip Wire price based on trend
  // For uptrend (put spreads): Trip Wire = Breakeven + 7%
  // For downtrend (call spreads): Trip Wire = Breakeven - 7%
  const tripWirePrice = trend === 'uptrend' 
    ? breakevenPrice * 1.07  // 7% above breakeven
    : trend === 'downtrend'
    ? breakevenPrice * 0.93  // 7% below breakeven
    : breakevenPrice;        // No trip wire for neutral
  
  console.log('📈 Chart data prepared:', {
    totalCandles: stockData.priceData.length,
    tradingDays: tradingDaysOnly.length,
    last14Days: last14TradingDays.length,
    trend,
    breakevenPrice,
    tripWirePrice: trend !== 'neutral' ? tripWirePrice : 'N/A'
  });
  
  if (last14TradingDays.length === 0) {
    return (
      <div className="h-[500px] flex items-center justify-center bg-white rounded-lg border border-gray-200 shadow-sm">
        <p className="text-gray-600">No trading day data available for chart</p>
      </div>
    );
  }
  
  // Prepare chart data for ApexCharts candlestick
  const chartData = last14TradingDays.map(candle => ({
    x: new Date(candle.x).toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric' 
    }),
    y: candle.y // [open, high, low, close]
  }));

  // Calculate price range for visual positioning
  const allPrices = last14TradingDays.flatMap(candle => candle.y);
  const minPriceData = Math.min(...allPrices);
  const maxPriceData = Math.max(...allPrices);
  
  // Create Y-axis range (include Trip Wire in calculations)
  const priceDifference = Math.abs(currentPrice - breakevenPrice);
  const buffer = Math.max(priceDifference * 0.2, (maxPriceData - minPriceData) * 0.1);
  
  const yAxisMin = Math.min(minPriceData, breakevenPrice, currentPrice, tripWirePrice) - buffer;
  const yAxisMax = Math.max(maxPriceData, breakevenPrice, currentPrice, tripWirePrice) + buffer;

  const chartOptions = {
    chart: {
      type: 'candlestick' as const,
      height: 500,
      background: 'transparent',
      toolbar: { show: false },
      zoom: { enabled: false },
      animations: {
        enabled: true,
        easing: 'easeinout',
        speed: 800
      }
    },
    theme: { mode: 'light' as const },
    plotOptions: {
      candlestick: {
        colors: {
          upward: '#16a34a',
          downward: '#dc2626'
        },
        wick: { useFillColor: true }
      }
    },
    xaxis: {
      type: 'category' as const,
      labels: {
        style: {
          colors: '#6b7280',
          fontSize: '12px'
        }
      },
      axisBorder: { color: '#e5e7eb' },
      axisTicks: { color: '#e5e7eb' }
    },
    yaxis: {
      min: yAxisMin,
      max: yAxisMax,
      tooltip: { enabled: true },
      labels: {
        style: {
          colors: '#6b7280',
          fontSize: '12px'
        },
        formatter: (value: number) => `$${value.toFixed(2)}`
      },
      axisBorder: { color: '#e5e7eb' }
    },
    grid: {
      borderColor: '#f3f4f6',
      strokeDashArray: 2,
      xaxis: { lines: { show: true } },
      yaxis: { lines: { show: true } }
    },
    annotations: {
      yaxis: [
        {
          y: breakevenPrice,
          borderColor: '#f59e0b',
          borderWidth: 3,
          strokeDashArray: 0,
          label: {
            borderColor: '#f59e0b',
            position: 'center',
            style: {
              color: '#fff',
              background: '#f59e0b',
              fontSize: '12px',
              fontWeight: 'bold'
            },
            text: `Breakeven: $${breakevenPrice.toFixed(2)}`
          }
        },
        {
          y: currentPrice,
          borderColor: '#16a34a',
          borderWidth: 2,
          strokeDashArray: 5,
          label: {
            borderColor: '#16a34a',
            position: 'center',
            style: {
              color: '#fff',
              background: '#16a34a',
              fontSize: '12px',
              fontWeight: 'bold'
            },
            text: `Current: $${currentPrice.toFixed(2)}`
          }
        },
        // Trip Wire line (only show for uptrend/downtrend)
        ...(trend !== 'neutral' ? [{
          y: tripWirePrice,
          borderColor: '#eab308',
          borderWidth: 2,
          strokeDashArray: 8,
          label: {
            borderColor: '#eab308',
            position: 'center',
            style: {
              color: '#fff',
              background: '#eab308',
              fontSize: '11px',
              fontWeight: 'bold'
            },
            text: `Trip Wire: $${tripWirePrice.toFixed(2)} (${trend === 'uptrend' ? '+7%' : '-7%'})`
          }
        }] : [])
      ],
      areas: [
        // Profit zone (safe zone)
        {
          y: breakevenPrice,
          y2: yAxisMax,
          fillColor: '#16a34a',
          opacity: 0.1,
          borderColor: '#16a34a',
          borderWidth: 1,
          strokeDashArray: 3
        },
        // Warning zone (between Trip Wire and Breakeven) - only for uptrend/downtrend
        ...(trend !== 'neutral' ? [{
          y: trend === 'uptrend' ? tripWirePrice : breakevenPrice,
          y2: trend === 'uptrend' ? breakevenPrice : tripWirePrice,
          fillColor: '#eab308',
          opacity: 0.08,
          borderColor: '#eab308',
          borderWidth: 1,
          strokeDashArray: 5
        }] : []),
        // Danger zone (past breakeven)
        {
          y: yAxisMin,
          y2: trend !== 'neutral' && trend === 'uptrend' ? tripWirePrice : breakevenPrice,
          fillColor: '#dc2626',
          opacity: 0.1,
          borderColor: '#dc2626',
          borderWidth: 1,
          strokeDashArray: 3
        }
      ]
    },
    tooltip: {
      theme: 'light',
      style: { fontSize: '12px' },
      custom: function({ seriesIndex, dataPointIndex, w }: any) {
        const data = w.globals.initialSeries[seriesIndex].data[dataPointIndex];
        const date = data.x;
        const [open, high, low, close] = data.y;
        
        return `
          <div class="bg-white border border-gray-200 rounded p-3 text-gray-900 shadow-lg">
            <div class="font-bold text-gray-900 mb-2">${date}</div>
            <div class="space-y-1 text-sm">
              <div>Open: <span class="text-green-600">$${open.toFixed(2)}</span></div>
              <div>High: <span class="text-green-600">$${high.toFixed(2)}</span></div>
              <div>Low: <span class="text-red-600">$${low.toFixed(2)}</span></div>
              <div>Close: <span class="text-gray-900">$${close.toFixed(2)}</span></div>
            </div>
          </div>
        `;
      }
    },
    legend: { show: false }
  };

  const series = [{
    name: 'Price',
    data: chartData
  }];

  console.log('🎯 Rendering chart with ApexCharts');

  return (
    <div className="relative">
      <div className="bg-white rounded-lg border border-gray-200 p-2 shadow-sm">
        <Suspense 
          fallback={
            <div className="h-[500px] flex items-center justify-center">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500 mx-auto mb-2"></div>
                <p className="text-gray-600">Loading chart library...</p>
              </div>
            </div>
          }
        >
          <Chart 
            options={chartOptions}
            series={series}
            type="candlestick"
            height={500}
          />
        </Suspense>
      </div>
    </div>
  );
}