'use client';

import { useState, useEffect } from 'react';

interface User {
  sub: string;
  user_id?: string;
  subscriptions?: any;
  exp?: number;
  iat?: number;
  is_active?: boolean;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  token: string | null;
}

export function useAuth(): AuthState {
  const [authState, setAuthState] = useState<AuthState>(() => {
    // Check BOTH localStorage and sessionStorage synchronously on initial render
    if (typeof window !== 'undefined') {
      const localToken = localStorage.getItem('auth_token');
      const sessionToken = sessionStorage.getItem('token');
      const token = localToken || sessionToken;
      
      if (token) {
        console.log('Token found in storage on init, assuming authenticated');
        // If we have a token, assume authenticated initially
        // Will verify async in useEffect
        return {
          user: { sub: 'verifying' },
          isAuthenticated: true,
          isLoading: true,
          token,
        };
      }
    }
    
    return {
      user: null,
      isAuthenticated: false,
      isLoading: true,
      token: null,
    };
  });

  useEffect(() => {
    let mounted = true;

    const checkAuthentication = async () => {
      try {
        // Check for token in URL params first
        const urlParams = new URLSearchParams(window.location.search);
        const tokenFromUrl = urlParams.get('token');
        
        let token = tokenFromUrl;
        
        // If token in URL, store it in BOTH places and clean URL
        if (tokenFromUrl) {
          console.log('Token found in URL, storing in both localStorage and sessionStorage...');
          localStorage.setItem('auth_token', tokenFromUrl);
          sessionStorage.setItem('token', tokenFromUrl);
          // Clean the URL without reloading
          const newUrl = window.location.pathname;
          window.history.replaceState({}, '', newUrl);
          token = tokenFromUrl;
        } else {
          // Check BOTH storage locations for existing token
          const localToken = localStorage.getItem('auth_token');
          const sessionToken = sessionStorage.getItem('token');
          token = localToken || sessionToken;
          
          console.log('Token from storage:', token ? 'found' : 'not found');
          console.log('localStorage has:', localToken ? 'token' : 'no token');
          console.log('sessionStorage has:', sessionToken ? 'token' : 'no token');
          
          // Sync tokens if one is missing
          if (token) {
            if (!localToken) {
              localStorage.setItem('auth_token', token);
            }
            if (!sessionToken) {
              sessionStorage.setItem('token', token);
            }
          }
        }

        if (!token) {
          console.log('No token found anywhere, setting unauthenticated');
          if (mounted) {
            setAuthState({
              user: null,
              isAuthenticated: false,
              isLoading: false,
              token: null,
            });
          }
          return;
        }

        console.log('Verifying token with backend...');
        // Verify token with backend
        const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${backendUrl}/api/v1/auth/verify`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const userData = await response.json();
          console.log('Token verified successfully:', userData);
          
          // Store token in both places for redundancy
          localStorage.setItem('auth_token', token);
          sessionStorage.setItem('token', token);
          
          if (mounted) {
            setAuthState({
              user: userData.user || userData,
              isAuthenticated: true,
              isLoading: false,
              token,
            });
          }
        } else {
          console.log('Token verification failed:', response.status);
          // Token invalid, remove from BOTH storages
          localStorage.removeItem('auth_token');
          sessionStorage.removeItem('token');
          
          if (mounted) {
            setAuthState({
              user: null,
              isAuthenticated: false,
              isLoading: false,
              token: null,
            });
          }
        }
      } catch (error) {
        console.error('Authentication check failed:', error);
        // On network error, if we have a token, keep authenticated
        const localToken = localStorage.getItem('auth_token');
        const sessionToken = sessionStorage.getItem('token');
        const token = localToken || sessionToken;
        
        if (token && mounted) {
          console.log('Network error but token exists, keeping authenticated');
          setAuthState({
            user: { sub: 'cached', user_id: 'cached' },
            isAuthenticated: true,
            isLoading: false,
            token,
          });
        } else if (mounted) {
          setAuthState({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            token: null,
          });
        }
      }
    };

    checkAuthentication();

    return () => {
      mounted = false;
    };
  }, []); // Only run once on mount

  return authState;
}