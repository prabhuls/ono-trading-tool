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

export const useAuthContext = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuthContext must be used within an AuthProvider");
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
          console.log("Token found in URL, storing immediately...");
          // Store the token IMMEDIATELY and update ApiClient
          AuthService.setToken(tokenFromUrl);
          // Clean URL without reloading
          const newUrl = window.location.pathname;
          window.history.replaceState({}, document.title, newUrl);

          // Set loading state while verifying
          setAuthState({
            user: { sub: "verifying" } as User,
            isAuthenticated: false,
            isLoading: true,
            token: tokenFromUrl,
          });
        }

        const token = AuthService.getToken();
        if (token) {
          console.log("Verifying token with backend...");
          // Verify token with backend
          const isValid = await AuthService.verifyToken();
          if (isValid) {
            // Get stored user from AuthService (set during verification)
            const user = AuthService.getStoredUser();
            if (user) {
              console.log("Token verified, user authenticated");
              setAuthState({
                user,
                isAuthenticated: true,
                isLoading: false,
                token,
              });
            } else {
              console.log("Token valid but no user data");
              setAuthState({
                user: null,
                isAuthenticated: false,
                isLoading: false,
                token: null,
              });
            }
          } else {
            // Invalid token
            console.log("Token verification failed");
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
          console.log("No token found");
          setAuthState({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            token: null,
          });
        }
      } catch (error) {
        console.error("Auth initialization error:", error);
        // On error, check if we at least have a token for fallback auth
        const token = AuthService.getToken();
        if (token) {
          console.log("Network error but token exists, keeping authenticated");
          setAuthState({
            user: { sub: "cached", user_id: "cached" } as User,
            isAuthenticated: true,
            isLoading: false,
            token,
          });
        } else {
          setAuthState({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            token: null,
          });
        }
      }
    };

    initAuth();
  }, []);

  const setToken = useCallback((token: string) => {
    AuthService.setExternalToken(token);
    
    // Verify token and get user info from backend
    AuthService.verifyToken().then(isValid => {
      if (isValid) {
        const user = AuthService.getStoredUser();
        if (user) {
          setAuthState({
            user,
            isAuthenticated: true,
            isLoading: false,
            token,
          });
        }
      }
    });
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
        const user = AuthService.getStoredUser();
        if (user) {
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
    const { isAuthenticated, isLoading, checkSubscription } = useAuthContext();
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