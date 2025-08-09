"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { AuthService, User, AuthState } from "@/lib/auth";

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  subscriptions: Record<string, boolean | unknown>;
  setToken: (token: string) => void;
  checkSubscription: (subscriptionName: string) => boolean;
  refreshAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
    token: null,
  });
  const router = useRouter();

  // Initialize auth on mount
  useEffect(() => {
    const initAuth = async () => {
      try {
        // Check if token is in URL (from One Click Trading)
        const urlParams = new URLSearchParams(window.location.search);
        const tokenFromUrl = urlParams.get("token");
        
        if (tokenFromUrl) {
          // Store the token and clean URL
          AuthService.setToken(tokenFromUrl);
          const newUrl = window.location.pathname;
          window.history.replaceState({}, document.title, newUrl);
        }
        
        const token = AuthService.getToken();
        if (token) {
          // Verify token with backend
          const isValid = await AuthService.verifyToken();
          if (isValid) {
            // Decode token to get user info
            const payload = AuthService.decodeToken(token);
            if (payload) {
              const user: User = {
                id: (payload.sub as string) || (payload.user_id as string) || "unknown",
                email: (payload.email as string) || "unknown@example.com",
                username: payload.username as string | undefined,
                full_name: payload.full_name as string | undefined,
                is_active: payload.is_active !== false,
                is_verified: true,
                subscriptions: (payload.subscriptions as Record<string, boolean | unknown>) || {},
                created_at: new Date().toISOString(),
              };
              
              AuthService.setStoredUser(user);
              setAuthState({
                user,
                isAuthenticated: true,
                isLoading: false,
                token,
              });
            }
          } else {
            // Invalid token
            AuthService.clearAuth();
            setAuthState({
              user: null,
              isAuthenticated: false,
              isLoading: false,
              token: null,
            });
          }
        } else {
          // No token
          setAuthState({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            token: null,
          });
        }
      } catch (error) {
        console.error("Auth initialization error:", error);
        setAuthState({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          token: null,
        });
      }
    };

    initAuth();
  }, []);

  const setToken = useCallback((token: string) => {
    AuthService.setExternalToken(token);
    
    // Decode token to get user info
    const payload = AuthService.decodeToken(token);
    if (payload) {
      const user: User = {
        id: (payload.sub as string) || (payload.user_id as string) || "unknown",
        email: (payload.email as string) || "unknown@example.com",
        username: payload.username as string | undefined,
        full_name: payload.full_name as string | undefined,
        is_active: payload.is_active !== false,
        is_verified: true,
        subscriptions: (payload.subscriptions as Record<string, boolean | unknown>) || {},
        created_at: new Date().toISOString(),
      };
      
      AuthService.setStoredUser(user);
      setAuthState({
        user,
        isAuthenticated: true,
        isLoading: false,
        token,
      });
    }
  }, []);


  const checkSubscription = useCallback((subscriptionName: string): boolean => {
    if (!authState.user) return false;
    const subscriptions = authState.user.subscriptions || {};
    return subscriptions[subscriptionName] === true;
  }, [authState.user]);

  const refreshAuth = useCallback(async () => {
    const token = AuthService.getToken();
    if (!token) {
      setAuthState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        token: null,
      });
      return;
    }

    try {
      const isValid = await AuthService.verifyToken();
      if (isValid) {
        const payload = AuthService.decodeToken(token);
        if (payload) {
          const user: User = {
            id: (payload.sub as string) || (payload.user_id as string) || "unknown",
            email: (payload.email as string) || "unknown@example.com",
            username: payload.username as string | undefined,
            full_name: payload.full_name as string | undefined,
            is_active: payload.is_active !== false,
            is_verified: true,
            subscriptions: (payload.subscriptions as Record<string, boolean | unknown>) || {},
            created_at: new Date().toISOString(),
          };
          
          AuthService.setStoredUser(user);
          setAuthState({
            user,
            isAuthenticated: true,
            isLoading: false,
            token,
          });
        }
      } else {
        AuthService.clearAuth();
        setAuthState({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          token: null,
        });
      }
    } catch (error) {
      console.error("Auth refresh error:", error);
      AuthService.clearAuth();
      setAuthState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        token: null,
      });
    }
  }, []);

  const value: AuthContextType = {
    user: authState.user,
    isAuthenticated: authState.isAuthenticated,
    isLoading: authState.isLoading,
    subscriptions: authState.user?.subscriptions || {},
    setToken,
    checkSubscription,
    refreshAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Higher-order component for protecting pages
export function withAuth<P extends object>(
  Component: React.ComponentType<P>,
  options?: {
    requiredSubscription?: string;
    redirectTo?: string;
  }
) {
  return function AuthenticatedComponent(props: P) {
    const { isAuthenticated, isLoading, checkSubscription } = useAuth();
    const router = useRouter();

    useEffect(() => {
      if (!isLoading) {
        if (!isAuthenticated) {
          router.push(options?.redirectTo || "/login");
        } else if (options?.requiredSubscription && !checkSubscription(options.requiredSubscription)) {
          router.push("/subscription-required");
        }
      }
    }, [isAuthenticated, isLoading, checkSubscription, router]);

    if (isLoading) {
      return <div>Loading...</div>;
    }

    if (!isAuthenticated) {
      return null;
    }

    if (options?.requiredSubscription && !checkSubscription(options.requiredSubscription)) {
      return null;
    }

    return <Component {...props} />;
  };
}