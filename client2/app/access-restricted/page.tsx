'use client';

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Lock } from "lucide-react";

export default function AccessRestrictedPage() {
  const handleLogin = () => {
    // Redirect to OCT login
    window.location.href = 'https://app.oneclicktrading.com/landing/login';
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 flex items-center justify-center p-4">
      <Card className="max-w-md w-full">
        <CardHeader className="text-center">
          <div className="mx-auto w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
            <Lock className="h-8 w-8 text-red-600" />
          </div>
          <CardTitle className="text-2xl font-bold">Access Restricted</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-center text-gray-600">
            You need to be authenticated to access this application.
          </p>
          <p className="text-center text-sm text-gray-500">
            Please log in with your One Click Trading account to continue.
          </p>
          <Button 
            onClick={handleLogin}
            className="w-full bg-green-600 hover:bg-green-700"
            size="lg"
          >
            Login with One Click Trading
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}