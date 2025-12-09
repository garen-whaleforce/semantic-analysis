"""
Test script for analyzing Top 10 Gainers + Top 10 Losers.

Analyzes the specified earnings events and outputs:
1. Console summary of results
2. CSV file with all signal analysis details
"""

import asyncio
import csv
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.fmp_client import (
    get_historical_earnings,
    get_price_history,
    get_transcript,
    get_transcript_dates,
    date_to_quarter,
    detect_call_time,
)
from app.db_client import (
    get_earnings_events_from_db,
    get_price_history_from_db,
    get_transcript_from_db,
)
from app.llm_client import extract_semantic_features, create_default_features
from app.earnings_logic import (
    calculate_all_signals,
    compute_day0_return,
    compute_forward_returns,
    find_price_index_on_or_after,
)
from app.models import EarningsRaw, EarningsEventWithTranscript

# Top 10 Gainers (2025-01-01 to 2025-12-01)
TOP_GAINERS = [
    ("ORCL", "2025-09-09", "+35.95%"),
    ("IDXX", "2025-08-04", "+27.49%"),
    ("NRG", "2025-05-12", "+26.21%"),
    ("APP", "2025-02-12", "+24.02%"),
    ("PLTR", "2025-02-03", "+23.99%"),
    ("DAL", "2025-04-09", "+23.38%"),
    ("DDOG", "2025-11-06", "+23.13%"),
    ("WST", "2025-07-24", "+22.78%"),
    ("JBHT", "2025-10-15", "+22.14%"),
    ("PODD", "2025-05-08", "+20.88%"),
]

# Top 10 Losers (2025-01-01 to 2025-12-01)
TOP_LOSERS = [
    ("FISV", "2025-10-29", "-44.04%"),
    ("TTD", "2025-08-07", "-38.61%"),
    ("WST", "2025-02-13", "-38.22%"),
    ("ALGN", "2025-07-30", "-36.63%"),
    ("SNPS", "2025-09-09", "-35.84%"),
    ("TTD", "2025-02-12", "-32.98%"),
    ("IT", "2025-08-05", "-27.55%"),
    ("SWKS", "2025-02-05", "-24.67%"),
    ("BAX", "2025-07-31", "-22.42%"),
    ("UNH", "2025-04-17", "-22.38%"),
]


