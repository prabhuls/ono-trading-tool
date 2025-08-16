"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/lib/hooks/useAuth";
import { ComprehensiveCreditSpreadDisplay } from './ComprehensiveCreditSpreadDisplay';

interface TodaysMover {
  id: number;
  symbol: string;
  name?: string;
  moverType: 'uptrend' | 'downtrend';
  currentPrice?: number;
  priceChange?: number;
  priceChangePercent?: number;
  volume?: number;
  specialCharacter?: string;
  lastUpdated?: string;
  calculatedAt?: string;
  hasEarnings?: boolean;  // Indicates if stock has upcoming earnings
  hasWeeklies?: boolean;
  hasSpreads?: boolean;
}

interface CreditSpreadData {
  current_stock_price: number;
  market_context: {
    analysis_time: string;
    api_calls_used: number;
    data_source: string;
    safety_first_approach: boolean;
  };
  spread_analysis: {
    breakeven: number;
    buy_ask: number;
    buy_bid: number;
    buy_contract_symbol: string;
    buy_mid_price: number;
    buy_strike: number;
    dte: number;
    expiration: string;
    found: boolean;
    max_profit: number;
    max_profit_details: any;
    roi_percentage: number;
    sell_ask: number;
    sell_bid: number;
    sell_contract_symbol: string;
    sell_mid_price: number;
    sell_strike: number;
    strategy_type: string;
  };
}

