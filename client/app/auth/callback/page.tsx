"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AuthService } from "@/lib/auth";

export default function AuthCallbackPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      const urlParams = new URLSearchParams(window.location.search);
      const code = urlParams.get("code");
      const error = urlParams.get("error");

      if (error) {
        setError(`Authentication failed: ${error}`);
        setTimeout(() => {
          router.push("/login");
        }, 3000);
        return;
      }

      if (!code) {
        setError("No authorization code received");
        setTimeout(() => {
          router.push("/login");
        }, 3000);
        return;
      }

      try {
        const authData = await AuthService.handleOAuthCallback(code);
        
        if (authData) {
          // Check for redirect URL in session storage
          const redirectUrl = sessionStorage.getItem("auth_redirect");
          sessionStorage.removeItem("auth_redirect");
          
          // Redirect to saved URL or dashboard
          router.push(redirectUrl || "/dashboard");
        } else {
          throw new Error("Failed to authenticate");
        }
      } catch (err) {
        console.error("OAuth callback error:", err);
        setError("Authentication failed. Please try again.");
        setTimeout(() => {
          router.push("/login");
        }, 3000);
      }
    };

    handleCallback();
  }, [router]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full">
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <p className="text-red-800">{error}</p>
            <p className="text-sm text-red-600 mt-2">Redirecting to login...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Completing authentication...</p>
        </div>
      </div>
    </div>
  );
}