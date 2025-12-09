#!/usr/bin/env python3
"""
Top 20 Gainers & Losers Semantic Analysis
With concurrency limit (Semaphore=10), retry logic, and delays.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

import logging
logging.disable(logging.CRITICAL)

# Top 10 Gainers from PDF
TOP_GAINERS = [
    {'ticker': 'ORCL', 'date': '2025-09-09', 'time': 'AMC', 'change': 0.3595},
    {'ticker': 'IDXX', 'date': '2025-08-04', 'time': 'BMO', 'change': 0.2749},
    {'ticker': 'NRG', 'date': '2025-05-12', 'time': 'BMO', 'change': 0.2621},
    {'ticker': 'APP', 'date': '2025-02-12', 'time': 'AMC', 'change': 0.2402},
    {'ticker': 'PLTR', 'date': '2025-02-03', 'time': 'AMC', 'change': 0.2399},
    {'ticker': 'DAL', 'date': '2025-04-09', 'time': 'BMO', 'change': 0.2338},
    {'ticker': 'DDOG', 'date': '2025-11-06', 'time': 'BMO', 'change': 0.2313},
    {'ticker': 'WST', 'date': '2025-07-24', 'time': 'BMO', 'change': 0.2278},
    {'ticker': 'JBHT', 'date': '2025-10-15', 'time': 'AMC', 'change': 0.2214},
    {'ticker': 'PODD', 'date': '2025-05-08', 'time': 'AMC', 'change': 0.2088},
]

# Top 10 Losers from PDF
TOP_LOSERS = [
    {'ticker': 'FISV', 'date': '2025-10-29', 'time': 'BMO', 'change': -0.4404},
    {'ticker': 'TTD', 'date': '2025-08-07', 'time': 'AMC', 'change': -0.3861},
    {'ticker': 'WST', 'date': '2025-02-13', 'time': 'BMO', 'change': -0.3822},
    {'ticker': 'ALGN', 'date': '2025-07-30', 'time': 'AMC', 'change': -0.3663},
    {'ticker': 'SNPS', 'date': '2025-09-09', 'time': 'AMC', 'change': -0.3584},
    {'ticker': 'TTD', 'date': '2025-02-12', 'time': 'AMC', 'change': -0.3298},
    {'ticker': 'IT', 'date': '2025-08-05', 'time': 'BMO', 'change': -0.2755},
    {'ticker': 'SWKS', 'date': '2025-02-05', 'time': 'AMC', 'change': -0.2467},
    {'ticker': 'BAX', 'date': '2025-07-31', 'time': 'BMO', 'change': -0.2242},
    {'ticker': 'UNH', 'date': '2025-04-17', 'time': 'BMO', 'change': -0.2238},
]

# Concurrency settings
MAX_CONCURRENT = 10  # Semaphore limit
RETRY_COUNT = 3      # Number of retries
RETRY_DELAY = 2.0    # Delay between retries (seconds)
REQUEST_DELAY = 0.5  # Delay between starting tasks


async def analyze_one_with_retry(semaphore: asyncio.Semaphore, event: dict, category: str, idx: int, total: int) -> dict:
    """Analyze a single event with semaphore, retry logic, and delays."""
    from app.earnings_logic import analyze_ticker

    ticker = event['ticker']
    target_date = event['date']

    async with semaphore:
        for attempt in range(1, RETRY_COUNT + 1):
            try:
                print(f"  [{idx}/{total}] {ticker} ({target_date}) - attempt {attempt}...")

                result = await analyze_ticker(symbol=ticker, max_events=12)

                for e in result.events:
                    if e.earning_date == target_date:
                        if e.signals:
                            t10 = next((fr for fr in e.forward_returns if fr.horizon == 10), None)
                            t30 = next((fr for fr in e.forward_returns if fr.horizon == 30), None)
                            t60 = next((fr for fr in e.forward_returns if fr.horizon == 60), None)

                            print(f"       -> Signal: {e.signals.final_signal.score:.1f}")

                            return {
                                'ticker': ticker,
                                'date': target_date,
                                'category': category,
                                'pdf_change': event['change'],
                                'call_time': e.call_time,
                                'day0': e.day0_return,
                                'signal': e.signals.final_signal.score,
                                'explanation': e.signals.final_signal.explanation,
                                't10': t10.return_pct if t10 else None,
                                't10_hit': t10.hit if t10 else None,
                                't30': t30.return_pct if t30 else None,
                                't30_hit': t30.hit if t30 else None,
                                't60': t60.return_pct if t60 else None,
                                't60_hit': t60.hit if t60 else None,
                            }

                # Event not found
                print(f"       -> Event not found in analysis")
                return {'ticker': ticker, 'date': target_date, 'category': category, 'error': 'Event not found'}

            except Exception as ex:
                error_msg = str(ex)
                print(f"       -> Error (attempt {attempt}): {error_msg[:50]}")

                if attempt < RETRY_COUNT:
                    # Check if it's a rate limit error
                    if '429' in error_msg or 'rate' in error_msg.lower():
                        wait_time = RETRY_DELAY * attempt * 2  # Exponential backoff for rate limits
                        print(f"       -> Rate limit, waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        await asyncio.sleep(RETRY_DELAY)
                else:
                    return {'ticker': ticker, 'date': target_date, 'category': category, 'error': error_msg[:100]}

    return {'ticker': ticker, 'date': target_date, 'category': category, 'error': 'Unknown error'}


async def main():
    print('=' * 100)
    print('TOP 20 GAINERS & LOSERS SEMANTIC ANALYSIS (2025)')
    print(f'Concurrency: {MAX_CONCURRENT} | Retries: {RETRY_COUNT} | Delay: {REQUEST_DELAY}s')
    print('=' * 100)

    # Create semaphore for concurrency limit
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    # Build all events
    all_events = [(e, 'GAINER') for e in TOP_GAINERS] + [(e, 'LOSER') for e in TOP_LOSERS]
    total = len(all_events)

    print(f'\nAnalyzing {total} events with max {MAX_CONCURRENT} concurrent requests...\n')

    # Create tasks with staggered start
    tasks = []
    for idx, (event, category) in enumerate(all_events, 1):
        task = asyncio.create_task(
            analyze_one_with_retry(semaphore, event, category, idx, total)
        )
        tasks.append(task)
        await asyncio.sleep(REQUEST_DELAY)  # Stagger task starts

    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    valid_results = []
    for r in results:
        if isinstance(r, Exception):
            print(f"Task exception: {r}")
        elif isinstance(r, dict):
            valid_results.append(r)

    # Display results
    print('\n' + '=' * 100)
    print('TOP 10 GAINERS')
    print('=' * 100)
    print(f"{'Ticker':<8} {'Date':<12} {'Call':<8} {'PDF Day0':<10} {'Our Day0':<10} {'Signal':<10} {'T+10':<10} {'T+30':<10} {'T+60':<10}")
    print('-' * 100)

    gainers = [r for r in valid_results if r.get('category') == 'GAINER' and 'signal' in r]
    for r in gainers:
        score = r['signal']
        if score > 5.5:
            sig_str = f"{score:.1f} Bull"
        elif score < 4.5:
            sig_str = f"{score:.1f} Bear"
        else:
            sig_str = f"{score:.1f} Neut"

        pdf_day0 = f"{r['pdf_change']:+.1%}"
        our_day0 = f"{r['day0']:+.1%}" if r.get('day0') else 'N/A'
        t10_str = f"{r['t10']:+.1%}" if r.get('t10') is not None else 'N/A'
        t30_str = f"{r['t30']:+.1%}" if r.get('t30') is not None else 'N/A'
        t60_str = f"{r['t60']:+.1%}" if r.get('t60') is not None else 'N/A'

        print(f"{r['ticker']:<8} {r['date']:<12} {r['call_time']:<8} {pdf_day0:<10} {our_day0:<10} {sig_str:<10} {t10_str:<10} {t30_str:<10} {t60_str:<10}")

    missing_gainers = [r for r in valid_results if r.get('category') == 'GAINER' and 'error' in r]
    if missing_gainers:
        print(f"\nErrors: {[(r['ticker'], r.get('error', '')[:30]) for r in missing_gainers]}")

    print('\n' + '=' * 100)
    print('TOP 10 LOSERS')
    print('=' * 100)
    print(f"{'Ticker':<8} {'Date':<12} {'Call':<8} {'PDF Day0':<10} {'Our Day0':<10} {'Signal':<10} {'T+10':<10} {'T+30':<10} {'T+60':<10}")
    print('-' * 100)

    losers = [r for r in valid_results if r.get('category') == 'LOSER' and 'signal' in r]
    for r in losers:
        score = r['signal']
        if score > 5.5:
            sig_str = f"{score:.1f} Bull"
        elif score < 4.5:
            sig_str = f"{score:.1f} Bear"
        else:
            sig_str = f"{score:.1f} Neut"

        pdf_day0 = f"{r['pdf_change']:+.1%}"
        our_day0 = f"{r['day0']:+.1%}" if r.get('day0') else 'N/A'
        t10_str = f"{r['t10']:+.1%}" if r.get('t10') is not None else 'N/A'
        t30_str = f"{r['t30']:+.1%}" if r.get('t30') is not None else 'N/A'
        t60_str = f"{r['t60']:+.1%}" if r.get('t60') is not None else 'N/A'

        print(f"{r['ticker']:<8} {r['date']:<12} {r['call_time']:<8} {pdf_day0:<10} {our_day0:<10} {sig_str:<10} {t10_str:<10} {t30_str:<10} {t60_str:<10}")

    missing_losers = [r for r in valid_results if r.get('category') == 'LOSER' and 'error' in r]
    if missing_losers:
        print(f"\nErrors: {[(r['ticker'], r.get('error', '')[:30]) for r in missing_losers]}")

    # Day0 Comparison
    print('\n' + '=' * 100)
    print('DAY0 COMPARISON (PDF vs Our Calculation)')
    print('=' * 100)

    valid = [r for r in valid_results if 'signal' in r and r.get('day0') is not None]
    for r in valid:
        diff = abs(r['day0'] - r['pdf_change'])
        match = 'OK' if diff < 0.02 else 'DIFF'
        print(f"{r['ticker']:<8} {r['date']:<12} PDF: {r['pdf_change']:+.1%} vs Ours: {r['day0']:+.1%} [{match}]")

    # Signal Summary
    print('\n' + '=' * 100)
    print('SIGNAL SUMMARY')
    print('=' * 100)

    g_sig = [r for r in valid_results if r.get('category') == 'GAINER' and 'signal' in r]
    print(f"\nGAINERS ({len(g_sig)} analyzed):")
    print(f"  Bullish (>5.5): {len([r for r in g_sig if r['signal'] > 5.5])}")
    print(f"  Bearish (<4.5): {len([r for r in g_sig if r['signal'] < 4.5])}")
    print(f"  Neutral: {len([r for r in g_sig if 4.5 <= r['signal'] <= 5.5])}")
    for h in [10, 30, 60]:
        hits = sum(1 for r in g_sig if r.get(f't{h}_hit') is True)
        total_h = sum(1 for r in g_sig if r.get(f't{h}_hit') is not None)
        if total_h > 0:
            print(f"  T+{h} hit rate: {hits}/{total_h} ({hits/total_h*100:.0f}%)")

    l_sig = [r for r in valid_results if r.get('category') == 'LOSER' and 'signal' in r]
    print(f"\nLOSERS ({len(l_sig)} analyzed):")
    print(f"  Bullish (>5.5): {len([r for r in l_sig if r['signal'] > 5.5])}")
    print(f"  Bearish (<4.5): {len([r for r in l_sig if r['signal'] < 4.5])}")
    print(f"  Neutral: {len([r for r in l_sig if 4.5 <= r['signal'] <= 5.5])}")
    for h in [10, 30, 60]:
        hits = sum(1 for r in l_sig if r.get(f't{h}_hit') is True)
        total_h = sum(1 for r in l_sig if r.get(f't{h}_hit') is not None)
        if total_h > 0:
            print(f"  T+{h} hit rate: {hits}/{total_h} ({hits/total_h*100:.0f}%)")

    # Signal Explanations
    print('\n' + '=' * 100)
    print('SIGNAL EXPLANATIONS')
    print('=' * 100)

    for r in valid_results:
        if 'signal' not in r:
            continue
        direction = 'BULLISH' if r['signal'] > 5.5 else ('BEARISH' if r['signal'] < 4.5 else 'NEUTRAL')
        print(f"\n{r['ticker']} ({r['date']}) - Day0: {r.get('day0', 0):+.1%} | Signal: {r['signal']:.1f} {direction}")
        print(f"  Call: {r['call_time']} | Category: {r['category']}")
        print(f"  {r['explanation']}")


if __name__ == "__main__":
    asyncio.run(main())
