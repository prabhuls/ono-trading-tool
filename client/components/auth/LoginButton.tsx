"use client";

import { useAuth } from "@/contexts/AuthContext";

interface LoginButtonProps {
  className?: string;
  redirectUri?: string;
  children?: React.ReactNode;
}

/**
 * Login button component that initiates OAuth flow
 */
export const LoginButton: React.FC<LoginButtonProps> = ({
  className = "px-4 py-2 bg-primary text-white rounded hover:bg-primary-dark transition-colors",
  redirectUri,
  children,
}) => {
  const { login } = useAuth();

  const handleLogin = () => {
    if (redirectUri) {
      // Store redirect URI in session storage for use after login
      sessionStorage.setItem("auth_redirect", redirectUri);
    }
    login();
  };

  return (
    <button onClick={handleLogin} className={className}>
      {children || "Sign In"}
    </button>
  );
};