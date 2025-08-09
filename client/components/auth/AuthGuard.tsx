"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

interface AuthGuardProps {
  children: React.ReactNode;
  requiredSubscription?: string;
  redirectTo?: string;
  fallback?: React.ReactNode;
}

/**
 * Component to protect pages that require authentication
 */
export const AuthGuard: React.FC<AuthGuardProps> = ({
  children,
  requiredSubscription,
  redirectTo = "/login",
  fallback,
}) => {
  const { isAuthenticated, isLoading, checkSubscription } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push(redirectTo);
    }

    if (!isLoading && isAuthenticated && requiredSubscription) {
      if (!checkSubscription(requiredSubscription)) {
        router.push("/subscription-required");
      }
    }
  }, [isAuthenticated, isLoading, requiredSubscription, redirectTo, router, checkSubscription]);

  if (isLoading) {
    return (
      fallback || (
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      )
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  if (requiredSubscription && !checkSubscription(requiredSubscription)) {
    return null;
  }

  return <>{children}</>;
};