#!/usr/bin/env python3
"""
Quick Test Script for Semantic Earnings Reversal Framework.

Usage:
    python scripts/quick_test.py [TICKER]

Examples:
    python scripts/quick_test.py AAPL
    python scripts/quick_test.py MSFT
    python scripts/quick_test.py        # defaults to AAPL
"""

from __future__ import annotations

import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def format_hit_rate(hit_rate: Optional[float]) -> str:
    """Format hit rate as percentage or N/A."""
    if hit_rate is None:
        return "N/A"
    return f"{hit_rate * 100:.1f}%"


def print_results(result):
    """Print analysis results in a readable format."""
    print("\n" + "=" * 60)
    print(f"ANALYSIS RESULTS: {result.ticker}")
    print("=" * 60)

    # Summary stats
    print(f"\nEvents found: {result.total_events_found}")
    print(f"Events analyzed: {result.events_analyzed}")
    print(f"Events with signals: {result.events_with_signals}")

    # Hit rates
    print("\n" + "-" * 40)
    print("HIT RATES BY HORIZON")
    print("-" * 40)
    print(f"{'Horizon':<10} {'Trades':<10} {'Hits':<10} {'Hit Rate':<10}")
    print("-" * 40)

    for horizon in ["5", "10", "30", "60"]:
        stats = result.summary.hit_rates.get(horizon)
        if stats:
            hit_rate_str = format_hit_rate(stats.hit_rate)
            print(f"T+{horizon:<7} {stats.num_trades:<10} {stats.num_hits:<10} {hit_rate_str:<10}")

    # Event details (summary)
    print("\n" + "-" * 40)
    print("EVENTS SUMMARY")
    print("-" * 40)
    print(f"{'Date':<12} {'EPS':<8} {'Day0':<10} {'Signal':<8} {'Summary'}")
    print("-" * 40)

    for event in result.events[:5]:  # Show first 5 events
        eps_str = f"{event.eps:.2f}" if event.eps is not None else "N/A"
        day0_str = f"{event.day0_return:+.1%}" if event.day0_return is not None else "N/A"

        if event.signals:
            signal_score = event.signals.final_signal.score
            # Format 0-10 score with direction indicator
            if signal_score > 5.5:
                signal_str = f"{signal_score:.1f}+"  # bullish
            elif signal_score < 4.5:
                signal_str = f"{signal_score:.1f}-"  # bearish
            else:
                signal_str = f"{signal_score:.1f}"   # neutral
        else:
            signal_str = "N/A"

        summary = ""
        if event.semantic_features:
            summary = event.semantic_features.one_sentence_summary[:40] + "..."

        print(f"{event.earning_date:<12} {eps_str:<8} {day0_str:<10} {signal_str:<8} {summary}")

    if len(result.events) > 5:
        print(f"... and {len(result.events) - 5} more events")

    print("\n" + "=" * 60)


async def main():
    """Main entry point for CLI testing."""
    # Get ticker from command line or default to AAPL
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    ticker = ticker.upper()

    print(f"\nAnalyzing {ticker}...")
    print("This may take 1-2 minutes as we fetch data and run LLM analysis.\n")

    try:
        from app.earnings_logic import analyze_ticker

        result = await analyze_ticker(symbol=ticker, max_events=8)
        print_results(result)

    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        logging.exception("Analysis failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
