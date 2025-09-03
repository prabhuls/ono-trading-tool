import { useState, useEffect, useRef } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ChartTimeInterval, IntradayChartData, IntradayDataPoint } from '@/types/overnight-options';
import { api } from '@/lib/api';

interface SpyIntradayChartProps {
  ticker: string; // The ticker symbol (SPY, SPX, etc.)
  buyStrike: number;
  sellStrike: number;
  currentPrice: number;
  chartIntervals: ChartTimeInterval[];
  lastUpdated: string;
  onIntervalChange?: (interval: string) => void;
  hasAlgorithmResult?: boolean; // To know if strikes are from actual results
}

export function SpyIntradayChart({ 
  ticker,
  buyStrike, 
  sellStrike, 
  currentPrice,
  chartIntervals,
  lastUpdated,
  onIntervalChange,
  hasAlgorithmResult = false
}: SpyIntradayChartProps) {
  const [chartData, setChartData] = useState<IntradayChartData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeInterval, setActiveInterval] = useState('5m');
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Get current active interval from props
  const currentActiveInterval = chartIntervals.find(interval => interval.isActive)?.value || '5m';

  // Helper function to format timestamp to ET 12-hour format
  const formatTimeET = (timestamp: string): string => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('en-US', {
        timeZone: 'America/New_York',
        hour: 'numeric',
        minute: '2-digit',
        second: '2-digit',
        hour12: true
      });
    } catch {
      return timestamp; // fallback to original if parsing fails
    }
  };

  // Fetch chart data from API
  const fetchChartData = async (interval: string = currentActiveInterval) => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await api.chartData.getIntradayData(ticker, {
        interval,
        ...(hasAlgorithmResult ? { buy_strike: buyStrike, sell_strike: sellStrike } : {})
      });
      
      if (response.success && response.data) {
        const chartData = response.data as IntradayChartData;
        setChartData(chartData);
      } else {
        setError(response.message || 'Failed to fetch chart data');
      }
    } catch (err: any) {
      console.error('Failed to fetch chart data:', err);
      setError(err.message || 'Failed to fetch chart data');
    } finally {
      setLoading(false);
    }
  };

  // Draw chart on canvas
  const drawChart = () => {
    if (!chartData || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * devicePixelRatio;
    canvas.height = rect.height * devicePixelRatio;
    ctx.scale(devicePixelRatio, devicePixelRatio);

    // Clear canvas
    ctx.clearRect(0, 0, rect.width, rect.height);

    const priceData = chartData.price_data;
    if (priceData.length === 0) return;

    // Chart dimensions
    const padding = { top: 20, right: 60, bottom: 60, left: 60 };
    const chartWidth = rect.width - padding.left - padding.right;
    const chartHeight = rect.height - padding.top - padding.bottom;

    // Get price range including benchmark lines
    const prices = priceData.map(d => d.close);
    let minPrice = Math.min(...prices);
    let maxPrice = Math.max(...prices);
    
    // Include benchmark lines in range calculation if they exist
    const benchmarkPrices = [
      chartData.benchmark_lines.current_price,
      chartData.benchmark_lines.buy_strike,
      chartData.benchmark_lines.sell_strike
    ].filter(price => price !== null && price !== undefined && price > 0) as number[];
    
    if (benchmarkPrices.length > 0) {
      minPrice = Math.min(minPrice, ...benchmarkPrices);
      maxPrice = Math.max(maxPrice, ...benchmarkPrices);
    }
    
    const priceRange = maxPrice - minPrice;
    const paddedMin = minPrice - (priceRange * 0.1);
    const paddedMax = maxPrice + (priceRange * 0.1);
    const paddedRange = paddedMax - paddedMin;
    

    // Draw grid lines (horizontal) and y-axis labels
    ctx.strokeStyle = '#374151';
    ctx.lineWidth = 0.5;
    ctx.fillStyle = '#9CA3AF';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    
    for (let i = 0; i <= 4; i++) {
      const y = padding.top + (chartHeight / 4) * i;
      const priceValue = paddedMax - (paddedRange / 4) * i;
      
      // Draw grid line
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(padding.left + chartWidth, y);
      ctx.stroke();
      
      // Draw y-axis price label
      ctx.fillText(priceValue.toFixed(2), padding.left - 8, y);
    }
    
    // Draw vertical grid lines
    const numVerticalLines = 6;
    for (let i = 0; i < numVerticalLines; i++) {
      const x = padding.left + (chartWidth / (numVerticalLines - 1)) * i;
      ctx.beginPath();
      ctx.moveTo(x, padding.top);
      ctx.lineTo(x, padding.top + chartHeight);
      ctx.stroke();
    }

    // Draw price line
    ctx.strokeStyle = '#60A5FA';
    ctx.lineWidth = 2;
    ctx.beginPath();

    priceData.forEach((point, index) => {
      const x = padding.left + (index / (priceData.length - 1)) * chartWidth;
      const y = padding.top + chartHeight - ((point.close - paddedMin) / paddedRange) * chartHeight;

      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });
    ctx.stroke();

    // Draw benchmark lines
    const drawBenchmarkLine = (price: number, color: string, label: string, isDashed = false) => {
      if (price < paddedMin || price > paddedMax) {
        return;
      }

      const y = padding.top + chartHeight - ((price - paddedMin) / paddedRange) * chartHeight;

      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      if (isDashed) {
        ctx.setLineDash([5, 5]);
      } else {
        ctx.setLineDash([]);
      }

      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(padding.left + chartWidth, y);
      ctx.stroke();

      // Draw label
      ctx.fillStyle = color;
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillText(`${label} (${price.toFixed(2)})`, padding.left + chartWidth + 5, y);
    };

    // Draw benchmark lines
    drawBenchmarkLine(chartData.benchmark_lines.current_price, '#60A5FA', 'Current');
    
    if (chartData.benchmark_lines.buy_strike && chartData.benchmark_lines.buy_strike > 0) {
      drawBenchmarkLine(chartData.benchmark_lines.buy_strike, '#F97316', 'Buy', true);
    }
    
    if (chartData.benchmark_lines.sell_strike && chartData.benchmark_lines.sell_strike > 0) {
      drawBenchmarkLine(chartData.benchmark_lines.sell_strike, '#EF4444', 'Sell', true);
    }

    // Reset line dash
    ctx.setLineDash([]);
    
    // Draw x-axis time labels
    ctx.fillStyle = '#9CA3AF';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    
    const numLabels = 6; // Show 6 time labels across the chart
    for (let i = 0; i < numLabels; i++) {
      const dataIndex = Math.floor((priceData.length - 1) * (i / (numLabels - 1)));
      const x = padding.left + (dataIndex / (priceData.length - 1)) * chartWidth;
      const timeData = priceData[dataIndex];
      
      if (timeData && timeData.timestamp) {
        const date = new Date(timeData.timestamp);
        // Convert to ET timezone and format in 12-hour format
        const timeStr = date.toLocaleTimeString('en-US', { 
          timeZone: 'America/New_York',
          hour: 'numeric', 
          minute: '2-digit',
          hour12: true 
        });
        
        ctx.fillText(timeStr, x, padding.top + chartHeight + 8);
      }
    }
  };

  // Handle interval change
  const handleIntervalChange = (interval: string) => {
    setActiveInterval(interval);
    onIntervalChange?.(interval);
    fetchChartData(interval);
  };

  // Initial data fetch and redraw on data change
  useEffect(() => {
    fetchChartData(currentActiveInterval);
  }, [ticker, buyStrike, sellStrike, hasAlgorithmResult]); // Refetch when ticker or strikes change or algorithm result status changes

  useEffect(() => {
    if (chartData) {
      drawChart();
    }
  }, [chartData]);

  // Handle canvas resize
  useEffect(() => {
    const handleResize = () => {
      if (chartData) {
        drawChart();
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [chartData]);

  return (
    <Card className="p-4" style={{ borderColor: '#616266' }}>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-foreground">{ticker} Intraday Chart</h3>
        <div className="flex gap-2">
          {chartIntervals.map((interval) => (
            <Button
              key={interval.value}
              size="sm"
              variant={interval.isActive ? "default" : "outline"}
              className={interval.isActive 
                ? "bg-blue-600 hover:bg-blue-700 text-white" 
                : ""
              }
              onClick={() => handleIntervalChange(interval.value)}
              disabled={loading}
            >
              {interval.label}
            </Button>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="flex gap-4 mb-4 text-sm">
        {chartData?.benchmark_lines?.buy_strike && (
          <div className="flex items-center gap-2">
            <div className="w-3 h-0.5 bg-orange-500"></div>
            <span className="text-muted-foreground">Buy Strike ({chartData.benchmark_lines.buy_strike.toFixed(0)})</span>
          </div>
        )}
        {chartData?.benchmark_lines?.sell_strike && (
          <div className="flex items-center gap-2">
            <div className="w-3 h-0.5 bg-red-500"></div>
            <span className="text-muted-foreground">Sell Strike ({chartData.benchmark_lines.sell_strike.toFixed(0)})</span>
          </div>
        )}
        <div className="flex items-center gap-2">
          <div className="w-3 h-0.5 bg-blue-400"></div>
          <span className="text-muted-foreground">Current Price</span>
        </div>
      </div>

      {/* Chart Container */}
      <div className="relative bg-gray-900 rounded-lg h-64 mb-4">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center text-muted-foreground">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400 mx-auto mb-2"></div>
              <div className="text-sm">Loading chart data...</div>
            </div>
          </div>
        )}
        
        {error && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center text-red-400">
              <div className="text-lg mb-2">⚠️</div>
              <div className="text-sm">{error}</div>
              <Button 
                size="sm" 
                variant="outline" 
                className="mt-2"
                onClick={() => fetchChartData(currentActiveInterval)}
              >
                Retry
              </Button>
            </div>
          </div>
        )}

        {!loading && !error && chartData && (
          <canvas
            ref={canvasRef}
            className="w-full h-full rounded-lg"
            style={{ width: '100%', height: '100%' }}
          />
        )}
      </div>

      {/* Chart Info */}
      <div className="flex justify-between text-sm text-muted-foreground">
        <div>
          {chartData && (
            <span>
              {chartData.metadata.total_candles} candles • {chartData.interval} interval
            </span>
          )}
        </div>
        <div>
          Last updated: {chartData ? formatTimeET(chartData.metadata.last_updated) : formatTimeET(lastUpdated)}
        </div>
      </div>
    </Card>
  );
}