async def analyze_single_event(
    symbol: str,
    event_date: str,
    expected_move: str,
    category: str
) -> dict:
    """Analyze a single earnings event."""
    print(f"\n{'='*60}")
    print(f"Analyzing {symbol} on {event_date} ({expected_move}) - {category}")
    print(f"{'='*60}")

    result = {
        "category": category,
        "symbol": symbol,
        "event_date": event_date,
        "expected_move": expected_move,
        "day0_return": None,
        "final_signal_score": None,
        "final_signal_direction": None,
        "tone_numbers_score": None,
        "prepared_qa_score": None,
        "regime_shift_score": None,
        "temp_struct_score": None,
        "analyst_skepticism_score": None,
        "t30_return": None,
        "t30_hit": None,
        "t60_return": None,
        "t60_hit": None,
        "one_sentence_summary": None,
        "error": None,
        # Additional LLM output fields
        "eps_strength": None,
        "revenue_strength": None,
        "overall_numbers_strength": None,
        "overall_tone": None,
        "prepared_tone": None,
        "qa_tone": None,
        "neg_temporary_ratio": None,
        "pos_temporary_ratio": None,
        "key_temporary_factors": None,
        "key_structural_factors": None,
        "skeptical_question_ratio": None,
        "followup_ratio": None,
        "topic_concentration": None,
        "risk_focus_score": None,
    }

    try:
        # Fetch price history
        prices = get_price_history_from_db(symbol)
        if not prices:
            prices = await get_price_history(symbol)

        if not prices:
            result["error"] = "No price data"
            return result

        # Fetch transcript dates to get fiscal year/quarter
        transcript_dates_list = await get_transcript_dates(symbol)
        transcript_date_lookup = {}
        for td in transcript_dates_list:
            td_date = td.get("date", "")
            td_year = td.get("fiscalYear") or td.get("year")
            td_quarter = td.get("quarter")
            if td_date and td_year and td_quarter:
                transcript_date_lookup[td_date] = (int(td_year), int(td_quarter))

        # Get fiscal year/quarter
        if event_date in transcript_date_lookup:
            year, quarter = transcript_date_lookup[event_date]
        else:
            year, quarter = date_to_quarter(event_date)

        print(f"  Fiscal: Q{quarter} {year}")

        # Fetch transcript
        transcript = get_transcript_from_db(symbol, year, quarter)
        if not transcript:
            transcript = await get_transcript(symbol, year, quarter)

        if not transcript:
            result["error"] = "No transcript"
            print(f"  WARNING: No transcript found")
            return result

        # Detect call time
        call_time = detect_call_time(transcript)
        print(f"  Call time: {call_time}")

        # Calculate day0 return
        day0_return = compute_day0_return(prices, event_date, call_time)
        if day0_return is None:
            result["error"] = "No day0 return"
            return result

        result["day0_return"] = day0_return
        print(f"  Day 0 Return: {day0_return:+.2%}")

        # Create event for LLM
        earning = EarningsRaw(
            date=event_date,
            symbol=symbol,
            eps=None,
            eps_estimated=None,
            revenue=None,
            revenue_estimated=None,
        )

        event_with_transcript = EarningsEventWithTranscript(
            symbol=symbol,
            earning_date=event_date,
            eps=None,
            eps_estimated=None,
            revenue=None,
            revenue_estimated=None,
            day0_return=day0_return,
            transcript=transcript,
            year=year,
            quarter=quarter
        )

        # Extract semantic features
        print(f"  Extracting semantic features...")
        features = await extract_semantic_features(event_with_transcript)
        result["one_sentence_summary"] = features.one_sentence_summary
        print(f"  Summary: {features.one_sentence_summary}")

        # Store all LLM output fields
        result["eps_strength"] = features.numbers.eps_strength
        result["revenue_strength"] = features.numbers.revenue_strength
        result["overall_numbers_strength"] = features.numbers.overall_numbers_strength
        result["overall_tone"] = features.tone.overall_tone
        result["prepared_tone"] = features.tone.prepared_tone
        result["qa_tone"] = features.tone.qa_tone
        result["neg_temporary_ratio"] = features.narrative.neg_temporary_ratio
        result["pos_temporary_ratio"] = features.narrative.pos_temporary_ratio
        result["key_temporary_factors"] = "; ".join(features.narrative.key_temporary_factors) if features.narrative.key_temporary_factors else ""
        result["key_structural_factors"] = "; ".join(features.narrative.key_structural_factors) if features.narrative.key_structural_factors else ""
        result["skeptical_question_ratio"] = features.skepticism.skeptical_question_ratio
        result["followup_ratio"] = features.skepticism.followup_ratio
        result["topic_concentration"] = features.skepticism.topic_concentration
        result["risk_focus_score"] = features.risk_focus_score

        # Calculate signals (no historical risk scores for single event)
        signals = calculate_all_signals(
            raw=earning,
            features=features,
            day0_return=day0_return,
            historical_risk_scores=[]
        )

        # Store signal scores
        result["tone_numbers_score"] = signals.tone_numbers.score
        result["prepared_qa_score"] = signals.prepared_vs_qa.score
        result["regime_shift_score"] = signals.regime_shift.score
        result["temp_struct_score"] = signals.temp_vs_struct.score
        result["analyst_skepticism_score"] = signals.analyst_skepticism.score
        result["final_signal_score"] = signals.final_signal.score

        # Determine direction
        if signals.final_signal.score > 5.5:
            result["final_signal_direction"] = "BULLISH"
        elif signals.final_signal.score < 4.5:
            result["final_signal_direction"] = "BEARISH"
        else:
            result["final_signal_direction"] = "NEUTRAL"

        print(f"  Final Signal: {result['final_signal_score']:.1f} ({result['final_signal_direction']})")
        print(f"    - Tone-Numbers: {signals.tone_numbers.score:.1f}")
        print(f"    - Prepared vs QA: {signals.prepared_vs_qa.score:.1f}")
        print(f"    - Regime Shift: {signals.regime_shift.score:.1f}")
        print(f"    - Temp vs Struct: {signals.temp_vs_struct.score:.1f}")
        print(f"    - Analyst Skepticism: {signals.analyst_skepticism.score:.1f}")

        # Calculate forward returns
        forward_returns = compute_forward_returns(
            prices=prices,
            event_date=event_date,
            final_signal_score=signals.final_signal.score,
            call_time=call_time,
            horizons=(30, 60)
        )

        for fr in forward_returns:
            if fr.horizon == 30:
                result["t30_return"] = fr.return_pct
                result["t30_hit"] = fr.hit
                print(f"  T+30: {fr.return_pct:+.2%} (Hit: {fr.hit})")
            elif fr.horizon == 60:
                result["t60_return"] = fr.return_pct
                result["t60_hit"] = fr.hit
                print(f"  T+60: {fr.return_pct:+.2%} (Hit: {fr.hit})")

    except Exception as e:
        result["error"] = str(e)
        print(f"  ERROR: {e}")

    return result


