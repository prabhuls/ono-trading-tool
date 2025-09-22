# Spread Recommendation Calculation Documentation

## Overview

This document explains how the **Overnight Options Trading Tool** calculates and recommends optimal call debit spreads for SPY and SPX options. The system uses a sophisticated multi-step algorithm to identify deep in-the-money spreads during the critical 3:00-4:00 PM ET trading window, prioritizing high probability trades with controlled risk profiles.

## Table of Contents
1. [Core Strategy Philosophy](#core-strategy-philosophy)
2. [Call Debit Spread Basics](#call-debit-spread-basics)
3. [The Calculation Process](#the-calculation-process)
4. [Selection Algorithm](#selection-algorithm)
5. [Real-World Example](#real-world-example)
6. [Risk Management](#risk-management)

---

## Core Strategy Philosophy

The application follows a **"Deep ITM Call Debit Spread Strategy"** that:

- **Prioritizes probability of profit**: Uses deep in-the-money (ITM) strikes
- **Controls risk through position sizing**: Maximum cost of $0.74 per spread
- **Optimizes for overnight holds**: Targets the 3:00-4:00 PM ET window
- **Uses realistic pricing**: Executes at bid-ask prices (Buy Ask - Sell Bid)

### Why Call Debit Spreads?

Call debit spreads are bullish strategies where you:
1. **BUY** a lower strike call (more expensive, deeper ITM)
2. **SELL** a higher strike call (less expensive, less ITM)
3. **PROFIT** when the stock price rises or stays above the higher strike

The strategy benefits from:
- Limited risk (maximum loss = spread cost)
- Defined reward (maximum profit = spread width - cost)
- Lower cost than buying calls outright
- Less time decay impact when deep ITM

---

## Call Debit Spread Basics

### Spread Width by Ticker

#### **SPY: $1-Wide Spreads**
- Example: Buy $580 Call, Sell $581 Call
- Maximum value: $1.00
- Typical cost range: $0.60 - $0.74

#### **SPX: $5-Wide Spreads**
- Example: Buy $5800 Call, Sell $5805 Call
- Maximum value: $5.00
- Scaled proportionally to SPX's ~10x price vs SPY

---

## The Calculation Process

### Step 1: Market Data Collection
The system gathers:
- **Current Stock Price**: Real-time SPY or SPX price from TheTradeList API
- **Option Chain**: Next-day expiration call options
- **Bid/Ask Spreads**: Live pricing for accurate cost calculations

### Step 2: In-The-Money (ITM) Filtering
The algorithm filters to only strikes **below** the current price:

```python
itm_contracts = [
    option for option in option_chain
    if option.strike < current_price
]
```

**Rationale:** ITM options have intrinsic value, making them less sensitive to time decay and volatility changes - ideal for overnight holds.

**Example:** If SPY = $585.18
- Valid strikes: $585, $584, $583, $582, ... (all below $585.18)
- Invalid strikes: $586, $587, $588, ... (all above $585.18)

### Step 3: Spread Construction and Cost Calculation

For each pair of ITM strikes, the system constructs $1-wide spreads (SPY) or $5-wide spreads (SPX):

```python
# For each consecutive strike pair:
buy_strike = lower_strike  # Deeper ITM (more expensive)
sell_strike = higher_strike # Less ITM (less expensive)

# Calculate midPrice spread cost (as per PROJECT_REQUIREMENTS.md):
spread_cost = (buy_option.ask - sell_option.bid) / 2
```

**Important:** The midPrice calculation uses:
- **Buy leg**: ASK price (what you pay)
- **Sell leg**: BID price (what you receive)
- **Divided by 2**: To get the midpoint price for fair valuation

### Step 4: Cost Filtering

The algorithm applies strict cost filtering:

```python
if spread_cost <= max_cost_threshold:  # Default: $0.74
    # Spread qualifies for consideration
```

**Why $0.74 Maximum?**
- Ensures favorable risk-reward ratio
- Maximum loss limited to ~74% of maximum gain
- Provides minimum 35% ROI potential

### Step 5: Metrics Calculation

For each qualifying spread, the system calculates:

```python
max_value = 1.00  # $1 for SPY, $5 for SPX
max_reward = max_value - spread_cost
max_risk = spread_cost
roi_potential = (max_reward / spread_cost) × 100
profit_target = spread_cost × 1.20  # 20% profit target
target_roi = ((profit_target - spread_cost) / spread_cost) × 100
```

---

## Selection Algorithm

### Step 6: Optimal Selection - Deepest ITM Priority

Among all qualifying spreads, the algorithm selects the one with the **lowest sell strike** (deepest in-the-money):

```python
best_spread = min(qualifying_spreads, key=lambda x: x.sell_strike)
```

**Strategic Advantages of Deep ITM Selection:**
- **Higher probability of profit**: Both strikes start with intrinsic value
- **Reduced time decay risk**: Deep ITM options have minimal time premium
- **Better overnight characteristics**: Less affected by after-hours volatility
- **Lower sensitivity to price movements**: Delta closer to 1.0

### Selection Priority Example

Given these qualifying spreads for SPY at $585.18:

| Spread | Cost (MidPrice) | Sell Strike | Selection |
|--------|-----------------|------------|-----------|
| 578/579 | $0.355 | $579 | ← **SELECTED** (Deepest ITM) |
| 579/580 | $0.340 | $580 | |
| 580/581 | $0.365 | $581 | |
| 581/582 | $0.350 | $582 | |

The 578/579 spread wins despite not being the cheapest, because the $579 sell strike is the furthest below current price.

---

## Real-World Example

Let's walk through a complete example with actual option contracts:

### Scenario: SPY Call Debit Spread at 3:30 PM ET

**Market Conditions:**
- SPY Current Price: **$585.18**
- Time: **3:30 PM ET** (optimal window)
- Strategy: **Call Debit Spread**
- Expiration: **Next trading day**

### Step 1: ITM Strike Filtering

The algorithm filters to strikes below $585.18:
- Available ITM strikes: $585, $584, $583, $582, $581, $580, $579, $578...

### Step 2: Spread Construction

The algorithm tests $1-wide spreads:

| Buy Strike | Sell Strike | Spread |
|------------|-------------|---------|
| $578 | $579 | 578/579 |
| $579 | $580 | 579/580 |
| $580 | $581 | 580/581 |
| $581 | $582 | 581/582 |
| $582 | $583 | 582/583 |

### Step 3: Cost Calculation

For each spread, using actual bid-ask quotes:

**Example: 578/579 Spread**

**BUY $578 Call:**
- Contract: SPY241220C00578000
- Bid: **$7.20**
- Ask: **$7.35** ← Use ASK for buying

**SELL $579 Call:**
- Contract: SPY241220C00579000
- Bid: **$6.64** ← Use BID for selling
- Ask: **$6.75**

**Spread Cost Calculation (MidPrice):**
```
Spread Cost = (Buy Ask - Sell Bid) / 2
           = ($7.35 - $6.64) / 2
           = $0.71 / 2
           = $0.355
```

### Step 4: Cost Filtering Results

| Spread | Cost (MidPrice) | Qualifies? |
|---------|-----------------|------------|
| 578/579 | $0.355 | ✓ Yes |
| 579/580 | $0.340 | ✓ Yes |
| 580/581 | $0.365 | ✓ Yes |
| 581/582 | $0.350 | ✓ Yes |
| 582/583 | $0.380 | ✓ Yes |

### Step 5: Metrics for Selected Spread (578/579)

```
Spread Cost (MidPrice) = $0.355
Max Value = $1.00 (spread width)
Max Reward = $1.00 - $0.355 = $0.645
Max Risk = $0.355
ROI Potential = ($0.645 / $0.355) × 100 = 181.7%
Profit Target = $0.355 × 1.20 = $0.426 (20% gain)
Target ROI = 20%
```

### Step 6: Final Selection

The 578/579 spread is selected because:
- **Lowest sell strike** ($579) among qualifying spreads
- **Deepest ITM** position (furthest below current price)
- **Cost within limit** ($0.355 < $0.74)
- **Favorable ROI** (181.7% potential)

### Profit/Loss Scenarios at Expiration

| SPY Price | Spread Value | Profit/Loss | Result |
|-----------|--------------|-------------|---------|
| $580+ | $1.00 | +$0.645 | **Maximum profit** (181.7% ROI) |
| $579.50 | $0.50 | +$0.145 | Partial profit |
| $579.355 | $0.355 | $0.00 | **Breakeven** |
| $579.00 | $0.00 | -$0.355 | **Maximum loss** (100% of cost) |
| $578.50 | $0.00 | -$0.355 | Maximum loss |
| $578.00 | $0.00 | -$0.355 | Maximum loss |

**Breakeven:** SPY at $579.355 (sell strike + midPrice cost)

---

## Risk Management

### Position Limits
- **Maximum spread cost**: $0.74 per spread
- **Spread width**: $1 for SPY, $5 for SPX
- **Expiration**: Next-day only (overnight holds)
- **Strike selection**: In-the-money only

### Time Window Optimization

**Why 3:00-4:00 PM ET?**
- **Reduced time premium**: Options have minimal time value remaining
- **Clearer direction**: Market trends are more established
- **Optimal pricing**: Bid-ask spreads typically tighten
- **Institutional activity**: Large players make end-of-day adjustments

### Exit Strategy
The recommended approach for overnight holds:
1. **Hold to expiration** for next-day options (most common)
2. **Early exit at profit target** (20% gain = $0.426 for $0.355 cost)
3. **Stop loss** if spread value drops below 50% of cost

### Risk Controls
- **Maximum loss**: Limited to spread cost (e.g., $0.355)
- **No naked options**: All positions are spread (defined risk)
- **Deep ITM selection**: Higher probability of profit
- **Cost filtering**: Ensures favorable risk-reward ratio

---

## Summary

The Overnight Options spread recommendation system implements a sophisticated algorithm that:

1. **Filters to ITM strikes only** (below current price for calls)
2. **Constructs $1-wide spreads** (SPY) or $5-wide spreads (SPX)
3. **Uses midPrice calculation** ((Buy Ask - Sell Bid) / 2)
4. **Applies strict cost filtering** (maximum $0.74)
5. **Selects deepest ITM spread** (lowest sell strike)

This approach prioritizes:
- **High probability of profit** through deep ITM positioning
- **Controlled risk** through cost limits
- **Optimal timing** during the 3:00-4:00 PM ET window
- **Clear execution** with defined entry and exit rules

The algorithm's strength lies in its systematic approach to capturing favorable overnight movements while maintaining strict risk controls and prioritizing capital preservation.

---

## Technical Implementation

For developers, the core logic resides in:
- **Backend**: `/server/app/services/credit_spread_scanner.py`
- **Frontend**: `/client/components/overnight-options/`
- **Types**: `/client/types/overnight-options.ts`

The system uses:
- Real-time option quotes from TradeList API
- Parallel processing for efficient spread testing
- Session-level caching to minimize API calls
- Structured logging for debugging and monitoring