export function TodaysMoversCards() {
  const { isAuthenticated, isLoading: authLoading, token: authToken } = useAuth();
  const [randomStocks, setRandomStocks] = useState<TodaysMover[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showChart, setShowChart] = useState(false);
  const [selectedStock, setSelectedStock] = useState<TodaysMover | null>(null);
  const [showCreditSpread, setShowCreditSpread] = useState(false);
  const [showDetailedSpread, setShowDetailedSpread] = useState(false);
  const [creditSpreadData, setCreditSpreadData] = useState<CreditSpreadData | null>(null);
  const [analyzingSpread, setAnalyzingSpread] = useState(false);
  const router = useRouter();

  // Search state
  const [searchTicker, setSearchTicker] = useState("");

  // Utility function to format timestamp in user's timezone
  const formatLastUpdated = (timestamp?: string) => {
    if (!timestamp) return "Unknown";
    
    try {
      const date = new Date(timestamp);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMinutes = Math.floor(diffMs / (1000 * 60));
      const diffHours = Math.floor(diffMinutes / 60);
      
      if (diffMinutes < 1) {
        return "Just now";
      } else if (diffMinutes < 60) {
        return `${diffMinutes}m ago`;
      } else if (diffHours < 24) {
        return `${diffHours}h ago`;
      } else {
        // Format as local time for older data
        return date.toLocaleString(undefined, {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
          timeZoneName: 'short'
        });
      }
    } catch (error) {
      return "Invalid date";
    }
  };

  useEffect(() => {
    const fetchRandomStocks = async () => {
      try {
        // Check BOTH storage locations for token
        const localToken = localStorage.getItem('auth_token');
        const sessionToken = sessionStorage.getItem('token');
        const token = localToken || sessionToken || authToken;
        
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        // Include token in both query param and header for compatibility
        const url = token ? `${backendUrl}/api/v1/market/todays-movers?token=${token}` : `${backendUrl}/api/v1/market/todays-movers`;
        const response = await fetch(url, {
          headers: {
            'Authorization': `Bearer ${token}`,
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          console.log('Today\'s Movers API Response:', data);
          
          if (data.stocks && Array.isArray(data.stocks)) {
            setRandomStocks(data.stocks);
          } else {
            console.warn('No stocks array found in response:', data);
            setRandomStocks([]);
          }
        } else {
          console.error('Failed to fetch today\'s movers:', response.status);
          setRandomStocks([]);
        }
      } catch (error) {
        console.error('Error fetching today\'s movers:', error);
        setRandomStocks([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchRandomStocks();
  }, []);

  const handleCardClick = (stock: TodaysMover) => {
    // Navigate directly to credit spread analysis page
    router.push(`/credit-spread/${stock.symbol}?trend=${stock.moverType}`);
  };

  const handleSearchFind = () => {
    if (!searchTicker.trim()) return;
    
    // Clean up ticker input (remove spaces - already uppercase from input)
    const cleanTicker = searchTicker.trim();
    
    // Navigate to credit spread analysis with UPTREND as default
    router.push(`/credit-spread/${cleanTicker}?trend=uptrend`);
  };

  const handleSearchKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearchFind();
    }
  };

  // Show auth loading state
  if (authLoading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-500 mx-auto mb-4"></div>
          <p className="text-xl text-gray-900">Checking authentication...</p>
        </div>
      </div>
    );
  }

  // Show access restricted if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-white to-gray-50 flex items-center justify-center">
        <div className="bg-white border-vip-thick border-gray-200 rounded-2xl p-12 max-w-md text-center shadow-premium animate-scale-in">
          <div className="text-7xl mb-6">🔒</div>
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Access Restricted</h2>
          <p className="text-gray-600 mb-6 text-lg">
            You need to be authenticated to access this trading platform.
          </p>
          <div className="bg-gradient-to-r from-green-50 to-green-100 rounded-xl p-4 text-sm text-green-800 font-medium border-2 border-green-200">
            Please authenticate via One Click Trading to continue
          </div>
        </div>
      </div>
    );
  }

  // Show loading state for data
  if (isLoading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-500 mx-auto mb-4"></div>
          <p className="text-xl text-gray-900">Loading today's market movers...</p>
        </div>
      </div>
    );
  }

  // Show friendly message when no stocks are available (not loading)
  if (!isLoading && randomStocks.length === 0) {
    return (
      <div className="min-h-screen bg-white">
        <div className="container mx-auto px-4 py-12">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold mb-4 text-gray-900">
              Today's Market Movers
            </h1>
            <p className="text-sm text-gray-500">
              No current data available
            </p>
          </div>

          {/* Search Bar Removed */}
          
          <div className="flex flex-col items-center justify-center py-12 px-8">
            <div className="bg-white border-vip-thick border-gray-200 rounded-2xl p-10 max-w-md text-center shadow-premium animate-scale-in">
              <div className="text-7xl mb-6 animate-pulse">📈</div>
              <h2 className="text-3xl font-bold text-gray-900 mb-4">No Trade Opportunities</h2>
              <p className="text-gray-600 mb-4 text-lg">There are no trade opportunities available at this moment.</p>
              <p className="text-sm text-gray-500 mb-6">
                We only show stocks with viable credit spread options during market hours.
              </p>
              <div className="bg-gradient-to-r from-green-50 to-green-100 rounded-xl p-4 text-sm text-green-800 font-medium border-2 border-green-200">
                <strong>Market Hours:</strong> 9:30 AM - 4:00 PM EST
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-gray-50">
      <div className="container mx-auto px-4 py-10">
        <div className="text-center mb-10 animate-fade-in">
          <h1 className="text-4xl font-black mb-4 text-gray-900">
            Today's Market Movers
          </h1>
          <p className="text-gray-600 text-lg mb-3 font-medium">
            Tap any stock to analyze credit spread opportunities immediately
          </p>
          {randomStocks.length > 0 && randomStocks[0]?.lastUpdated && (
            <p className="text-sm text-gray-500 font-medium">
              Data last updated: {formatLastUpdated(randomStocks[0].lastUpdated)}
            </p>
          )}
        </div>

        {/* Search Bar Removed */}

        {/* Main Cards Grid */}
        <div className="flex flex-wrap justify-center gap-6 max-w-7xl mx-auto">
          {randomStocks.map((stock, index) => (
            <Card 
              key={stock.id} 
              className="cursor-pointer transition-all duration-300 ease-out rounded-2xl bg-white border-vip-thick border-gray-200 shadow-card hover:shadow-premium hover:scale-102 hover:-translate-y-1 group w-72 flex-shrink-0 overflow-hidden animate-scale-in"
              onClick={() => handleCardClick(stock)}
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <CardHeader className="pb-4 bg-gradient-to-b from-white to-gray-50/50">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-3xl font-black text-gray-900 group-hover:text-green-600 transition-colors duration-200">
                    {stock.symbol || 'N/A'}
                  </CardTitle>
                  {stock.moverType === 'uptrend' ? (
                    <div className="w-4 h-4 bg-green-500 rounded-full shadow-green-glow pulse-green" />
                  ) : (
                    <div className="w-4 h-4 bg-red-500 rounded-full shadow-sm" />
                  )}
                </div>
              </CardHeader>
              
              <CardContent className="space-y-4 pb-6">
                <div className="text-center">
                  <div className="text-4xl font-black text-gray-900">
                    ${stock.currentPrice?.toFixed(2) || 'N/A'}
                  </div>
                </div>

                <div className={`relative overflow-hidden text-base px-6 py-3 rounded-xl text-center font-bold transition-all duration-200 ${
                  stock.moverType === 'uptrend' 
                    ? 'bg-gradient-to-r from-green-50 to-green-100 text-green-700 border-2 border-green-300 group-hover:from-green-500 group-hover:to-green-600 group-hover:text-white group-hover:border-green-600 group-hover:shadow-lg' 
                    : 'bg-gradient-to-r from-red-50 to-red-100 text-red-700 border-2 border-red-300 group-hover:from-red-500 group-hover:to-red-600 group-hover:text-white group-hover:border-red-600 group-hover:shadow-lg'
                }`}>
                  <span className="relative z-10">ANALYZE TRADE</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}