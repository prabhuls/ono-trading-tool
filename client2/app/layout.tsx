import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import ErrorBoundary from "@/components/ErrorBoundary";
import { AuthProvider } from "@/contexts/AuthContext";
import { QueryClientProvider } from "@/lib/query-client";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/toaster";
import Navbar from "@/components/layout/Navbar";
import { MarketHoursPopup } from "@/components/MarketHoursPopup";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Cash Flow Agent",
  description: "Professional trading and investment tools platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <ErrorBoundary>
          <AuthProvider>
            <QueryClientProvider>
              <TooltipProvider>
                <div className="min-h-screen flex flex-col bg-white text-gray-900">
                  <Navbar />
                  <div className="flex-1 bg-white">
                    {children}
                  </div>
                  <MarketHoursPopup />
                </div>
                <Toaster />
              </TooltipProvider>
            </QueryClientProvider>
          </AuthProvider>
        </ErrorBoundary>
      </body>
    </html>
  );
}
