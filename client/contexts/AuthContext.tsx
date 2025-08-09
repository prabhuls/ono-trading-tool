"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { AuthService, User, AuthState } from "@/lib/auth";
import { ApiClient } from "@/lib/api";

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  subscriptions: Record<string, boolean | unknown>;
  login: () => void;
  logout: () => Promise<void>;
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
        const token = AuthService.getToken();
        if (token) {
          // Verify token with backend
          const isValid = await AuthService.verifyToken();
          if (isValid) {
            const user = await AuthService.getCurrentUser();
            if (user) {
              setAuthState({
                user,
                isAuthenticated: true,
                isLoading: false,
                token,
              });
            } else {
              // Token is valid but couldn't get user
              AuthService.clearAuth();
              setAuthState({
                user: null,
                isAuthenticated: false,
                isLoading: false,
                token: null,
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

  // Handle OAuth callback
  useEffect(() => {
    const handleCallback = async () => {
      // Check if we're on the callback page
      if (typeof window !== "undefined" && window.location.pathname === "/auth/callback") {
        const urlParams = new URLSearchParams(window.location.search);
        const code = urlParams.get("code");
        
        if (code) {
          try {
            const authData = await AuthService.handleOAuthCallback(code);
            if (authData) {
              setAuthState({
                user: authData.user,
                isAuthenticated: true,
                isLoading: false,
                token: authData.access_token,
              });
              
              // Redirect to dashboard or home
              router.push("/dashboard");
            }
          } catch (error) {
            console.error("OAuth callback error:", error);
            router.push("/login?error=auth_failed");
          }
        }
      }
    };

    handleCallback();
  }, [router]);

  const login = useCallback(() => {
    AuthService.initiateLogin();
  }, []);

  const logout = useCallback(async () => {
    try {
      await AuthService.logout();
      setAuthState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        token: null,
      });
      router.push("/");
    } catch (error) {
      console.error("Logout error:", error);
    }
  }, [router]);

  const checkSubscription = useCallback((subscriptionName: string): boolean => {
    if (!authState.user?.subscriptions) return false;
    return authState.user.subscriptions[subscriptionName] === true;
  }, [authState.user]);

  const refreshAuth = useCallback(async () => {
    try {
      setAuthState(prev => ({ ...prev, isLoading: true }));
      
      const isValid = await AuthService.verifyToken();
      if (isValid) {
        const user = await AuthService.getCurrentUser();
        if (user) {
          setAuthState({
            user,
            isAuthenticated: true,
            isLoading: false,
            token: AuthService.getToken(),
          });
        } else {
          throw new Error("Failed to get user");
        }
      } else {
        throw new Error("Token invalid");
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
    login,
    logout,
    checkSubscription,
    refreshAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Higher-order component for protecting pages
export function withAuth<P extends object>(
  Component: React.ComponentType<P>,
  options?: {
    redirectTo?: string;
    requiredSubscription?: string;
  }
): React.ComponentType<P> {
  return function AuthenticatedComponent(props: P) {
    const { isAuthenticated, isLoading, checkSubscription } = useAuth();
    const router = useRouter();

    useEffect(() => {
      if (!isLoading && !isAuthenticated) {
        router.push(options?.redirectTo || "/login");
      }

      if (!isLoading && isAuthenticated && options?.requiredSubscription) {
        if (!checkSubscription(options.requiredSubscription)) {
          router.push("/subscription-required");
        }
      }
    }, [isAuthenticated, isLoading, router]);

    if (isLoading) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      );
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