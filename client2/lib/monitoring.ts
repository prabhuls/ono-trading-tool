import * as Sentry from "@sentry/nextjs";

/**
 * Simple error monitoring utilities using Sentry
 * Focused only on error capture, no performance monitoring
 */

interface User {
  id: string;
  email?: string;
  username?: string;
}

interface ErrorContext {
  [key: string]: unknown;
}

/**
 * Capture an exception and send it to Sentry
 */
export function captureException(
  error: Error | unknown,
  context?: ErrorContext
): void {
  if (process.env.NODE_ENV === "development") {
    console.error("Error captured:", error, context);
  }

  if (context) {
    Sentry.withScope((scope) => {
      Object.entries(context).forEach(([key, value]) => {
        scope.setExtra(key, value);
      });
      Sentry.captureException(error);
    });
  } else {
    Sentry.captureException(error);
  }
}

/**
 * Capture an error message
 */
export function captureMessage(
  message: string,
  level: "error" | "fatal" = "error"
): void {
  Sentry.captureMessage(message, level);
}

/**
 * Set user context for error tracking
 */
export function setUser(user: User | null): void {
  Sentry.setUser(user);
}

/**
 * Add breadcrumb for error context
 */
export function addBreadcrumb(breadcrumb: {
  message: string;
  category?: string;
  level?: Sentry.SeverityLevel;
  data?: Record<string, unknown>;
}): void {
  Sentry.addBreadcrumb(breadcrumb);
}

/**
 * Handle API errors with proper typing
 */
interface ApiError {
  response?: {
    status: number;
    data?: {
      message?: string;
      [key: string]: unknown;
    };
  };
  request?: unknown;
  config?: {
    url?: string;
    method?: string;
  };
  message?: string;
}

export function handleApiError(
  error: unknown,
  context?: ErrorContext
): { message: string; statusCode: number } {
  let errorMessage = "An unexpected error occurred";
  let statusCode = 500;

  // Type guard for API errors
  if (
    error &&
    typeof error === "object" &&
    "response" in error
  ) {
    const apiError = error as ApiError;

    if (apiError.response) {
      statusCode = apiError.response.status;
      errorMessage = apiError.response.data?.message || errorMessage;

      captureException(new Error(`API Error: ${errorMessage}`), {
        ...context,
        statusCode,
        endpoint: apiError.config?.url,
        method: apiError.config?.method,
      });
    } else if (apiError.request) {
      errorMessage = "Network error - please check your connection";
      captureException(new Error("Network Error"), context);
    }
  } else {
    // Handle non-API errors
    const errorObj = error instanceof Error ? error : new Error(String(error));
    captureException(errorObj, context);
  }

  return {
    message: errorMessage,
    statusCode,
  };
}