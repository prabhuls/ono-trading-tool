import axios, { AxiosError, AxiosInstance, AxiosRequestConfig } from "axios";
import { captureException, handleApiError, setUser, addBreadcrumb } from "./monitoring";

// Types
export interface ApiResponse<T = unknown> {
  success: boolean;
  message: string;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
  metadata?: Record<string, unknown>;
  request_id?: string;
  timestamp: string;
}

export interface PaginatedResponse<T = unknown> extends ApiResponse<T[]> {
  pagination: {
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

// Error type for standardized errors
export interface StandardizedError extends Error {
  standardizedError?: {
    message: string;
    statusCode: number;
    error: unknown;
  };
}

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = getAuthToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Add request ID
    const requestId = generateRequestId();
    config.headers["X-Request-ID"] = requestId;
    
    // Log request
    addBreadcrumb({
      message: `API Request: ${config.method?.toUpperCase()} ${config.url}`,
      category: "api.request",
      level: "info",
      data: {
        method: config.method,
        url: config.url,
        params: config.params,
        requestId,
      },
    });
    
    return config;
  },
  (error) => {
    captureException(error, {
      context: "api.request.interceptor",
    });
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    // Log successful response
    addBreadcrumb({
      message: `API Response: ${response.status} ${response.config.url}`,
      category: "api.response",
      level: "info",
      data: {
        status: response.status,
        url: response.config.url,
        requestId: response.config.headers["X-Request-ID"],
      },
    });
    
    return response;
  },
  async (error: AxiosError<ApiResponse>) => {
    // Handle 401 Unauthorized
    if (error.response?.status === 401) {
      // Clear auth and redirect to login
      clearAuthToken();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }
    
    // Log error response
    const errorData = handleApiError(error, {
      context: "api.response.interceptor",
    });
    
    // Return a standardized error
    return Promise.reject({
      ...error,
      standardizedError: errorData,
    });
  }
);

// Helper functions
function getAuthToken(): string | null {
  if (typeof window !== "undefined") {
    return localStorage.getItem("auth_token");
  }
  return null;
}

function clearAuthToken(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem("auth_token");
    setUser(null);
  }
}

function generateRequestId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

// API client wrapper with better error handling
export class ApiClient {
  static async get<T = unknown>(
    url: string,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    try {
      const response = await apiClient.get<ApiResponse<T>>(url, config);
      return response.data;
    } catch (error) {
      const standardizedError = error as StandardizedError;
      throw standardizedError.standardizedError || error;
    }
  }
  
  static async post<T = unknown>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    try {
      const response = await apiClient.post<ApiResponse<T>>(url, data, config);
      return response.data;
    } catch (error) {
      const standardizedError = error as StandardizedError;
      throw standardizedError.standardizedError || error;
    }
  }
  
  static async put<T = unknown>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    try {
      const response = await apiClient.put<ApiResponse<T>>(url, data, config);
      return response.data;
    } catch (error) {
      const standardizedError = error as StandardizedError;
      throw standardizedError.standardizedError || error;
    }
  }
  
  static async patch<T = unknown>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    try {
      const response = await apiClient.patch<ApiResponse<T>>(url, data, config);
      return response.data;
    } catch (error) {
      const standardizedError = error as StandardizedError;
      throw standardizedError.standardizedError || error;
    }
  }
  
  static async delete<T = unknown>(
    url: string,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    try {
      const response = await apiClient.delete<ApiResponse<T>>(url, config);
      return response.data;
    } catch (error) {
      const standardizedError = error as StandardizedError;
      throw standardizedError.standardizedError || error;
    }
  }
  
  // Paginated request helper
  static async getPaginated<T = unknown>(
    url: string,
    params?: {
      page?: number;
      page_size?: number;
      [key: string]: string | number | boolean | undefined;
    }
  ): Promise<PaginatedResponse<T>> {
    const defaultParams = {
      page: 1,
      page_size: 50,
      ...params,
    };
    
    try {
      const response = await apiClient.get<PaginatedResponse<T>>(url, {
        params: defaultParams,
      });
      return response.data;
    } catch (error) {
      const standardizedError = error as StandardizedError;
      throw standardizedError.standardizedError || error;
    }
  }
  
  // Set auth token
  static setAuthToken(token: string): void {
    if (typeof window !== "undefined") {
      localStorage.setItem("auth_token", token);
    }
  }
  
  // Clear auth token
  static clearAuth(): void {
    clearAuthToken();
  }
}

// Export the raw axios instance for advanced use cases
export { apiClient };

// Example API endpoints
export const api = {
  // Health
  health: {
    check: () => ApiClient.get("/api/v1/health"),
    ready: () => ApiClient.get("/api/v1/health/ready"),
    live: () => ApiClient.get("/api/v1/health/live"),
  },
  
  // Auth endpoints
  auth: {
    login: (redirectUri?: string) => {
      const params = redirectUri ? `?redirect_uri=${encodeURIComponent(redirectUri)}` : "";
      return ApiClient.get(`/api/v1/auth/login${params}`);
    },
    callback: (code: string) => ApiClient.get(`/api/v1/auth/callback?code=${code}`),
    verify: () => ApiClient.post("/api/v1/auth/verify"),
    logout: () => ApiClient.post("/api/v1/auth/logout"),
    user: () => ApiClient.get("/api/v1/auth/user"),
    checkSubscription: (name: string) => ApiClient.get(`/api/v1/auth/check-subscription/${name}`),
    refresh: () => ApiClient.post("/api/v1/auth/refresh"),
    // Development only
    createTestToken: (userId?: string, email?: string, includeSubscriptions?: boolean) => {
      const params = new URLSearchParams();
      if (userId) params.append("user_id", userId);
      if (email) params.append("email", email);
      if (includeSubscriptions !== undefined) params.append("include_subscriptions", String(includeSubscriptions));
      return ApiClient.get(`/api/v1/auth/dev/create-test-token?${params.toString()}`);
    },
  },
  
  // Example endpoints
  example: {
    list: (params?: { page?: number; page_size?: number; search?: string }) =>
      ApiClient.getPaginated("/api/v1/example/items", params),
    get: (id: string) => ApiClient.get(`/api/v1/example/items/${id}`),
    create: (data: unknown) => ApiClient.post("/api/v1/example/items", data),
    update: (id: string, data: unknown) => ApiClient.put(`/api/v1/example/items/${id}`, data),
    delete: (id: string) => ApiClient.delete(`/api/v1/example/items/${id}`),
  },
  
  // Add more API endpoints here
};