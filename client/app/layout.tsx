import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import ErrorBoundary from "@/components/error-boundary";
import { AuthProvider } from "@/contexts/AuthContext";
import { QueryClientProvider } from "@/lib/query-client";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/toaster";
import Navbar from "@/components/layout/Navbar";
import { MarketHoursPopup } from "@/components/MarketHoursPopup";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Overnight Options Assistant",
  description: "Professional trading and investment tools platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <ErrorBoundary>
          <AuthProvider>
            <QueryClientProvider>
              <TooltipProvider>
                <div className="min-h-screen">
                  {children}
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
