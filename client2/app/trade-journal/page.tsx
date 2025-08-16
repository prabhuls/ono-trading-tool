"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { format } from "date-fns";
import { ArrowLeft, Trash2 } from "lucide-react";
import { ComprehensiveCreditSpreadDisplay } from "@/components/ComprehensiveCreditSpreadDisplay";
import { useToast } from "@/lib/hooks/use-toast";
import { useAuth } from "@/lib/hooks/useAuth";
import { useRouter } from "next/navigation";

interface SavedCreditSpread {
  id: number;
  symbol: string;
  spreadData: string | any; // Can be JSON string or object
  claimedAt: string;
  parsedData?: {
    ticker: string;
    currentPrice?: number;
    shortStrike: number;
    longStrike: number;
    netCredit: number;
    maxRisk: number;
    roi: number;
    expiration: string;
    contractType: string;
    daysToExpiration: number;
    breakeven: number;
    bufferRoom: number;
    scenarios?: Array<{
      priceChange: string;
      newPrice: number;
      profit: number;
      profitPercent: number;
    }>;
  };
}

export default function TradeJournal() {
  const [selectedSpread, setSelectedSpread] = useState<SavedCreditSpread | null>(null);
  const [viewMode, setViewMode] = useState<'list' | 'analysis'>('list');
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0); // Force refresh trigger
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();

  // FORCE REFRESH EVERY TIME TRADE JOURNAL IS ACCESSED
  useEffect(() => {
    console.log('🔄 Trade Journal: Component mounted - FORCING FRESH DATA...');
    
    // Clear all cached data for this query
    queryClient.removeQueries({ queryKey: ['/api/credit-spread/user-claims'] });
    
    // Force immediate fresh fetch
    setRefreshTrigger(Date.now()); // Use timestamp to ensure unique trigger
    
    console.log('✅ Trade Journal: Forced refresh triggered on mount');
  }, []); // Empty dependency array = runs only on mount

  // Listen for trade updates from other components
  useEffect(() => {
    const handleTradeUpdate = (event: CustomEvent) => {
      console.log('🔄 Trade Journal: Received update event:', event.detail);
      setRefreshTrigger(prev => prev + 1); // Force component re-render
      queryClient.resetQueries({ queryKey: ['/api/credit-spread/user-claims'] });
      queryClient.refetchQueries({ queryKey: ['/api/credit-spread/user-claims'] });
    };

    window.addEventListener('tradeJournalUpdate', handleTradeUpdate as EventListener);
    
    return () => {
      window.removeEventListener('tradeJournalUpdate', handleTradeUpdate as EventListener);
    };
  }, [queryClient]);

  const { data: savedSpreads = [], isLoading, refetch } = useQuery({
    queryKey: ['/api/credit-spread/user-claims', refreshTrigger], // Include refresh trigger in key
    queryFn: async () => {
      console.log('🔄 Trade Journal: Fetching user claims... (Trigger:', refreshTrigger, ')');
      
      const localToken = localStorage.getItem('auth_token');
      const sessionToken = sessionStorage.getItem('token');
      const token = localToken || sessionToken;
      
      if (!token) {
        throw new Error('No authentication token found');
      }
      
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/api/v1/user-spreads/user-claims`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch user claims');
      }
      
      const responseData = await response.json();
      console.log('✅ Trade Journal: Received data:', responseData);
      
      // API returns { claims: [...] }, so extract the claims array
      const claimsArray = responseData.claims || [];
      
      // Process each spread - spreadData might be string or object
      const processedData = claimsArray.map((spread: any) => {
        // Parse spreadData if it's a string, otherwise use as-is
        let parsedData;
        if (typeof spread.spreadData === 'string') {
          try {
            parsedData = JSON.parse(spread.spreadData);
          } catch (e) {
            console.error('Failed to parse spreadData:', e);
            parsedData = {};
          }
        } else {
          parsedData = spread.spreadData || {};
        }
        
        return {
          ...spread,
          parsedData
        };
      });
      
      console.log('📊 Trade Journal: Processed data:', processedData.length, 'trades');
      return processedData;
    },
    enabled: refreshTrigger > 0 && isAuthenticated, // Only run query when trigger is set and authenticated
    refetchOnWindowFocus: true,
    refetchOnMount: true,
    staleTime: 0, // Always refetch when invalidated
    gcTime: 0, // Don't cache stale data (was cacheTime in v4)
    refetchInterval: false, // Don't auto-refetch
  });

  // Simplified delete mutation with forced refresh
  const deleteMutation = useMutation({
    mutationFn: async (spreadId: number) => {
      const localToken = localStorage.getItem('auth_token');
      const sessionToken = sessionStorage.getItem('token');
      const token = localToken || sessionToken;
      
      if (!token) {
        throw new Error('No authentication token found');
      }
      
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/api/v1/user-spreads/${spreadId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to delete credit spread');
      }
      
      return response.json();
    },
    onSuccess: async (data, spreadId) => {
      console.log('🗑️ DELETE SUCCESS - Forcing immediate refresh...', spreadId);
      
      toast({
        title: "Trade Deleted",
        description: "Credit spread removed from your journal",
      });
      
      // NUCLEAR OPTION: Force immediate refresh
      setRefreshTrigger(prev => prev + 1); // Force re-render
      await queryClient.resetQueries({ queryKey: ['/api/credit-spread/user-claims'] });
      await queryClient.refetchQueries({ queryKey: ['/api/credit-spread/user-claims'] });
      
      // Trigger window event
      window.dispatchEvent(new CustomEvent('tradeJournalUpdate', { 
        detail: { action: 'delete', spreadId, timestamp: Date.now() } 
      }));
      
      setDeletingId(null);
      console.log('✅ DELETE - Forced refresh complete');
    },
    onError: (error: Error, spreadId) => {
      console.error('❌ DELETE ERROR:', error, spreadId);
      toast({
        title: "Delete Failed",
        description: error.message || "Could not delete trade",
        variant: "destructive",
      });
      setDeletingId(null);
    },
  });

  const handleDelete = (spreadId: number, ticker: string) => {
    setDeletingId(spreadId);
    deleteMutation.mutate(spreadId);
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const formatPercentage = (value: number) => {
    return `${value.toFixed(2)}%`;
  };

  // Check auth loading state
  if (authLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Checking authentication...</p>
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
            You need to be authenticated to access the trade journal.
          </p>
          <div className="bg-gradient-to-r from-green-50 to-green-100 rounded-xl p-4 text-sm text-green-800 font-medium border-2 border-green-200">
            Please authenticate via One Click Trading to continue
          </div>
          <Button
            onClick={() => router.push('/')}
            className="mt-6 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            Return to Dashboard
          </Button>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading your trade journal...</p>
        </div>
      </div>
    );
  }

  // Show detailed analysis view as full page
  if (viewMode === 'analysis' && selectedSpread?.parsedData) {
    return (
      <div className="min-h-screen bg-white">
        {/* Header with back button */}
        <div className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setViewMode('list');
                setSelectedSpread(null);
              }}
              className="flex items-center gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Trade Journal
            </Button>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {selectedSpread.parsedData.ticker} Credit Spread Analysis
              </h1>
              <p className="text-gray-600">
                Saved on {format(new Date(selectedSpread.claimedAt), 'MMMM d, yyyy \'at\' h:mm a')}
              </p>
            </div>
          </div>
        </div>

        {/* Credit Spread Analysis Component */}
        <ComprehensiveCreditSpreadDisplay 
          data={selectedSpread.parsedData}
          onClose={() => {
            setViewMode('list');
            setSelectedSpread(null);
          }}
          hideClaimButton={true}
        />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Trade Journal</h1>
        <p className="text-gray-600">Your saved credit spread analyses and trade ideas</p>
      </div>

      {savedSpreads.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-gray-400 text-6xl mb-4">📊</div>
          <h2 className="text-2xl font-semibold text-gray-700 mb-2">No trades saved yet</h2>
          <p className="text-gray-500 mb-6">Start by analyzing stocks and claiming credit spreads to build your journal</p>
          <Button 
            onClick={() => router.push('/')}
            className="bg-green-600 hover:bg-green-700 text-white"
          >
            Explore Stocks
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          {savedSpreads.map((spread: SavedCreditSpread) => (
            <Card key={spread.id} className="hover:shadow-lg transition-shadow border-gray-200">
              <CardHeader className="pb-3">
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-3">
                    <CardTitle className="text-lg font-semibold text-gray-900">
                      {spread.parsedData?.ticker || spread.symbol}
                    </CardTitle>
                    <Badge 
                      variant={spread.parsedData?.contractType === 'put' ? 'default' : 'secondary'}
                      className="text-xs"
                    >
                      {spread.parsedData?.contractType?.toUpperCase() || 'PUT'}
                    </Badge>
                  </div>
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={deletingId === spread.id}
                        className="text-red-500 hover:text-red-700 hover:bg-red-50 p-2"
                        title="Delete this trade"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {deletingId === spread.id ? (
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-red-500"></div>
                        ) : (
                          <Trash2 className="h-4 w-4" />
                        )}
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent onClick={(e) => e.stopPropagation()}>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Delete Credit Spread</AlertDialogTitle>
                        <AlertDialogDescription>
                          Are you sure you want to delete the <strong>{spread.parsedData?.ticker || spread.symbol}</strong> credit spread from your Trade Journal?
                          <br />
                          <br />
                          This action cannot be undone and will permanently remove the trade from your records.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                          onClick={() => handleDelete(spread.id, spread.parsedData?.ticker || spread.symbol)}
                          className="bg-red-600 hover:bg-red-700 focus:ring-red-600"
                        >
                          Delete Trade
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
                <p className="text-sm text-gray-500">
                  Saved {format(new Date(spread.claimedAt), 'MMM d, yyyy')}
                </p>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="space-y-1 mb-4">
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-600">Strikes:</span>
                    <span className="font-medium">{spread.parsedData?.shortStrike}/{spread.parsedData?.longStrike}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-bold">Net Credit:</span>
                    <span className="text-sm font-bold text-green-600">{formatCurrency(spread.parsedData?.netCredit || 0)}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-600">Max Risk:</span>
                    <span className="font-medium text-red-600">{formatCurrency(spread.parsedData?.maxRisk || 0)}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-600">ROI:</span>
                    <span className="font-medium text-blue-600">{formatPercentage(spread.parsedData?.roi || 0)}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-600">DTE:</span>
                    <span className="font-medium">{spread.parsedData?.daysToExpiration || 'N/A'} days</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-600">Strategy:</span>
                    <span className="font-medium">{spread.parsedData?.contractType?.replace('_', ' ') || 'put credit'}</span>
                  </div>
                </div>
                <Button 
                  onClick={() => {
                    setSelectedSpread(spread);
                    setViewMode('analysis');
                  }}
                  className="w-full bg-gray-100 hover:bg-gray-200 text-gray-700 border border-gray-300"
                  variant="outline"
                >
                  View Analysis
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}