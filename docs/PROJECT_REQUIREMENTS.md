# Overnight Options Assistant: Top Ranked Trade Logic

## Executive Summary
The Overnight Options Assistant uses a sophisticated multi-step algorithm to identify the optimal $1-wide call debit spread for SPY options during the critical 3:20-3:40 PM ET trading window. The system prioritizes deep in-the-money spreads with controlled risk profiles and favorable overnight holding characteristics.

## Core Algorithm Overview

### Step 1: Market Data Collection
• Real-time SPY price: Current market price from Alpha Vantage API
• Next-day option chain: All call options expiring the next trading day
• Bid/Ask spreads: Live pricing for accurate mid-price calculations

### Step 2: Initial Filtering - In-The-Money Bias
const belowCurrentPrice = optionChain.filter(option => parseFloat(option.strike) < currentPrice);
Rationale: Only considers strikes below current SPY price to ensure both legs start in-the-money, maximizing profit probability for overnight holds.

## Step 3: Spread Construction - $1-Wide Methodology
const midPrice = (parseFloat(buyOption.ask) - parseFloat(sellOption.bid)) / 2;

**Spread Mechanics:**
• BUY lower strike call (more expensive, more intrinsic value)
• SELL higher strike call (less expensive, less intrinsic value)
• Net Cost = (Buy Ask - Sell Bid) / 2

### Step 4: Cost Filtering - Risk Management
if (midPrice <= maxCost) { // Default: $0.74 maximum
Why $0.74 Maximum: Ensures favorable risk-reward ratio where maximum loss is limited to approximately 74% of maximum gain potential.

### Step 5: Risk/Reward Calculation
const maxValue = 1.00; // $1 spread width
const maxReward = maxValue - midPrice; // Maximum profit potential
const maxRisk = midPrice; // Maximum loss
const profitTarget = midPrice * 1.20; // 20% profit target

**Example Calculation (Spread costs $0.60):**
• Max Reward: $1.00 - $0.60 = $0.40
• Max Risk: $0.60
• ROI Potential: ($0.40 / $0.60) × 100 = 66.7%
• Profit Target: $0.60 × 1.20 = $0.72
• Target ROI: (($0.72 - $0.60) / $0.60) × 100 = 20.0%

### Step 6: Optimal Selection - Deepest ITM Priority
return spreads.sort((a, b) => parseFloat(a.sellStrike) - parseFloat(b.sellStrike))[0];

Selection Criteria: Among all qualifying spreads, chooses the one with the lowest sell strike (most deeply in-the-money).

Strategic Advantages of Deep ITM Selection:
• Higher probability of profit
• Reduced time decay risk
• Better overnight holding characteristics
• Less sensitive to volatility changes

## Complete Trade Example
Market Conditions: SPY trading at $585.18

Spread  Cost    Qualifies
580/581 $0.73   ✓
579/580 $0.68   ✓
578/579 $0.71   ✓
577/578 $0.76   ✗ (exceeds $0.74 limit)

**Selection Process Results:**
• Winner: 580/581 spread (lowest sell strike = 581)
• Cost: $0.73
• Max Reward: $0.27
• Max Risk: $0.73
• ROI Potential: 36.1%
• Profit Target: $0.88 (20% above cost)
• Target ROI: 19.7%

## Time Window Optimization
Why 3:20-3:40 PM ET?
• Reduced Time Premium: Options have minimal time value left
• Clearer Direction: Market trends are more established
• Optimal Pricing: Bid-ask spreads typically tighten
• Institutional Activity: Large players often make end-of-day adjustments

## Conclusion
The Top Ranked Trade algorithm represents a sophisticated approach to overnight options trading, combining systematic risk management with strategic market timing. By focusing on deep in-the-money spreads during optimal trading windows, the system maximizes probability of success while maintaining strict risk controls.
The algorithm's strength lies in its conservative approach, prioritizing capital preservation while capturing favorable risk-adjusted returns through systematic selection of the most advantageous spread structures available in the market.