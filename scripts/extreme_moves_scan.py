#!/usr/bin/env python3
"""
Extreme Moves Scanner - Find S&P 500 stocks with Day0 return > ±20%.
Analyzes 2024 & 2025 earnings events and compares signals with forward returns.
"""

from __future__ import annotations

import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional
import json

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# Completely silence all logging
logging.disable(logging.CRITICAL)

# S&P 500 tickers (subset for testing - major companies)
SP500_TICKERS = [
    # Tech
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "AMD", "INTC", "CRM",
    "ORCL", "ADBE", "CSCO", "IBM", "QCOM", "TXN", "AVGO", "NOW", "INTU", "AMAT",
    "MU", "LRCX", "KLAC", "MRVL", "SNPS", "CDNS", "PANW", "CRWD", "ZS", "DDOG",
    # Finance
    "JPM", "BAC", "WFC", "GS", "MS", "C", "BLK", "SCHW", "AXP", "V", "MA", "PYPL",
    # Healthcare
    "JNJ", "UNH", "PFE", "MRK", "ABBV", "LLY", "TMO", "ABT", "DHR", "BMY",
    "AMGN", "GILD", "VRTX", "REGN", "MRNA", "BIIB", "ISRG", "MDT", "SYK", "ELV",
    # Consumer
    "WMT", "COST", "TGT", "HD", "LOW", "MCD", "SBUX", "NKE", "DIS", "NFLX",
    "CMCSA", "T", "VZ", "PG", "KO", "PEP", "PM", "MO", "CL", "EL",
    # Energy
    "XOM", "CVX", "SLB", "EOG", "COP", "OXY", "PSX", "VLO", "MPC", "HAL",
    # Industrial
    "CAT", "DE", "HON", "GE", "MMM", "BA", "RTX", "LMT", "UPS", "FDX",
    # Other
    "TSLA", "BRK.B", "COIN", "SQ", "SHOP", "SNOW", "PLTR", "NET", "U", "RBLX"
]


async def find_extreme_moves(ticker: str, results: list, threshold: float = 0.20) -> None:
    """Find earnings events with Day0 return exceeding threshold."""
    from app.fmp_client import get_historical_earnings, get_price_history, date_to_quarter

    try:
        # Get earnings and price data
        earnings = await get_historical_earnings(symbol=ticker, limit=12)
        prices = await get_price_history(symbol=ticker)

        if not earnings or not prices:
            return

        # Create price lookup
        price_map = {bar.date: bar for bar in prices}

        for earn in earnings:
            # Filter to 2024-2025
            if not (earn.date.startswith("2024") or earn.date.startswith("2025")):
                continue

            # Find T0 (first trading day on or after earnings date)
            t0_date = None
            t0_idx = None
            for i, bar in enumerate(prices):
                if bar.date >= earn.date:
                    t0_date = bar.date
                    t0_idx = i
                    break

            if t0_idx is None or t0_idx == 0:
                continue

            # Calculate Day0 return
            prev_close = prices[t0_idx - 1].close
            t0_close = prices[t0_idx].close
            day0_return = (t0_close - prev_close) / prev_close

            # Check if exceeds threshold
            if abs(day0_return) >= threshold:
                year, quarter = date_to_quarter(earn.date)
                results.append({
                    "ticker": ticker,
                    "earning_date": earn.date,
                    "year": year,
                    "quarter": quarter,
                    "day0_return": day0_return,
                    "eps": earn.eps,
                    "eps_estimated": earn.eps_estimated,
                    "revenue": earn.revenue,
                    "revenue_estimated": earn.revenue_estimated,
                })

    except Exception as e:
        pass


async def analyze_extreme_move(event: dict) -> Optional[dict]:
    """Analyze a single extreme move event."""
    from app.earnings_logic import analyze_ticker

    try:
        ticker = event["ticker"]
        target_date = event["earning_date"]

        # Run full analysis (use 12 events to cover 2024-2025 range)
        result = await analyze_ticker(symbol=ticker, max_events=12)

        # Find matching event
        for e in result.events:
            if e.earning_date == target_date:
                if e.signals:
                    # Get forward returns
                    t10 = next((fr for fr in e.forward_returns if fr.horizon == 10), None)
                    t30 = next((fr for fr in e.forward_returns if fr.horizon == 30), None)
                    t60 = next((fr for fr in e.forward_returns if fr.horizon == 60), None)

                    return {
                        **event,
                        "call_time": e.call_time,
                        "signal_score": e.signals.final_signal.score,
                        "signal_explanation": e.signals.final_signal.explanation,
                        "summary": e.semantic_features.one_sentence_summary if e.semantic_features else "",
                        "t10_return": t10.return_pct if t10 else None,
                        "t10_hit": t10.hit if t10 else None,
                        "t30_return": t30.return_pct if t30 else None,
                        "t30_hit": t30.hit if t30 else None,
                        "t60_return": t60.return_pct if t60 else None,
                        "t60_hit": t60.hit if t60 else None,
                    }

        return None

    except Exception as e:
        return None


