/**
 * Runtime configuration for the application
 * This allows environment variables to be read at runtime instead of build time
 */

export function getBackendUrl(): string {
  // Check multiple possible sources for the backend URL
  
  // 1. First check if we're in the browser
  if (typeof window !== 'undefined') {
    // Try to get from window object (can be injected by server)
    if ((window as any).__RUNTIME_CONFIG__?.BACKEND_URL) {
      return (window as any).__RUNTIME_CONFIG__.BACKEND_URL;
    }
    
    // Check the current URL - if we're not on localhost, construct backend URL
    const currentHost = window.location.hostname;
    if (currentHost !== 'localhost' && currentHost !== '127.0.0.1') {
      // If we're on a Railway app, try to construct the backend URL
      if (currentHost.includes('railway.app')) {
        // Replace 'frontend' with 'backend' in the hostname
        const backendHost = currentHost.replace('-frontend', '-backend').replace('frontend-', 'backend-');
        return `https://${backendHost}`;
      }
    }
  }
  
  // 2. Fall back to environment variables (build-time)
  return process.env.NEXT_PUBLIC_BACKEND_URL || 
         process.env.NEXT_PUBLIC_API_URL || 
         'http://localhost:8000';
}

// Export a singleton instance
export const API_URL = getBackendUrl();