async def main():
    """Main entry point."""
    print("=" * 80)
    print("EXTREME MOVES ANALYSIS: Top 10 Gainers + Top 10 Losers")
    print("=" * 80)

    all_results = []

    def print_interim_summary(results, title):
        """Print interim summary table."""
        print(f"\n{'='*80}")
        print(f"INTERIM SUMMARY: {title}")
        print(f"{'='*80}")
        print(f"{'Symbol':<6} {'Date':<12} {'Day0':>8} {'Signal':<8} {'T+30':>8} {'T+60':>8} {'Hit'}")
        print("-" * 80)
        for r in results:
            d0 = f"{r['day0_return']:+.1%}" if r.get('day0_return') else "N/A"
            sig = r.get('final_signal_direction', 'N/A')[:4]
            t30 = f"{r['t30_return']:+.1%}" if r.get('t30_return') is not None else "N/A"
            t60 = f"{r['t60_return']:+.1%}" if r.get('t60_return') is not None else "N/A"
            hit30 = "✓" if r.get('t30_hit') == True else ("✗" if r.get('t30_hit') == False else "-")
            hit60 = "✓" if r.get('t60_hit') == True else ("✗" if r.get('t60_hit') == False else "-")
            print(f"{r['symbol']:<6} {r['event_date']:<12} {d0:>8} {sig:<8} {t30:>8} {t60:>8} {hit30}/{hit60}")

    # Analyze Top 10 Gainers
    print("\n" + "=" * 80)
    print("TOP 10 GAINERS")
    print("=" * 80)

    for i, (symbol, date, move) in enumerate(TOP_GAINERS):
        result = await analyze_single_event(symbol, date, move, "GAINER")
        all_results.append(result)
        # Print interim summary every 5 stocks
        if (i + 1) % 5 == 0:
            print_interim_summary([r for r in all_results if r["category"] == "GAINER"], f"Gainers ({i+1}/10)")

    # Analyze Top 10 Losers
    print("\n" + "=" * 80)
    print("TOP 10 LOSERS")
    print("=" * 80)

    for i, (symbol, date, move) in enumerate(TOP_LOSERS):
        result = await analyze_single_event(symbol, date, move, "LOSER")
        all_results.append(result)
        # Print interim summary every 5 stocks
        if (i + 1) % 5 == 0:
            print_interim_summary([r for r in all_results if r["category"] == "LOSER"], f"Losers ({i+1}/10)")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    # Count hits
    gainers_results = [r for r in all_results if r["category"] == "GAINER"]
    losers_results = [r for r in all_results if r["category"] == "LOSER"]

    print(f"\nGainers ({len(gainers_results)} events):")
    for r in gainers_results:
        direction = r.get("final_signal_direction", "N/A")
        t30 = f"{r['t30_return']:+.2%}" if r.get("t30_return") is not None else "N/A"
        t60 = f"{r['t60_return']:+.2%}" if r.get("t60_return") is not None else "N/A"
        print(f"  {r['symbol']:5} {r['event_date']} | Signal: {direction:8} | T+30: {t30:8} | T+60: {t60:8}")

    print(f"\nLosers ({len(losers_results)} events):")
    for r in losers_results:
        direction = r.get("final_signal_direction", "N/A")
        t30 = f"{r['t30_return']:+.2%}" if r.get("t30_return") is not None else "N/A"
        t60 = f"{r['t60_return']:+.2%}" if r.get("t60_return") is not None else "N/A"
        print(f"  {r['symbol']:5} {r['event_date']} | Signal: {direction:8} | T+30: {t30:8} | T+60: {t60:8}")

    # Hit rate analysis
    print("\n" + "=" * 80)
    print("HIT RATE ANALYSIS")
    print("=" * 80)

    # For gainers: bearish signal should predict negative returns (mean reversion)
    # For losers: bullish signal should predict positive returns (mean reversion)

    # T+30 analysis
    t30_trades = [r for r in all_results if r.get("t30_hit") is not None]
    t30_hits = sum(1 for r in t30_trades if r.get("t30_hit") == True)
    if t30_trades:
        print(f"\nT+30 Hit Rate: {t30_hits}/{len(t30_trades)} = {t30_hits/len(t30_trades):.1%}")

    # T+60 analysis
    t60_trades = [r for r in all_results if r.get("t60_hit") is not None]
    t60_hits = sum(1 for r in t60_trades if r.get("t60_hit") == True)
    if t60_trades:
        print(f"T+60 Hit Rate: {t60_hits}/{len(t60_trades)} = {t60_hits/len(t60_trades):.1%}")

    # Write CSV with all LLM output fields
    csv_path = Path(__file__).parent / "extreme_moves_results_v2.csv"
    fieldnames = [
        "category", "symbol", "event_date", "expected_move",
        "day0_return", "final_signal_score", "final_signal_direction",
        "tone_numbers_score", "prepared_qa_score", "regime_shift_score",
        "temp_struct_score", "analyst_skepticism_score",
        "t30_return", "t30_hit", "t60_return", "t60_hit",
        # All LLM output fields
        "eps_strength", "revenue_strength", "overall_numbers_strength",
        "overall_tone", "prepared_tone", "qa_tone",
        "neg_temporary_ratio", "pos_temporary_ratio",
        "key_temporary_factors", "key_structural_factors",
        "skeptical_question_ratio", "followup_ratio", "topic_concentration",
        "risk_focus_score",
        "one_sentence_summary", "error"
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in all_results:
            # Format percentages
            row = r.copy()
            if row.get("day0_return") is not None:
                row["day0_return"] = f"{row['day0_return']:.4f}"
            if row.get("t30_return") is not None:
                row["t30_return"] = f"{row['t30_return']:.4f}"
            if row.get("t60_return") is not None:
                row["t60_return"] = f"{row['t60_return']:.4f}"
            writer.writerow(row)

    print(f"\nResults saved to: {csv_path}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
