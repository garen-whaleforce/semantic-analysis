#!/usr/bin/env python3
"""
S&P 500 Scanner - Find stocks with reversal signals in 2025.
"""

from __future__ import annotations

import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# Configure logging - less verbose
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# S&P 500 tickers (top ~100 by market cap for faster scanning)
SP500_TICKERS = [
    # Mega caps
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "LLY", "V",
    "UNH", "JPM", "XOM", "MA", "JNJ", "PG", "HD", "AVGO", "COST", "MRK",
    "ABBV", "CVX", "PEP", "KO", "ADBE", "WMT", "BAC", "CRM", "TMO", "MCD",
    "CSCO", "ACN", "ABT", "LIN", "ORCL", "DHR", "NKE", "TXN", "PM", "NEE",
    "AMD", "UPS", "RTX", "HON", "QCOM", "IBM", "INTC", "CAT", "GE", "AMGN",
    # Large caps
    "LOW", "SPGI", "GS", "MS", "BLK", "ELV", "PFE", "ISRG", "BKNG", "MDLZ",
    "AXP", "SYK", "GILD", "VRTX", "ADI", "TJX", "MMC", "LRCX", "SCHW", "C",
    "CB", "PGR", "REGN", "ZTS", "MO", "SBUX", "CME", "BDX", "SO", "DUK",
    "CI", "CL", "EOG", "ITW", "SLB", "PNC", "USB", "TGT", "AON", "ICE",
    "APD", "WM", "EMR", "CSX", "FDX", "NSC", "GM", "F", "DE", "MMM",
]


async def scan_ticker(ticker: str, results: list) -> None:
    """Scan a single ticker for reversal signals."""
    from app.earnings_logic import analyze_ticker
    
    try:
        result = await analyze_ticker(symbol=ticker, max_events=4)
        
        # Find events with non-neutral signals in 2025
        for event in result.events:
            if not event.signals:
                continue
            
            # Check if 2025 event
            if not event.earning_date.startswith("2025"):
                continue
                
            final_score = event.signals.final_signal.score
            
            # Non-neutral signal
            if final_score < 4.5 or final_score > 5.5:
                direction = "BULLISH" if final_score > 5.5 else "BEARISH"
                results.append({
                    "ticker": ticker,
                    "date": event.earning_date,
                    "score": final_score,
                    "direction": direction,
                    "day0_return": event.day0_return,
                    "explanation": event.signals.final_signal.explanation,
                    "summary": event.semantic_features.one_sentence_summary if event.semantic_features else "",
                })
                
    except Exception as e:
        # Silently skip failed tickers
        pass


async def main():
    """Main scanner function."""
    print("\n" + "=" * 70)
    print("S&P 500 REVERSAL SIGNAL SCANNER - 2025")
    print("=" * 70)
    print(f"\nScanning {len(SP500_TICKERS)} tickers...")
    print("This will take several minutes. Please wait.\n")
    
    results = []
    total = len(SP500_TICKERS)
    
    # Process in batches of 5 to avoid rate limits
    batch_size = 5
    for i in range(0, total, batch_size):
        batch = SP500_TICKERS[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size
        
        print(f"Processing batch {batch_num}/{total_batches}: {', '.join(batch)}")
        
        tasks = [scan_ticker(ticker, results) for ticker in batch]
        await asyncio.gather(*tasks)
        
        # Small delay between batches
        await asyncio.sleep(0.5)
    
    # Sort results by score (most extreme first)
    results.sort(key=lambda x: abs(x["score"] - 5.0), reverse=True)
    
    # Print results
    print("\n" + "=" * 70)
    print(f"FOUND {len(results)} REVERSAL SIGNALS IN 2025")
    print("=" * 70)
    
    if not results:
        print("\nNo significant reversal signals found.")
        return
    
    # Separate bullish and bearish
    bullish = [r for r in results if r["direction"] == "BULLISH"]
    bearish = [r for r in results if r["direction"] == "BEARISH"]
    
    print(f"\nBULLISH signals: {len(bullish)}")
    print(f"BEARISH signals: {len(bearish)}")
    
    print("\n" + "-" * 70)
    print("DETAILED RESULTS (sorted by signal strength)")
    print("-" * 70)
    print(f"{'Ticker':<8} {'Date':<12} {'Score':<8} {'Dir':<8} {'Day0':<10} {'Summary'}")
    print("-" * 70)
    
    for r in results:
        day0_str = f"{r['day0_return']:+.1%}" if r['day0_return'] else "N/A"
        summary = r['summary'][:45] + "..." if len(r['summary']) > 45 else r['summary']
        print(f"{r['ticker']:<8} {r['date']:<12} {r['score']:<8.1f} {r['direction']:<8} {day0_str:<10} {summary}")
    
    # Detailed breakdown
    print("\n" + "=" * 70)
    print("SIGNAL DETAILS")
    print("=" * 70)
    
    for r in results[:10]:  # Top 10 most extreme
        print(f"\n{r['ticker']} ({r['date']}) - Score: {r['score']:.1f} ({r['direction']})")
        print(f"  Day0 Return: {r['day0_return']:+.1%}" if r['day0_return'] else "  Day0 Return: N/A")
        print(f"  {r['explanation']}")


if __name__ == "__main__":
    asyncio.run(main())
