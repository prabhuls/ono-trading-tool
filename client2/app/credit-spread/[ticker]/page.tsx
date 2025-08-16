'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { ComprehensiveCreditSpreadDisplay } from '@/components/ComprehensiveCreditSpreadDisplay';
import { useAuth } from "@/lib/hooks/useAuth";

export default function CreditSpreadAnalysisPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [spreadData, setSpreadData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const ticker = params?.ticker as string;
  const trend = searchParams?.get('trend') || 'uptrend';

  useEffect(() => {
    if (ticker) {
      analyzeCreditSpread(ticker);
    }
  }, [ticker]);

  const analyzeCreditSpread = async (tickerSymbol: string) => {
    setLoading(true);
    setError(null);
    
    try {
      // Check BOTH storage locations for token
      const localToken = localStorage.getItem('auth_token');
      const sessionToken = sessionStorage.getItem('token');
      const token = localToken || sessionToken;
      
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      // Include token in query param as well for backend compatibility
      const url = token ? `${backendUrl}/api/v1/credit-spread/analyze-credit-spread?token=${token}` : `${backendUrl}/api/v1/credit-spread/analyze-credit-spread`;
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          ticker: tickerSymbol.toUpperCase(),
          trend: trend
        })
      });

      if (response.ok) {
        const data = await response.json();
        // Add trend information to the data
        data.trend = trend;
        setSpreadData(data);
      } else {
        try {
          const errorData = await response.json();
          
          if (response.status === 500 || 
              (errorData.error && errorData.error.includes('500'))) {
            setError(`${tickerSymbol.toUpperCase()} could not be analyzed at this moment. Please try again in a few minutes or select a different ticker.`);
          }
          else if (response.status === 404 || 
                   (errorData.error && errorData.error.includes('404'))) {
            setError(`${tickerSymbol.toUpperCase()} is not available for credit spread analysis. Please verify the ticker symbol or try a different stock.`);
          } else {
            setError(`Analysis failed: ${response.status} - ${errorData.error || errorData.details || 'Unknown error'}`);
          }
        } catch {
          const errorText = await response.text();
          if (response.status === 500) {
            setError(`${tickerSymbol.toUpperCase()} could not be analyzed at this moment. Please try again in a few minutes or select a different ticker.`);
          } else if (response.status === 404) {
            setError(`${tickerSymbol.toUpperCase()} is not available for credit spread analysis. Please verify the ticker symbol or try a different stock.`);
          } else {
            setError(`Analysis failed: ${response.status} - ${errorText}`);
          }
        }
      }
    } catch (error: any) {
      setError('Network error connecting to credit spread service. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    router.push('/');
  };

  // Check auth loading state
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
            You need to be authenticated to analyze credit spreads.
          </p>
          <div className="bg-gradient-to-r from-green-50 to-green-100 rounded-xl p-4 text-sm text-green-800 font-medium border-2 border-green-200">
            Please authenticate via One Click Trading to continue
          </div>
          <button
            onClick={handleClose}
            className="mt-6 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      {loading && (
        <div className="min-h-screen bg-white flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-500 mx-auto mb-4"></div>
            <h2 className="text-xl font-semibold text-gray-900">Analyzing Credit Spreads...</h2>
            <p className="text-gray-600">Fetching real-time market data</p>
          </div>
        </div>
      )}

      {error && (
        <div className="min-h-screen bg-white flex items-center justify-center">
          <div className="text-center max-w-md">
            <div className="text-red-500 mb-4">
              <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Analysis Error</h2>
            <p className="text-gray-600 mb-6">{error}</p>
            <button
              onClick={handleClose}
              className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              Return to Dashboard
            </button>
          </div>
        </div>
      )}

      {spreadData && (
        <div className="min-h-screen bg-gray-50">
          <ComprehensiveCreditSpreadDisplay 
            data={spreadData} 
            onClose={handleClose}
          />
        </div>
      )}
    </>
  );
}