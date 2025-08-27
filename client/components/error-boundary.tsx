"use client";

import React from "react";
import * as Sentry from "@sentry/nextjs";
import { captureException, addBreadcrumb } from "@/lib/monitoring";

interface Props {
  children: React.ReactNode;
  fallback?: React.ComponentType<{ 
    error: Error; 
    resetError: () => void;
    errorInfo?: React.ErrorInfo;
  }>;
  showDialog?: boolean;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

// Default error fallback component
const DefaultErrorFallback: React.FC<{ 
  error: Error; 
  resetError: () => void;
  errorInfo?: React.ErrorInfo;
}> = ({ error, resetError, errorInfo }) => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
            Oops! Something went wrong
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            We&apos;re sorry for the inconvenience. The error has been reported to our team.
          </p>
        </div>
        
        {process.env.NODE_ENV === "development" && (
          <div className="mt-8 bg-red-50 border border-red-200 rounded-md p-4">
            <h3 className="text-sm font-medium text-red-800">Error Details:</h3>
            <pre className="mt-2 text-xs text-red-600 overflow-auto">
              {error.toString()}
              {errorInfo && errorInfo.componentStack}
            </pre>
          </div>
        )}
        
        <div className="mt-8 space-y-4">
          <button
            onClick={resetError}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            Try Again
          </button>
          
          <button
            onClick={() => window.location.href = "/"}
            className="w-full flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            Go to Homepage
          </button>
        </div>
      </div>
    </div>
  );
};

class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI
    return { 
      hasError: true, 
      error,
      errorInfo: null
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log the error to console in development
    if (process.env.NODE_ENV === "development") {
      console.error("ErrorBoundary caught an error:", error, errorInfo);
    }
    
    // Update state with error info
    this.setState({
      errorInfo
    });
    
    // Report to Sentry
    Sentry.withScope((scope) => {
      // Add error boundary context
      scope.setContext("errorBoundary", {
        componentStack: errorInfo.componentStack,
        props: this.props.children?.toString(),
      });
      
      // Set error level
      scope.setLevel("error");
      
      // Add tags
      scope.setTag("error_boundary", true);
      scope.setTag("component", this.getComponentName());
      
      // Capture the exception
      Sentry.captureException(error);
    });
    
    // Also log with our monitoring
    captureException(error, {
      errorBoundary: true,
      componentStack: errorInfo.componentStack,
    });
    
    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
    
    // Show Sentry dialog in production if enabled
    if (this.props.showDialog && process.env.NODE_ENV === "production") {
      Sentry.showReportDialog();
    }
  }

  getComponentName(): string {
    // Try to extract component name from stack or children
    if (this.state.errorInfo?.componentStack) {
      const match = this.state.errorInfo.componentStack.match(/in (\w+)/);
      if (match) return match[1];
    }
    return "Unknown";
  }

  resetError = () => {
    // Add breadcrumb for error recovery
    addBreadcrumb({
      message: "Error boundary reset",
      category: "ui.error_boundary",
      level: "info",
    });
    
    this.setState({ 
      hasError: false, 
      error: null,
      errorInfo: null
    });
  };

  render() {
    if (this.state.hasError && this.state.error) {
      const FallbackComponent = this.props.fallback || DefaultErrorFallback;
      
      return (
        <FallbackComponent
          error={this.state.error}
          resetError={this.resetError}
          errorInfo={this.state.errorInfo || undefined}
        />
      );
    }

    return this.props.children;
  }
}

// HOC for wrapping components with error boundary
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<Props, "children">
): React.ComponentType<P> {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </ErrorBoundary>
  );
  
  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;
  
  return WrappedComponent;
}

export default ErrorBoundary;