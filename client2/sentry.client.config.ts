import * as Sentry from "@sentry/nextjs";

Sentry.init({
  // Only required configuration
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_ENVIRONMENT || "development",
  
  // Disable all performance monitoring
  tracesSampleRate: 0,
  
  // Only enable in production
  enabled: process.env.NODE_ENV === "production",
});