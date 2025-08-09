import { ApiClient } from "./api";

export interface User {
  id: string;
  email: string;
  username?: string;
  full_name?: string;
  is_active: boolean;
  is_verified: boolean;
  subscriptions: Record<string, boolean | unknown>;
  created_at: string;
  last_login_at?: string;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  token: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user?: User;
}

export interface TokenVerifyResponse {
  valid: boolean;
  user_id: string;
  email?: string;
  username?: string;
  subscriptions: Record<string, boolean | unknown>;
  expires_at?: number;
}

const AUTH_TOKEN_KEY = "auth_token";
const AUTH_USER_KEY = "auth_user";

export class AuthService {
  /**
   * Get stored authentication token
   */
  static getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(AUTH_TOKEN_KEY);
  }

  /**
   * Store authentication token
   */
  static setToken(token: string): void {
    if (typeof window !== "undefined") {
      localStorage.setItem(AUTH_TOKEN_KEY, token);
      ApiClient.setAuthToken(token);
    }
  }

  /**
   * Get stored user data
   */
  static getStoredUser(): User | null {
    if (typeof window === "undefined") return null;
    const userStr = localStorage.getItem(AUTH_USER_KEY);
    if (!userStr) return null;
    try {
      return JSON.parse(userStr);
    } catch {
      return null;
    }
  }

  /**
   * Store user data
   */
  static setStoredUser(user: User): void {
    if (typeof window !== "undefined") {
      localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
    }
  }

  /**
   * Clear all auth data
   */
  static clearAuth(): void {
    if (typeof window !== "undefined") {
      localStorage.removeItem(AUTH_TOKEN_KEY);
      localStorage.removeItem(AUTH_USER_KEY);
      ApiClient.clearAuth();
    }
  }

  /**
   * Set token from external source (e.g., received from parent application)
   */
  static setExternalToken(token: string): void {
    this.setToken(token);
  }

  /**
   * Verify current token
   */
  static async verifyToken(): Promise<boolean> {
    try {
      const token = this.getToken();
      if (!token) return false;
      
      const response = await ApiClient.post<TokenVerifyResponse>("/api/v1/auth/auth/verify");
      
      if (response.success && response.data?.valid) {
        return true;
      }
      
      // Token is invalid, clear auth
      this.clearAuth();
      return false;
    } catch (error) {
      console.error("Token verification error:", error);
      this.clearAuth();
      return false;
    }
  }


  /**
   * Check if user has a specific subscription
   */
  static async checkSubscription(subscriptionName: string): Promise<boolean> {
    try {
      const response = await ApiClient.get<{
        has_subscription: boolean;
        authenticated: boolean;
        subscription_data?: unknown;
      }>(`/api/v1/auth/auth/check-subscription/${subscriptionName}`);
      
      return response.data?.has_subscription || false;
    } catch (error) {
      console.error("Check subscription error:", error);
      return false;
    }
  }

  /**
   * Create a test token for development
   */
  static async createTestToken(
    userId: string = "test-user-123",
    email: string = "test@example.com",
    includeSubscriptions: boolean = true
  ): Promise<string | null> {
    if (process.env.NODE_ENV === "production") {
      console.error("Test token generation is disabled in production");
      return null;
    }
    
    try {
      const params = new URLSearchParams({
        user_id: userId,
        email: email,
        include_subscriptions: includeSubscriptions.toString(),
      });
      
      const response = await ApiClient.get<AuthResponse>(
        `/api/v1/auth/auth/dev/create-test-token?${params}`
      );
      
      if (response.success && response.data) {
        const token = response.data.access_token;
        this.setToken(token);
        
        console.log("Test token created successfully");
        return token;
      }
      
      return null;
    } catch (error) {
      console.error("Create test token error:", error);
      return null;
    }
  }

  /**
   * Handle token from URL parameters (if passed as query param)
   */
  static handleTokenFromUrl(): boolean {
    if (typeof window === "undefined") return false;
    
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get("token");
    
    if (token) {
      this.setToken(token);
      
      // Clean up URL
      const newUrl = window.location.pathname;
      window.history.replaceState({}, document.title, newUrl);
      
      return true;
    }
    
    return false;
  }

  /**
   * Decode JWT token to get payload (client-side only, no verification)
   */
  static decodeToken(token?: string): Record<string, unknown> | null {
    const tokenToUse = token || this.getToken();
    if (!tokenToUse) return null;

    try {
      const payload = JSON.parse(atob(tokenToUse.split('.')[1]));
      return payload;
    } catch {
      return null;
    }
  }

  /**
   * Check if token is expired (client-side check)
   */
  static isTokenExpired(token?: string): boolean {
    const payload = this.decodeToken(token);
    if (!payload || !payload.exp) return true;
    
    const exp = payload.exp as number;
    const now = Math.floor(Date.now() / 1000);
    return exp < now;
  }
}