async def main():
    """Main scanner function."""
    print("\n" + "=" * 90)
    print("EXTREME MOVES SCANNER - S&P 500 (2024-2025)")
    print("Finding earnings events with Day0 return > ±20%")
    print("=" * 90)

    # Phase 1: Find extreme moves
    print(f"\nPhase 1: Scanning {len(SP500_TICKERS)} tickers for extreme Day0 moves...")

    extreme_moves = []
    batch_size = 10
    total = len(SP500_TICKERS)

    for i in range(0, total, batch_size):
        batch = SP500_TICKERS[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size

        print(f"  Batch {batch_num}/{total_batches}...", end=" ", flush=True)

        tasks = [find_extreme_moves(ticker, extreme_moves) for ticker in batch]
        await asyncio.gather(*tasks)

        print(f"Found {len(extreme_moves)} so far")
        await asyncio.sleep(0.3)

    print(f"\nFound {len(extreme_moves)} extreme moves (Day0 > ±20%)")

    if not extreme_moves:
        print("No extreme moves found.")
        return

    # Sort by date descending
    extreme_moves.sort(key=lambda x: x["earning_date"], reverse=True)

    # Show found events
    print("\n" + "-" * 70)
    print("EXTREME MOVES FOUND:")
    print("-" * 70)
    print(f"{'Ticker':<8} {'Date':<12} {'Day0':<10}")
    print("-" * 70)
    for em in extreme_moves:
        print(f"{em['ticker']:<8} {em['earning_date']:<12} {em['day0_return']:+.1%}")

    # Phase 2: Analyze each event
    print("\n" + "=" * 90)
    print("Phase 2: Running semantic analysis on extreme moves...")
    print("=" * 90)

    analyzed_results = []
    for i, event in enumerate(extreme_moves):
        print(f"  Analyzing {event['ticker']} ({event['earning_date']})... [{i+1}/{len(extreme_moves)}]")
        result = await analyze_extreme_move(event)
        if result:
            analyzed_results.append(result)
        await asyncio.sleep(0.5)

    # Phase 3: Display results
    print("\n" + "=" * 90)
    print(f"ANALYSIS RESULTS: {len(analyzed_results)} events analyzed")
    print("=" * 90)

    if not analyzed_results:
        print("No events could be analyzed (transcripts may not be available).")
        return

    # Header
    print(f"\n{'Ticker':<8} {'Date':<12} {'Call':<6} {'Day0':<10} {'Signal':<8} {'T+10':<10} {'T+30':<10} {'T+60':<10}")
    print("-" * 90)

    for r in analyzed_results:
        day0 = f"{r['day0_return']:+.1%}"

        score = r['signal_score']
        if score > 5.5:
            signal = f"{score:.1f}↑"
        elif score < 4.5:
            signal = f"{score:.1f}↓"
        else:
            signal = f"{score:.1f} "

        t10 = f"{r['t10_return']:+.1%}" if r['t10_return'] is not None else "N/A"
        t30 = f"{r['t30_return']:+.1%}" if r['t30_return'] is not None else "N/A"
        t60 = f"{r['t60_return']:+.1%}" if r['t60_return'] is not None else "N/A"

        # Add hit indicator
        t10_hit = "✓" if r.get('t10_hit') else ("✗" if r.get('t10_hit') is False else "")
        t30_hit = "✓" if r.get('t30_hit') else ("✗" if r.get('t30_hit') is False else "")
        t60_hit = "✓" if r.get('t60_hit') else ("✗" if r.get('t60_hit') is False else "")

        print(f"{r['ticker']:<8} {r['earning_date']:<12} {r['call_time']:<6} {day0:<10} {signal:<8} {t10:<10} {t30:<10} {t60:<10}")

    # Summary by signal direction
    print("\n" + "=" * 90)
    print("SIGNAL ACCURACY ANALYSIS")
    print("=" * 90)

    bullish_signals = [r for r in analyzed_results if r['signal_score'] > 5.5]
    bearish_signals = [r for r in analyzed_results if r['signal_score'] < 4.5]

    print(f"\nBULLISH signals (score > 5.5): {len(bullish_signals)}")
    if bullish_signals:
        for horizon in [10, 30, 60]:
            hits = sum(1 for r in bullish_signals if r.get(f't{horizon}_hit') is True)
            total = sum(1 for r in bullish_signals if r.get(f't{horizon}_hit') is not None)
            if total > 0:
                print(f"  T+{horizon}: {hits}/{total} hits ({hits/total*100:.1f}%)")

    print(f"\nBEARISH signals (score < 4.5): {len(bearish_signals)}")
    if bearish_signals:
        for horizon in [10, 30, 60]:
            hits = sum(1 for r in bearish_signals if r.get(f't{horizon}_hit') is True)
            total = sum(1 for r in bearish_signals if r.get(f't{horizon}_hit') is not None)
            if total > 0:
                print(f"  T+{horizon}: {hits}/{total} hits ({hits/total*100:.1f}%)")

    # Detailed breakdown
    print("\n" + "=" * 90)
    print("DETAILED SIGNAL EXPLANATIONS")
    print("=" * 90)

    for r in analyzed_results:
        direction = "↑ BULLISH" if r['signal_score'] > 5.5 else ("↓ BEARISH" if r['signal_score'] < 4.5 else "— NEUTRAL")
        print(f"\n{r['ticker']} ({r['earning_date']}) - Score: {r['signal_score']:.1f} {direction}")
        print(f"  Day0: {r['day0_return']:+.1%} | Call: {r['call_time']}")
        print(f"  {r['signal_explanation']}")
        if r['summary']:
            print(f"  Summary: {r['summary'][:100]}...")


if __name__ == "__main__":
    asyncio.run(main())
