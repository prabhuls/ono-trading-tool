import * as Sentry from "@sentry/nextjs";

export class ErrorMonitoring {
  static init() {
    // Initialization happens in sentry config files
    // This is for any additional setup
  }

  static captureException(error: Error, context?: Record<string, any>) {
    console.error("Error captured:", error);
    
    Sentry.withScope((scope) => {
      if (context) {
        Object.keys(context).forEach((key) => {
          scope.setExtra(key, context[key]);
        });
      }
      
      // Add user context if available
      const user = getCurrentUser();
      if (user) {
        scope.setUser({ id: user.id, email: user.email });
      }
      
      // Add current route
      if (typeof window !== "undefined") {
        scope.setTag("route", window.location.pathname);
        scope.setContext("browser", {
          url: window.location.href,
          userAgent: navigator.userAgent,
        });
      }
      
      Sentry.captureException(error);
    });
  }

  static captureMessage(
    message: string, 
    level: "debug" | "info" | "warning" | "error" | "fatal" = "info",
    context?: Record<string, any>
  ) {
    Sentry.withScope((scope) => {
      if (context) {
        Object.keys(context).forEach((key) => {
          scope.setExtra(key, context[key]);
        });
      }
      
      Sentry.captureMessage(message, level);
    });
  }

  static setUser(user: { id: string; email?: string; username?: string }) {
    Sentry.setUser(user);
  }

  static clearUser() {
    Sentry.setUser(null);
  }

  static addBreadcrumb(breadcrumb: {
    message: string;
    category?: string;
    level?: Sentry.SeverityLevel;
    data?: Record<string, any>;
    timestamp?: number;
  }) {
    Sentry.addBreadcrumb(breadcrumb);
  }

  static startTransaction(name: string, op: string) {
    return Sentry.startTransaction({ name, op });
  }

  static setContext(name: string, context: Record<string, any>) {
    Sentry.setContext(name, context);
  }

  static setTag(key: string, value: string | number | boolean) {
    Sentry.setTag(key, value);
  }

  static setExtra(key: string, extra: any) {
    Sentry.setExtra(key, extra);
  }
}

// Helper function to get current user (implement based on your auth system)
function getCurrentUser(): { id: string; email?: string } | null {
  // This is a placeholder - implement based on your auth system
  if (typeof window !== "undefined") {
    const userStr = localStorage.getItem("user");
    if (userStr) {
      try {
        return JSON.parse(userStr);
      } catch {
        return null;
      }
    }
  }
  return null;
}

// Performance monitoring helpers
export function measurePerformance<T>(
  operation: string,
  fn: () => T | Promise<T>
): T | Promise<T> {
  const transaction = Sentry.startTransaction({
    op: operation,
    name: `Frontend: ${operation}`,
  });

  Sentry.getCurrentHub().configureScope((scope) => scope.setSpan(transaction));

  try {
    const result = fn();
    
    if (result instanceof Promise) {
      return result.finally(() => {
        transaction.finish();
      });
    } else {
      transaction.finish();
      return result;
    }
  } catch (error) {
    transaction.setStatus("internal_error");
    transaction.finish();
    throw error;
  }
}

// Error boundary helper
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  fallback?: React.ComponentType<{ error: Error; resetError: () => void }>
) {
  return Sentry.withErrorBoundary(Component, {
    fallback,
    showDialog: process.env.NODE_ENV === "production",
  });
}

// API error handler
export function handleApiError(error: any, context?: Record<string, any>) {
  let errorMessage = "An unexpected error occurred";
  let statusCode = 500;
  
  if (error.response) {
    // Server responded with error
    statusCode = error.response.status;
    errorMessage = error.response.data?.message || error.message;
    
    ErrorMonitoring.captureException(
      new Error(`API Error: ${errorMessage}`),
      {
        ...context,
        statusCode,
        endpoint: error.config?.url,
        method: error.config?.method,
        responseData: error.response.data,
      }
    );
  } else if (error.request) {
    // Request made but no response
    errorMessage = "Network error - please check your connection";
    
    ErrorMonitoring.captureException(
      new Error("Network Error"),
      {
        ...context,
        endpoint: error.config?.url,
        method: error.config?.method,
      }
    );
  } else {
    // Something else happened
    ErrorMonitoring.captureException(error, context);
  }
  
  return {
    message: errorMessage,
    statusCode,
    error: error.response?.data || error,
  };
}