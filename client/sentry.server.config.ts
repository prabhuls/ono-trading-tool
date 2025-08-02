import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.SENTRY_DSN || process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.ENVIRONMENT || process.env.NEXT_PUBLIC_ENVIRONMENT || "development",
  
  // Performance Monitoring
  tracesSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 1.0,
  
  // Release Tracking
  release: process.env.NEXT_PUBLIC_SENTRY_RELEASE,
  
  // Debug
  debug: process.env.NODE_ENV === "development",
  
  // Integrations
  integrations: [
    // Automatically instrument Node.js libraries and frameworks
    ...Sentry.autoDiscoverNodePerformanceMonitoringIntegrations(),
  ],
  
  // beforeSend callback to filter sensitive data
  beforeSend(event, hint) {
    // Remove sensitive headers
    if (event.request && event.request.headers) {
      const sensitiveHeaders = ["cookie", "authorization", "x-api-key"];
      sensitiveHeaders.forEach(header => {
        if (event.request?.headers?.[header]) {
          event.request.headers[header] = "[REDACTED]";
        }
      });
    }
    
    // Remove sensitive query parameters
    if (event.request && event.request.query_string) {
      const sensitiveParams = ["api_key", "token", "secret"];
      let queryString = event.request.query_string;
      sensitiveParams.forEach(param => {
        const regex = new RegExp(`${param}=[^&]*`, "gi");
        queryString = queryString.replace(regex, `${param}=[REDACTED]`);
      });
      event.request.query_string = queryString;
    }
    
    return event;
  },
});