import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_ENVIRONMENT || "development",
  
  // Performance Monitoring
  integrations: [
    new Sentry.BrowserTracing({
      // Set tracingOrigins to control what URLs are traced
      tracingOrigins: ["localhost", /^https:\/\/yourserver\.io\/api/],
      // Set sample rate for performance monitoring
      routingInstrumentation: Sentry.nextRouterInstrumentation,
    }),
    new Sentry.Replay({
      // Mask all text content, but record user interactions
      maskAllText: true,
      blockAllMedia: true,
    }),
  ],
  
  // Performance Monitoring
  tracesSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 1.0,
  
  // Session Replay
  replaysSessionSampleRate: 0.1, // 10% of sessions will be recorded
  replaysOnErrorSampleRate: 1.0, // 100% of sessions with errors will be recorded
  
  // Release Tracking
  release: process.env.NEXT_PUBLIC_SENTRY_RELEASE,
  
  // Filter out non-error events in production
  beforeSend(event, hint) {
    // Filter out non-error console logs in production
    if (process.env.NODE_ENV === "production") {
      if (event.level === "log" || event.level === "debug") {
        return null;
      }
    }
    
    // Filter out certain errors
    const error = hint.originalException;
    if (error && error instanceof Error) {
      // Filter out network errors that are expected
      if (error.message && error.message.includes("NetworkError")) {
        return null;
      }
      
      // Filter out user-cancelled requests
      if (error.message && error.message.includes("AbortError")) {
        return null;
      }
    }
    
    return event;
  },
  
  // Ignore certain errors
  ignoreErrors: [
    // Browser extensions
    "top.GLOBALS",
    // Facebook related errors
    "fb_xd_fragment",
    // Network errors
    "Network request failed",
    "NetworkError",
    "Failed to fetch",
    // User actions
    "Non-Error promise rejection captured",
    // Safari specific
    "Non-Error exception captured",
  ],
});