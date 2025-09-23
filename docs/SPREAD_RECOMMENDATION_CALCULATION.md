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

# Calculate spread cost using mid-market pricing:
buy_mid = (buy_option.ask + buy_option.bid) / 2
sell_mid = (sell_option.ask + sell_option.bid) / 2
spread_cost = buy_mid - sell_mid
```

**Important:** The spread cost calculation uses:
- **Buy leg mid-market price**: (ASK + BID) / 2
- **Sell leg mid-market price**: (ASK + BID) / 2
- **Spread cost**: Difference between the two mid-market prices

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

| Spread | Cost (Mid-Market) | Sell Strike | Selection |
|--------|-------------------|------------|-----------|
| 578/579 | $0.58 | $579 | ← **SELECTED** (Deepest ITM) |
| 579/580 | $0.55 | $580 | |
| 580/581 | $0.59 | $581 | |
| 581/582 | $0.57 | $582 | |

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

**Spread Cost Calculation (Mid-Market Pricing):**
```
Buy Mid = (Buy Ask + Buy Bid) / 2 = ($7.35 + $7.20) / 2 = $7.275
Sell Mid = (Sell Ask + Sell Bid) / 2 = ($6.75 + $6.64) / 2 = $6.695
Spread Cost = Buy Mid - Sell Mid = $7.275 - $6.695 = $0.58
```

### Step 4: Cost Filtering Results

| Spread | Cost (Mid-Market) | Qualifies? |
|---------|-------------------|------------|
| 578/579 | $0.58 | ✓ Yes |
| 579/580 | $0.55 | ✓ Yes |
| 580/581 | $0.59 | ✓ Yes |
| 581/582 | $0.57 | ✓ Yes |
| 582/583 | $0.62 | ✓ Yes |

### Step 5: Metrics for Selected Spread (578/579)

```
Spread Cost (Mid-Market) = $0.58
Max Value = $1.00 (spread width)
Max Reward = $1.00 - $0.58 = $0.42
Max Risk = $0.58
ROI Potential = ($0.42 / $0.58) × 100 = 72.4%
Profit Target = $0.58 × 1.20 = $0.696 (20% gain)
Target ROI = 20%
```

### Step 6: Final Selection

The 578/579 spread is selected because:
- **Lowest sell strike** ($579) among qualifying spreads
- **Deepest ITM** position (furthest below current price)
- **Cost within limit** ($0.58 < $0.74)
- **Favorable ROI** (72.4% potential)

### Profit/Loss Scenarios at Expiration

| SPY Price | Spread Value | Profit/Loss | Result |
|-----------|--------------|-------------|---------|
| $580+ | $1.00 | +$0.42 | **Maximum profit** (72.4% ROI) |
| $579.75 | $0.75 | +$0.17 | Partial profit |
| $579.58 | $0.58 | $0.00 | **Breakeven** |
| $579.00 | $0.00 | -$0.58 | **Maximum loss** (100% of cost) |
| $578.50 | $0.00 | -$0.58 | Maximum loss |
| $578.00 | $0.00 | -$0.58 | Maximum loss |

**Breakeven:** SPY at $579.58 (sell strike + spread cost)

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
2. **Early exit at profit target** (20% gain = $0.696 for $0.58 cost)
3. **Stop loss** if spread value drops below 50% of cost

### Risk Controls
- **Maximum loss**: Limited to spread cost (e.g., $0.58)
- **No naked options**: All positions are spread (defined risk)
- **Deep ITM selection**: Higher probability of profit
- **Cost filtering**: Ensures favorable risk-reward ratio

---

## Summary

The Overnight Options spread recommendation system implements a sophisticated algorithm that:

1. **Filters to ITM strikes only** (below current price for calls)
2. **Constructs $1-wide spreads** (SPY) or $5-wide spreads (SPX)
3. **Uses mid-market pricing** (buy_mid - sell_mid)
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