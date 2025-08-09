"use client";

import { AuthGuard } from "@/components/auth/AuthGuard";
import { UserMenu } from "@/components/auth/UserMenu";
import { useAuth } from "@/contexts/AuthContext";

export default function DashboardPage() {
  return (
    <AuthGuard>
      <DashboardContent />
    </AuthGuard>
  );
}

function DashboardContent() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <UserMenu />
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Welcome, {user?.full_name || user?.email}!</h2>
          
          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-medium text-gray-500">User Information</h3>
              <dl className="mt-2 space-y-1">
                <div className="flex justify-between">
                  <dt className="text-sm text-gray-600">Email:</dt>
                  <dd className="text-sm text-gray-900">{user?.email}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-sm text-gray-600">Username:</dt>
                  <dd className="text-sm text-gray-900">{user?.username || "Not set"}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-sm text-gray-600">User ID:</dt>
                  <dd className="text-sm text-gray-900 font-mono text-xs">{user?.id}</dd>
                </div>
              </dl>
            </div>

            {user?.subscriptions && Object.keys(user.subscriptions).length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-2">Active Subscriptions</h3>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(user.subscriptions).map(([key, value]) => {
                    if (value === true) {
                      return (
                        <span
                          key={key}
                          className="px-3 py-1 text-sm bg-green-100 text-green-700 rounded-full"
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

            <div className="pt-4 border-t">
              <h3 className="text-sm font-medium text-gray-500 mb-2">Feature Access</h3>
              <div className="space-y-2">
                <FeatureCheck name="Basic Features" subscription="BASIC" />
                <FeatureCheck name="Premium Features" subscription="PREMIUM" />
                <FeatureCheck name="FI Access" subscription="FI" />
                <FeatureCheck name="DITTY Access" subscription="DITTY" />
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

function FeatureCheck({ name, subscription }: { name: string; subscription: string }) {
  const { checkSubscription } = useAuth();
  const hasAccess = checkSubscription(subscription);

  return (
    <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
      <span className="text-sm text-gray-700">{name}</span>
      {hasAccess ? (
        <span className="flex items-center text-green-600">
          <svg className="w-5 h-5 mr-1" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
          Enabled
        </span>
      ) : (
        <span className="flex items-center text-gray-400">
          <svg className="w-5 h-5 mr-1" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
          Not Available
        </span>
      )}
    </div>
  );
}