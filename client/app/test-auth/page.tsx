"use client";

import { useEffect, useState } from "react";
import { useAuthContext } from "@/contexts/AuthContext";
import { AuthService } from "@/lib/auth";

export default function TestAuthPage() {
  const { user, isAuthenticated, isLoading } = useAuthContext();
  const [tokenInfo, setTokenInfo] = useState<any>(null);
  const [verifyResult, setVerifyResult] = useState<any>(null);

  useEffect(() => {
    // Get and decode token
    const token = AuthService.getToken();
    if (token) {
      const decoded = AuthService.decodeToken(token);
      setTokenInfo({
        token: token.substring(0, 50) + "...",
        decoded: decoded,
        isExpired: AuthService.isTokenExpired(token)
      });
    }
  }, []);

  const handleVerifyToken = async () => {
    try {
      const response = await fetch("/api/v1/auth/verify", {
        headers: {
          "Authorization": `Bearer ${AuthService.getToken()}`
        }
      });
      const data = await response.json();
      setVerifyResult(data);
    } catch (error) {
      setVerifyResult({ error: String(error) });
    }
  };

  const handleTestToken = () => {
    // Add the real JWT to URL and reload
    const testToken = "eyJ0eXAiOiJKV1QiLCJraWQiOiJvY3QtZXh0ZXJuYWwiLCJhbGciOiJSUzI1NiJ9.eyJzdWJzY3JpcHRpb25zIjp7IkZJTk1DIjpbIkxJUyIsIklOQ1YiLCJJTkMiLCJQT1MiXX0sInN1YiI6ImRiY2JlYjlmLWNkNmQtNDc2MC04Mjc3LWUyNjEzYTg3NDAzNSIsImlhdCI6MTc1NTI2MTE0MSwiZXhwIjoxNzU3NjgwMzQxfQ.bApZZUmuVf1cwfWG0ny_EYKuJdyutKY1Gpm9pgiESRnN9RrghF-rozBrTiSPk0inMXUOCR_k0i1yCb_ldXD0kF8gYD6cvpEOnaf7wWfy0-t334O0AqNQMIUkRgZ7-BIL7Ds7XTy9e_kSJdTt6F5pRIsfbMJN6P4JXHsamvDcQe0tjoj_KyXFjaFuIaDNFxXev8K-c15O_SQLXh7Bi0f_x9kF_agYykcyxTJOP_6r_oUQLTl29Wfq-ITI06haDFDIUaynptXzO-WXP6vOZEDDdhaZ4-sGIa6sLbvVVcR-ozb89t-98M4EZLDNyJY1EpWdAHV0qKxj31cdsbPlHf_13Q";
    window.location.href = `?token=${testToken}`;
  };

  if (isLoading) {
    return <div className="p-8">Loading auth...</div>;
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-8">Authentication Test Page</h1>
      
      <div className="space-y-6">
        {/* Auth Status */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Auth Status</h2>
          <div className="space-y-2">
            <p><strong>Is Authenticated:</strong> {isAuthenticated ? "✅ Yes" : "❌ No"}</p>
            <p><strong>Is Loading:</strong> {isLoading ? "Yes" : "No"}</p>
          </div>
        </div>

        {/* User Info */}
        {user && (
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">User Info</h2>
            <pre className="bg-gray-50 p-4 rounded overflow-x-auto">
              {JSON.stringify(user, null, 2)}
            </pre>
          </div>
        )}

        {/* Token Info */}
        {tokenInfo && (
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Token Info</h2>
            <div className="space-y-2">
              <p><strong>Token (truncated):</strong> {tokenInfo.token}</p>
              <p><strong>Is Expired:</strong> {tokenInfo.isExpired ? "❌ Yes" : "✅ No"}</p>
              <div>
                <strong>Decoded Payload:</strong>
                <pre className="bg-gray-50 p-4 rounded mt-2 overflow-x-auto">
                  {JSON.stringify(tokenInfo.decoded, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        )}

        {/* Verify Result */}
        {verifyResult && (
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Verify API Result</h2>
            <pre className="bg-gray-50 p-4 rounded overflow-x-auto">
              {JSON.stringify(verifyResult, null, 2)}
            </pre>
          </div>
        )}

        {/* Actions */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Actions</h2>
          <div className="space-x-4">
            <button 
              onClick={handleTestToken}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              Simulate OCT Redirect (Add Token to URL)
            </button>
            <button 
              onClick={handleVerifyToken}
              className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
            >
              Verify Token with Backend
            </button>
            <button 
              onClick={() => {
                AuthService.clearAuth();
                window.location.reload();
              }}
              className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
            >
              Clear Auth & Reload
            </button>
          </div>
        </div>

        {/* Instructions */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">How OCT Authentication Works</h2>
          <ol className="list-decimal list-inside space-y-2">
            <li>User arrives from OCT with JWT token in URL: <code>/?token=JWT_TOKEN</code></li>
            <li>Frontend extracts token from URL and stores in localStorage</li>
            <li>Frontend verifies token with backend <code>/api/v1/auth/verify</code> endpoint</li>
            <li>Backend validates JWT signature using OCT public key</li>
            <li>User info (sub, subscriptions) is extracted and stored</li>
            <li>Token is automatically added to all API requests as Bearer token</li>
          </ol>
        </div>
      </div>
    </div>
  );
}