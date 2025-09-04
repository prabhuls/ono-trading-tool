"use client";

import Link from "next/link";

export default function Navbar() {
  
  const handleTradeJournalClick = () => {
    console.log('🔄 Navbar: Trade Journal clicked - FORCING REFRESH...');
    
    // Dispatch the same event that DELETE button uses to force refresh
    window.dispatchEvent(new CustomEvent('tradeJournalUpdate', { 
      detail: { action: 'navigation', source: 'navbar', timestamp: Date.now() } 
    }));
    
    console.log('✅ Navbar: Trade Journal refresh event dispatched');
  };

  return (
    <nav className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b-vip-thick border-gray-200 shadow-sm">
      <div className="container mx-auto px-6 py-4">
        <div className="flex flex-col sm:flex-row justify-between items-center">
          <div className="flex items-center mb-4 sm:mb-0">
            <Link href="/">
              <h1 className="text-2xl font-black text-gradient cursor-pointer hover:scale-105 transition-transform duration-200">
                Cash Flow Agent VIP
              </h1>
            </Link>
          </div>
          <div className="flex items-center space-x-8">
            <Link href="/">
              <span className="relative font-semibold text-gray-800 hover:text-green-600 transition-colors duration-200 cursor-pointer after:content-[''] after:absolute after:bottom-[-4px] after:left-0 after:w-0 after:h-[2px] after:bg-green-500 hover:after:w-full after:transition-all after:duration-300">
                Dashboard
              </span>
            </Link>
            <Link href="/market-data">
              <span className="relative font-semibold text-gray-800 hover:text-green-600 transition-colors duration-200 cursor-pointer after:content-[''] after:absolute after:bottom-[-4px] after:left-0 after:w-0 after:h-[2px] after:bg-green-500 hover:after:w-full after:transition-all after:duration-300">
                Market Data
              </span>
            </Link>
            <Link href="/trade-journal" onClick={handleTradeJournalClick}>
              <span className="relative font-semibold text-gray-800 hover:text-green-600 transition-colors duration-200 cursor-pointer after:content-[''] after:absolute after:bottom-[-4px] after:left-0 after:w-0 after:h-[2px] after:bg-green-500 hover:after:w-full after:transition-all after:duration-300">
                Trade Journal
              </span>
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}