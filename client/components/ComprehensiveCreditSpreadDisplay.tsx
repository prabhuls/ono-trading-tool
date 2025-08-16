"use client";

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, DollarSign, Calendar, Target, AlertCircle, CheckCircle, ArrowLeft, Bookmark } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { BreakevenChart } from './BreakevenChart';
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useToast } from '@/lib/hooks/use-toast';

interface CreditSpreadDisplayProps {
  data: any;
  onClose: () => void;
  hideClaimButton?: boolean;
}

export function ComprehensiveCreditSpreadDisplay({ data, onClose, hideClaimButton = false }: CreditSpreadDisplayProps) {
  const [isClaiming, setIsClaiming] = useState(false);
  const [contractQuantity, setContractQuantity] = useState(1);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // 🔍 DEBUG: Log the incoming data structure
  console.log('🔍 ComprehensiveCreditSpreadDisplay - Received data:', data);
  console.log('🔍 Data keys:', Object.keys(data || {}));
  console.log('🔍 data.ticker:', data?.ticker);
  console.log('🔍 data.symbol:', data?.symbol);
  console.log('🔍 data.spreadData:', data?.spreadData);
  console.log('🔍 data.spread_analysis:', data?.spread_analysis);

  const claimMutation = useMutation({
    mutationFn: async (spreadData: any) => {
      const localToken = localStorage.getItem('auth_token');
      const sessionToken = sessionStorage.getItem('token');
      const token = localToken || sessionToken;
      
      if (!token) {
        throw new Error('No authentication token found');
      }
      
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      
      // Prepare the data for the new credit-spreads endpoint
      const requestData = {
        ticker: spreadData.ticker,
        current_price: spreadData.currentPrice,
        short_strike: spreadData.shortStrike,
        long_strike: spreadData.longStrike,
        net_credit: spreadData.netCredit,
        max_risk: spreadData.maxRisk,
        roi: spreadData.roi,
        expiration: spreadData.expiration,
        contract_type: spreadData.contractType,
        days_to_expiration: spreadData.daysToExpiration,
        breakeven: spreadData.breakeven,
        buffer_room: spreadData.bufferRoom,
        scenarios: spreadData.scenarios,
        spread_type: data?.spread_analysis?.spread_type,
        sell_contract: data?.spread_analysis?.sell_contract || data?.spread_analysis?.sell_contract_symbol,
        buy_contract: data?.spread_analysis?.buy_contract || data?.spread_analysis?.buy_contract_symbol
      };
      
      // Use the simplified user-spreads endpoint (matches reference implementation)
      const response = await fetch(`${backendUrl}/api/v1/user-spreads/claim`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(spreadData), // Send spreadData directly, like reference
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || 'Failed to claim credit spread');
      }
      
      return response.json();
    },
    onSuccess: async () => {
      console.log('🎯 CLAIM SUCCESS - Forcing immediate Trade Journal refresh...');
      
      toast({
        title: "Credit Spread Claimed!",
        description: "Analysis saved to your Trade Journal",
        variant: "default",
      });
      
      // NUCLEAR OPTION: Force immediate data refetch
      await queryClient.resetQueries({ queryKey: ['/api/credit-spread/user-claims'] });
      await queryClient.refetchQueries({ queryKey: ['/api/credit-spread/user-claims'] });
      
      // Also trigger a window event that Trade Journal can listen to
      window.dispatchEvent(new CustomEvent('tradeJournalUpdate', { 
        detail: { action: 'claim', timestamp: Date.now() } 
      }));
      
      console.log('✅ CLAIM - Forced refresh complete');
    },
    onError: (error) => {
      console.error('❌ CLAIM ERROR:', error);
      toast({
        title: "Failed to Claim",
        description: "Please try again",
        variant: "destructive",
      });
    },
    onSettled: () => {
      setIsClaiming(false);
    }
  });

  const handleClaim = () => {
    if (!data || !data.spread_analysis || !data.spread_analysis.found) return;
    
    setIsClaiming(true);
    const { current_stock_price, spread_analysis } = data;
    
    // FIXED: Determine correct contract type based on trend direction
    // - uptrend tickers → 'put' credit spreads (safer above support)
    // - downtrend tickers → 'call' credit spreads (safer below resistance)
    let contractType = 'call'; // default fallback
    
    // PRIORITY 1: Use trend from URL (most reliable)
    if (data.trend) {
      contractType = data.trend === 'uptrend' ? 'put' : 'call';
      console.log('🎯 Using TREND-BASED determination:', data.trend, '→', contractType);
    } 
    // PRIORITY 2: Extract trend from URL if data.trend is missing
    else {
      const urlParams = new URLSearchParams(window.location.search);
      const urlTrend = urlParams.get('trend');
      if (urlTrend) {
        contractType = urlTrend === 'uptrend' ? 'put' : 'call';
        console.log('🎯 Using URL TREND determination:', urlTrend, '→', contractType);
      }
      // PRIORITY 3: Fallback to API strategy_type only if no trend available
      else if (spread_analysis.strategy_type) {
        contractType = spread_analysis.strategy_type.includes('put') ? 'put' : 'call';
        console.log('⚠️ Fallback to strategy_type:', spread_analysis.strategy_type, '→', contractType);
      } 
      // PRIORITY 4: Final fallback to spread_type
      else if (spread_analysis.spread_type) {
        contractType = spread_analysis.spread_type.includes('put') ? 'put' : 'call';
        console.log('⚠️ Final fallback to spread_type:', spread_analysis.spread_type, '→', contractType);
      }
    }
    
    console.log('🔍 CLAIM CONTRACT TYPE DETERMINATION:');
    console.log('   - data.trend:', data.trend);
    console.log('   - strategy_type:', spread_analysis.strategy_type);
    console.log('   - spread_type:', spread_analysis.spread_type);
    console.log('   - Final contractType:', contractType);
    
    // Create comprehensive spread data to save
    const spreadToSave = {
      ticker: data.ticker,
      currentPrice: current_stock_price,
      shortStrike: spread_analysis.sell_strike,
      longStrike: spread_analysis.buy_strike,
      netCredit: spread_analysis.net_credit,
      maxRisk: spread_analysis.max_risk,
      roi: spread_analysis.roi_percent,
      expiration: spread_analysis.expiration,
      contractType: contractType,
      daysToExpiration: spread_analysis.dte,
      breakeven: spread_analysis.breakeven,
      bufferRoom: ((spread_analysis.breakeven / current_stock_price - 1) * 100),
      scenarios: Object.entries(spread_analysis.price_scenarios).map(([change, scenario]: [string, any]) => ({
        priceChange: change === '+0%' ? '0%' : change,
        newPrice: scenario.stock_price,
        profit: scenario.profit_loss,
        profitPercent: scenario.profit_loss_percent
      }))
    };
    
    claimMutation.mutate(spreadToSave);
  };
  // Check if this is saved data or API response data
  const isSavedData = data && (data.spreadData || (data.ticker && data.shortStrike && !data.spread_analysis));
  const isApiData = data && data.spread_analysis && data.spread_analysis.found;
  
  // 🔍 DEBUG: Log data detection results
  console.log('🔍 isSavedData:', isSavedData);
  console.log('🔍 isApiData:', isApiData);
  console.log('🔍 Detection criteria:');
  console.log('   - data.spreadData exists:', !!data?.spreadData);
  console.log('   - data.ticker exists:', !!data?.ticker);
  console.log('   - data.shortStrike exists:', !!data?.shortStrike);
  console.log('   - data.spread_analysis exists:', !!data?.spread_analysis);
  console.log('   - data.spread_analysis.found:', data?.spread_analysis?.found);

  if (!isSavedData && !isApiData) {
    return (
      <div className="min-h-screen bg-white p-6">
        <div className="max-w-4xl mx-auto">
          <Button onClick={onClose} className="mb-6 bg-gray-100 hover:bg-gray-200 text-gray-900">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Chart
          </Button>
          <div className="text-center py-12">
            <AlertCircle className="h-16 w-16 text-orange-500 mx-auto mb-4" />
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">No Credit Spread Opportunities Found</h2>
            <p className="text-gray-600">{data.message || "No viable opportunities within safety criteria"}</p>
          </div>
        </div>
      </div>
    );
  }

  // Handle both data formats: API response and saved data
  let current_stock_price, market_context, spread_analysis, netCredit, maxRisk, roiPercent, bufferRoom, profitScenarios;

  if (isSavedData) {
    // Use saved data format - handle both nested and direct formats
    const spreadData = data.spreadData 
      ? (typeof data.spreadData === 'string' ? JSON.parse(data.spreadData) : data.spreadData)
      : data;
    
    current_stock_price = spreadData.currentPrice || 0;
    netCredit = spreadData.netCredit;
    maxRisk = spreadData.maxRisk;
    roiPercent = spreadData.roi;
    bufferRoom = spreadData.bufferRoom;
    
    // Create spread_analysis object from saved data
    const savedContractType = spreadData.contractType || 'call'; // Use saved contract type
    const contractSymbol = savedContractType === 'put' ? 'P' : 'C';
    
    spread_analysis = {
      sell_strike: spreadData.shortStrike,
      buy_strike: spreadData.longStrike,
      net_credit: spreadData.netCredit,
      max_risk: spreadData.maxRisk,
      roi_percent: spreadData.roi,
      expiration: spreadData.expiration,
      dte: spreadData.daysToExpiration,
      breakeven: spreadData.breakeven,
      spread_type: `${savedContractType}_credit`, // FIXED: Use saved contract type
      sell_mid_price: spreadData.netCredit / 2,
      buy_mid_price: spreadData.netCredit / 2,
      spread_width: spreadData.shortStrike - spreadData.longStrike,
      max_profit: spreadData.netCredit,
      buy_contract_symbol: `${spreadData.ticker} ${spreadData.expiration} ${spreadData.longStrike}${contractSymbol}`, // FIXED: Use correct symbol
      sell_contract_symbol: `${spreadData.ticker} ${spreadData.expiration} ${spreadData.shortStrike}${contractSymbol}`, // FIXED: Use correct symbol
      buy_bid: spreadData.netCredit / 4,
      buy_ask: spreadData.netCredit / 3,
      sell_bid: spreadData.netCredit / 3,
      sell_ask: spreadData.netCredit / 2
    };
    
    // Convert saved scenarios to expected format
    profitScenarios = (spreadData.scenarios || []).map((scenario: any) => ({
      change: scenario.priceChange,
      stockPrice: scenario.newPrice,
      profitLoss: scenario.profit,
      profitLossPercent: scenario.profitPercent
    }));
  } else {
    // Use API response format
    current_stock_price = data.current_stock_price;
    market_context = data.market_context;
    spread_analysis = data.spread_analysis;
    netCredit = spread_analysis.net_credit;
    maxRisk = spread_analysis.max_risk;
    roiPercent = spread_analysis.roi_percent;
    
    // Calculate Buffer Room: (Breakeven / Current Price - 1) * 100%
    bufferRoom = ((spread_analysis.breakeven / current_stock_price - 1) * 100);

    // Use actual price scenarios from API response
    const scenarioOrder = ['-10%', '-5%', '-2.5%', '-1%', '+0%', '+1%', '+2.5%', '+5%', '+10%'];
    profitScenarios = scenarioOrder
      .map(key => {
        const scenarioData = spread_analysis.price_scenarios[key];
        if (scenarioData) {
          return {
            change: key === '+0%' ? '0%' : key,
            stockPrice: scenarioData.stock_price,
            profitLoss: scenarioData.profit_loss,
            profitLossPercent: scenarioData.profit_loss_percent
          };
        }
        return null;
      })
      .filter((scenario): scenario is NonNullable<typeof scenario> => scenario !== null);
  }

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <Button onClick={onClose} className="bg-gray-100 hover:bg-gray-200 text-gray-900 border border-gray-300">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Chart
          </Button>
          <div className="text-center">
            <h1 className="text-5xl font-bold text-gray-900">{(isSavedData ? (data.spreadData ? (typeof data.spreadData === 'string' ? JSON.parse(data.spreadData).ticker : data.spreadData.ticker) : data.ticker) : data.ticker) || data.symbol} Credit Spread Analysis</h1>
          </div>
          <div className="flex items-center space-x-4">
            <div className="text-right">
              <div className="text-lg text-gray-600 mb-1">CURRENT PRICE</div>
              <div className="text-4xl font-bold text-green-600">${current_stock_price.toFixed(2)}</div>
            </div>
            {!hideClaimButton && !isSavedData && (
              <Button 
                onClick={handleClaim}
                disabled={isClaiming}
                className="bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg font-medium"
              >
                <Bookmark className="h-4 w-4 mr-2" />
                {isClaiming ? 'Claiming...' : 'Claim'}
              </Button>
            )}
          </div>
        </div>

        {/* Top Four Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-4">
          {/* EXPIRATION Card */}
          <Card className="bg-white border border-gray-200 shadow-sm">
            <CardContent className="p-4 text-center">
              <div className="text-lg text-gray-600 mb-2 font-semibold">EXPIRATION</div>
              <div className="text-3xl font-bold text-gray-900">
                {spread_analysis.expiration}
              </div>
            </CardContent>
          </Card>

          {/* TRADE CONSTRUCTION Card */}
          <Card className="bg-white border border-gray-200 shadow-sm">
            <CardContent className="p-4">
              <div className="text-lg text-gray-600 mb-2 font-semibold">Trade Construction</div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-lg text-red-600 font-bold">SELL</span>
                  <span className="text-lg font-bold">${spread_analysis.sell_strike} {spread_analysis.spread_type?.includes('put') ? 'Put' : 'Call'}</span>
                </div>
                <div className="text-right text-base text-gray-600">Mid: ${spread_analysis.sell_mid_price?.toFixed(2)}</div>
                <div className="flex justify-between">
                  <span className="text-lg text-green-600 font-bold">BUY</span>
                  <span className="text-lg font-bold">${spread_analysis.buy_strike} {spread_analysis.spread_type?.includes('put') ? 'Put' : 'Call'}</span>
                </div>
                <div className="text-right text-base text-gray-600">Mid: ${spread_analysis.buy_mid_price?.toFixed(2)}</div>
              </div>
            </CardContent>
          </Card>

          {/* OPTION DETAILS Card */}
          <Card className="bg-white border border-gray-200 shadow-sm">
            <CardContent className="p-4">
              <div className="text-lg text-gray-600 mb-2 font-semibold">Option Details</div>
              <div className="space-y-2">
                <div className="text-base text-gray-500 font-semibold">Short Contract:</div>
                <div className="text-sm font-mono truncate">{spread_analysis.sell_contract_symbol || spread_analysis.sell_contract || 'N/A'}</div>
                <div className="text-base text-gray-500 font-semibold">Long Contract:</div>
                <div className="text-sm font-mono truncate">{spread_analysis.buy_contract_symbol || spread_analysis.buy_contract || 'N/A'}</div>
              </div>
            </CardContent>
          </Card>

          {/* SPREAD DETAILS Card */}
          <Card className="bg-white border border-gray-200 shadow-sm">
            <CardContent className="p-4">
              <div className="text-lg text-gray-600 mb-2 font-semibold">Spread Details</div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-lg font-bold">Net Credit:</span>
                  <span className="text-lg font-bold text-green-600">${netCredit?.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-base">Max Risk:</span>
                  <span className="text-base font-semibold text-red-600">${maxRisk?.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-base">DTE:</span>
                  <span className="text-base font-semibold">{spread_analysis.dte} days</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-base">Strategy:</span>
                  <span className="text-base font-semibold">{spread_analysis.spread_type?.replace('_', ' ')}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Trade Summary Bar */}
        <div className="mb-4">
          <div className="text-xl text-gray-600 mb-3 font-semibold">Trade Summary</div>
          <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
            <div className="text-center">
              <div className="text-sm text-gray-600 font-semibold">CURRENT STOCK PRICE</div>
              <div className="text-xl font-bold text-gray-900">${current_stock_price.toFixed(2)}</div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-600 font-semibold">BREAKEVEN PRICE</div>
              <div className="text-xl font-bold text-gray-900">${spread_analysis.breakeven.toFixed(2)}</div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-600 font-semibold">DISTANCE TO BREAKEVEN</div>
              <div className="text-xl font-bold text-gray-900">${(current_stock_price - spread_analysis.breakeven).toFixed(2)}</div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-600 font-semibold">BUFFER ROOM</div>
              <div className="text-xl font-bold text-gray-900">{bufferRoom.toFixed(1)}%</div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-600 font-semibold">DAYS TIL EXPIRATION</div>
              <div className="text-xl font-bold text-gray-900">{spread_analysis.dte}</div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-600 font-semibold">RETURN ON INVESTMENT</div>
              <div className="text-xl font-bold text-green-600">{roiPercent.toFixed(1)}%</div>
            </div>
          </div>
        </div>

        {/* Chart Section */}
        <Card className="bg-white border border-gray-200 shadow-sm mb-3">
          <CardHeader className="pb-2">
            <CardTitle className="text-center text-2xl text-gray-900 font-bold">14-Day Price Chart with Profit Zones</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            {(() => {
              // 🔍 ENHANCED TICKER EXTRACTION with multiple fallbacks
              let extractedTicker = null;
              
              console.log('🔍 === TICKER EXTRACTION DEBUG START ===');
              console.log('🔍 Full data object structure:', {
                dataKeys: Object.keys(data || {}),
                isSavedData,
                hasSpreadAnalysis: !!data?.spread_analysis,
                hasMarketContext: !!data?.market_context
              });
              
              if (isSavedData) {
                // Handle saved data format
                const spreadData = data.spreadData 
                  ? (typeof data.spreadData === 'string' ? JSON.parse(data.spreadData) : data.spreadData)
                  : data;
                extractedTicker = spreadData.ticker || spreadData.symbol || data.ticker || data.symbol;
                console.log('🔍 Saved data ticker extraction:', {
                  spreadDataTicker: spreadData.ticker,
                  spreadDataSymbol: spreadData.symbol,
                  dataTicker: data.ticker,
                  dataSymbol: data.symbol,
                  result: extractedTicker
                });
              } else {
                // Handle API response format - try multiple extraction methods
                console.log('🔍 API response data inspection:', {
                  rootTicker: data.ticker,
                  rootSymbol: data.symbol,
                  spreadAnalysis: data.spread_analysis,
                  marketContext: data.market_context
                });
                
                // Method 1: Direct from root
                extractedTicker = data.ticker || data.symbol;
                
                // Method 2: From spread analysis contract symbols
                if (!extractedTicker && data.spread_analysis) {
                  const sellContract = data.spread_analysis.sell_contract_symbol || data.spread_analysis.sell_contract;
                  const buyContract = data.spread_analysis.buy_contract_symbol || data.spread_analysis.buy_contract;
                  
                  if (sellContract && typeof sellContract === 'string') {
                    // Extract ticker from option contract symbol (e.g., "TSLA250725C00290000" -> "TSLA")
                    const match = sellContract.match(/^([A-Z]{1,5})/);
                    extractedTicker = match ? match[1] : null;
                    console.log('🔍 Extracted from sell contract:', { sellContract, extracted: extractedTicker });
                  }
                  
                  if (!extractedTicker && buyContract && typeof buyContract === 'string') {
                    const match = buyContract.match(/^([A-Z]{1,5})/);
                    extractedTicker = match ? match[1] : null;
                    console.log('🔍 Extracted from buy contract:', { buyContract, extracted: extractedTicker });
                  }
                }
                
                // Method 3: From URL parameters as last resort
                if (!extractedTicker) {
                  const urlParams = new URLSearchParams(window.location.search);
                  const pathParts = window.location.pathname.split('/');
                  // Look for ticker in URL path like /credit-spread/TSLA
                  const tickerFromPath = pathParts.find(part => part.match(/^[A-Z]{1,5}$/));
                  extractedTicker = tickerFromPath || urlParams.get('ticker') || urlParams.get('symbol');
                  console.log('🔍 Extracted from URL:', { 
                    pathname: window.location.pathname,
                    pathParts,
                    tickerFromPath,
                    urlTicker: urlParams.get('ticker'),
                    result: extractedTicker 
                  });
                }
              }
              
              console.log('🔍 FINAL TICKER EXTRACTION RESULT:', {
                extractedTicker,
                isValid: !!extractedTicker && typeof extractedTicker === 'string' && extractedTicker.trim().length > 0,
                willPassToChart: !!(extractedTicker && typeof extractedTicker === 'string' && extractedTicker.trim().length > 0)
              });
              console.log('🔍 === TICKER EXTRACTION DEBUG END ===');
              
              // Validate extracted ticker
              const isValidTicker = extractedTicker && 
                                  typeof extractedTicker === 'string' && 
                                  extractedTicker.trim().length > 0 &&
                                  extractedTicker.match(/^[A-Z]{1,5}$/i);
              
              if (!isValidTicker) {
                console.error('❌ INVALID TICKER - Chart will not load:', extractedTicker);
                return (
                  <div className="h-[500px] flex items-center justify-center bg-white rounded-lg border border-gray-200 shadow-sm">
                    <div className="text-center">
                      <p className="text-red-600 font-medium">Chart Unavailable</p>
                      <p className="text-gray-600 text-sm">Could not extract ticker symbol from data</p>
                      <p className="text-xs text-gray-400 mt-1">
                        Extracted: {JSON.stringify(extractedTicker)}
                      </p>
                      <details className="mt-2 text-xs text-gray-400">
                        <summary className="cursor-pointer">Debug Info</summary>
                        <pre className="mt-1 text-left">{JSON.stringify({
                          isSavedData,
                          hasRootTicker: !!data?.ticker,
                          hasRootSymbol: !!data?.symbol,
                          hasSpreadAnalysis: !!data?.spread_analysis,
                          urlPath: window.location.pathname
                        }, null, 2)}</pre>
                      </details>
                    </div>
                  </div>
                );
              }
              
              const cleanTicker = extractedTicker.trim().toUpperCase();
              console.log('✅ VALID TICKER - Rendering chart component:', cleanTicker);
              
              return (
                <BreakevenChart 
                  currentPrice={current_stock_price}
                  breakevenPrice={spread_analysis.breakeven}
                  scenarios={spread_analysis.price_scenarios}
                  ticker={cleanTicker}
                  trend={data.trend || (spread_analysis.spread_type?.includes('put') ? 'uptrend' : 'downtrend')}
                />
              );
            })()}
          </CardContent>
        </Card>

        {/* Income Potential Calculator */}
        <Card className="bg-white border border-gray-200 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-center text-2xl text-gray-900 font-bold">Income Potential Calculator</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-center">
              <div>
                <Label className="text-base text-gray-600 mb-2 block font-semibold">NUMBER OF CONTRACTS</Label>
                <Input
                  type="number"
                  value={contractQuantity}
                  onChange={(e) => setContractQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                  className="text-center text-xl font-bold h-12"
                  min="1"
                  max="100"
                />
              </div>
              <div>
                <div className="text-base text-gray-600 mb-2 font-semibold">TOTAL INVESTMENT</div>
                <div className="text-xl font-bold text-gray-900 bg-gray-50 p-3 rounded border">
                  ${(maxRisk * contractQuantity * 100).toFixed(2)}
                </div>
              </div>
              <div>
                <div className="text-base text-gray-600 mb-2 font-semibold">INCOME POTENTIAL</div>
                <div className="text-xl font-bold text-green-600 bg-green-50 p-3 rounded border">
                  ${(netCredit * contractQuantity * 100).toFixed(2)}
                </div>
              </div>
              <div>
                <div className="text-base text-gray-600 mb-2 font-semibold">ROI PER CONTRACT</div>
                <div className="text-xl font-bold text-green-600 bg-green-50 p-3 rounded border">
                  {roiPercent.toFixed(2)}%
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}