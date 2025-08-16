"use client";

import { useAuthContext } from "@/contexts/AuthContext";

interface LoginButtonProps {
  className?: string;
  token?: string;
  children?: React.ReactNode;
}

/**
 * Login button component for setting JWT token
 * In production, the token would come from an external authentication service
 */
export const LoginButton: React.FC<LoginButtonProps> = ({
  className = "px-4 py-2 bg-primary text-white rounded hover:bg-primary-dark transition-colors",
  token,
  children,
}) => {
  const { setToken } = useAuthContext();

  const handleLogin = () => {
    if (token) {
      // Set the provided token
      setToken(token);
    } else {
      // In production, this would redirect to external auth or show a token input
      console.warn("No token provided. In production, obtain token from authentication service.");
    }
  };

  return (
    <button onClick={handleLogin} className={className}>
      {children || "Set Token"}
    </button>
  );
};