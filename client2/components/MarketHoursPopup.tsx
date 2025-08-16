"use client";

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { X, Clock } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function MarketHoursPopup() {
  const [isOpen, setIsOpen] = useState(false)
  const [marketStatus, setMarketStatus] = useState<'open' | 'closed' | 'pre' | 'after'>('closed')
  const [timeUntilChange, setTimeUntilChange] = useState('')

  useEffect(() => {
    const checkMarketHours = () => {
      const now = new Date()
      const hours = now.getUTCHours()
      const minutes = now.getUTCMinutes()
      const day = now.getUTCDay()
      
      // Convert to EST/EDT (UTC-5 or UTC-4)
      const estHours = (hours - 5 + 24) % 24
      
      // Market is closed on weekends
      if (day === 0 || day === 6) {
        setMarketStatus('closed')
        setTimeUntilChange('Market closed (Weekend)')
        return
      }
      
      // Pre-market: 4:00 AM - 9:30 AM EST
      if (estHours >= 4 && (estHours < 9 || (estHours === 9 && minutes < 30))) {
        setMarketStatus('pre')
        const openTime = new Date(now)
        openTime.setUTCHours(14, 30, 0, 0) // 9:30 AM EST
        const diff = Math.floor((openTime.getTime() - now.getTime()) / 60000)
        setTimeUntilChange(`Pre-market - Opens in ${diff} minutes`)
      }
      // Regular market: 9:30 AM - 4:00 PM EST
      else if ((estHours === 9 && minutes >= 30) || (estHours > 9 && estHours < 16)) {
        setMarketStatus('open')
        const closeTime = new Date(now)
        closeTime.setUTCHours(21, 0, 0, 0) // 4:00 PM EST
        const diff = Math.floor((closeTime.getTime() - now.getTime()) / 60000)
        setTimeUntilChange(`Market open - Closes in ${diff} minutes`)
      }
      // After-hours: 4:00 PM - 8:00 PM EST
      else if (estHours >= 16 && estHours < 20) {
        setMarketStatus('after')
        const closeTime = new Date(now)
        closeTime.setUTCHours(1, 0, 0, 0) // 8:00 PM EST (next day UTC)
        const diff = Math.floor((closeTime.getTime() - now.getTime()) / 60000)
        setTimeUntilChange(`After-hours - Ends in ${diff} minutes`)
      }
      // Market closed
      else {
        setMarketStatus('closed')
        setTimeUntilChange('Market closed')
      }
    }
    
    checkMarketHours()
    const interval = setInterval(checkMarketHours, 60000) // Update every minute
    
    // Show popup initially if market is open
    const timer = setTimeout(() => {
      if (marketStatus === 'open' || marketStatus === 'pre' || marketStatus === 'after') {
        setIsOpen(true)
      }
    }, 1000)
    
    return () => {
      clearInterval(interval)
      clearTimeout(timer)
    }
  }, [])

  if (!isOpen) return null

  return (
    <div className="fixed bottom-4 right-4 z-50 animate-in slide-in-from-bottom-2">
      <Card className="w-80">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium">Market Hours</CardTitle>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={() => setIsOpen(false)}
          >
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4" />
            <span className={`text-sm font-medium ${
              marketStatus === 'open' ? 'text-green-500' :
              marketStatus === 'pre' || marketStatus === 'after' ? 'text-yellow-500' :
              'text-red-500'
            }`}>
              {timeUntilChange}
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}