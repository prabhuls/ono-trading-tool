import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  
  // Environment variables that should be available on the client
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME || "Cash Flow Agent VIP",
    NEXT_PUBLIC_ENVIRONMENT: process.env.NEXT_PUBLIC_ENVIRONMENT || "development",
  },
  
  // Image domains for next/image
  images: {
    domains: ["localhost", "yourdomain.com"],
  },
  
  // Headers for security
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "X-XSS-Protection",
            value: "1; mode=block",
          },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
        ],
      },
    ];
  },
  
  // Webpack configuration
  webpack: (config, { isServer }) => {
    if (isServer) {
      // Ignore harmless warnings from OpenTelemetry
      config.ignoreWarnings = [
        {
          module: /@opentelemetry\/instrumentation/,
          message: /Critical dependency: the request of a dependency is an expression/,
        },
        {
          module: /@prisma\/instrumentation/,
          message: /Critical dependency: the request of a dependency is an expression/,
        },
      ];
    }
    return config;
  },
};

// Minimal Sentry configuration
const sentryWebpackPluginOptions = {
  silent: true,
  
  // Disable source maps completely for simplicity
  sourcemaps: {
    disable: true,
  },
  
  // Disable all optional features
  widenClientFileUpload: false,
  hideSourceMaps: true,
  disableLogger: true,
};

// Export without Sentry wrapping in development or when no auth token
const shouldUseSentry = 
  process.env.NODE_ENV === "production" && 
  process.env.SENTRY_AUTH_TOKEN && 
  process.env.SENTRY_AUTH_TOKEN !== '' &&
  process.env.SENTRY_AUTH_TOKEN !== 'your-auth-token';

export default shouldUseSentry 
  ? withSentryConfig(nextConfig, sentryWebpackPluginOptions)
  : nextConfig;