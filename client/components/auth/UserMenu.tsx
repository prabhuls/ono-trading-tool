"use client";

import { useState, useRef, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";

interface UserMenuProps {
  className?: string;
}

/**
 * User menu dropdown component for authenticated users
 */
export const UserMenu: React.FC<UserMenuProps> = ({ className = "" }) => {
  const { user, logout, checkSubscription } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  if (!user) return null;

  const handleLogout = async () => {
    await logout();
    router.push("/");
  };

  const initials = user.full_name
    ? user.full_name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : user.email.slice(0, 2).toUpperCase();

  return (
    <div className={`relative ${className}`} ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 p-2 rounded-lg hover:bg-gray-100 transition-colors"
      >
        <div className="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center text-sm font-medium">
          {initials}
        </div>
        <span className="text-sm font-medium text-gray-700">
          {user.full_name || user.username || user.email}
        </span>
        <svg
          className={`w-4 h-4 text-gray-500 transition-transform ${
            isOpen ? "rotate-180" : ""
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50">
          <div className="px-4 py-2 border-b border-gray-200">
            <p className="text-sm font-medium text-gray-900">
              {user.full_name || user.username}
            </p>
            <p className="text-xs text-gray-500">{user.email}</p>
          </div>

          {/* Subscriptions */}
          {user.subscriptions && Object.keys(user.subscriptions).length > 0 && (
            <div className="px-4 py-2 border-b border-gray-200">
              <p className="text-xs font-medium text-gray-500 mb-1">Subscriptions</p>
              <div className="flex flex-wrap gap-1">
                {Object.entries(user.subscriptions).map(([key, value]) => {
                  if (value === true) {
                    return (
                      <span
                        key={key}
                        className="px-2 py-0.5 text-xs bg-green-100 text-green-700 rounded-full"
                      >
                        {key}
                      </span>
                    );
                  }
                  return null;
                })}
              </div>
            </div>
          )}

          {/* Menu Items */}
          <div className="py-1">
            <button
              onClick={() => {
                router.push("/profile");
                setIsOpen(false);
              }}
              className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
            >
              Profile
            </button>
            <button
              onClick={() => {
                router.push("/settings");
                setIsOpen(false);
              }}
              className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
            >
              Settings
            </button>
            {checkSubscription("PREMIUM") && (
              <button
                onClick={() => {
                  router.push("/premium");
                  setIsOpen(false);
                }}
                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
              >
                Premium Features
              </button>
            )}
          </div>

          <div className="border-t border-gray-200 pt-1">
            <button
              onClick={handleLogout}
              className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
            >
              Sign Out
            </button>
          </div>
        </div>
      )}
    </div>
  );
};