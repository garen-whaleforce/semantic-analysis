"""
Earnings Analysis Logic Module.

Implements the five semantic reversal signals and forward return calculations:
1. Tone-Numbers Divergence
2. Prepared vs. Q&A Asymmetry
3. Language Regime Shift
4. Temporary vs. Structural Story
5. Analyst Skepticism

Also calculates T+5/10/30/60 forward returns and hit rates.

Main entry point: analyze_ticker(symbol, max_events) -> TickerAnalysisResult
"""

import logging
from datetime import datetime
from typing import Optional, Sequence
from statistics import mean, stdev

from app.models import (
    EarningsRaw,
    SemanticFeatures,
    SingleSignal,
    AllSignals,
    PriceBar,
    ForwardReturn,
    HitRateStat,
    EarningsEventResult,
    EarningsEventWithTranscript,
    EventAnalysisStatus,
    SummaryStats,
    TickerAnalysisResult,
)

# Setup module logger
logger = logging.getLogger(__name__)

# =============================================================================
# Score Conversion Constants and Helpers
# =============================================================================

BASE_SCORE = 5.0  # Neutral score (center of 0-10 scale)


def _to_score(direction: int, strength: float) -> float:
    """
    Convert direction and strength to a 0-10 score.

    Args:
        direction: -1 (bearish), 0 (neutral), +1 (bullish)
        strength: 0.0 to 1.0 (intensity of the signal)

    Returns:
        Score from 0.0 to 10.0:
        - 0 = strong bearish reversal
        - 5 = neutral (no clear edge)
        - 10 = strong bullish reversal
    """
    if direction == 0 or strength <= 0:
        return BASE_SCORE
    strength = max(0.0, min(1.0, strength))
    score = BASE_SCORE + direction * strength * BASE_SCORE
    return max(0.0, min(10.0, score))


# =============================================================================
# Signal Calculation Functions
# =============================================================================

def calc_tone_numbers_divergence(
    features: SemanticFeatures,
    raw: EarningsRaw
) -> SingleSignal:
    """
    Signal 1: Tone-Numbers Divergence

    Detects when management tone doesn't match the headline numbers.

    Score: 0-10 scale
    - Good numbers + Bad tone => bearish reversal (score < 5)
    - Bad numbers + Good tone => bullish reversal (score > 5)
    - Otherwise => neutral (score = 5)
    """
    numbers_strength = features.numbers.overall_numbers_strength
    tone = features.tone.overall_tone

    direction = 0
    strength = 0.0
    explanation = f"Numbers and tone are broadly consistent (numbers={numbers_strength}, tone={tone}); no divergence."

    # Good numbers + bad tone => bearish reversal
    if numbers_strength >= 1 and tone <= -1:
        direction = -1
        strength = 1.0 if (numbers_strength >= 2 or tone <= -2) else 0.6
        explanation = (
            f"Strong numbers (strength={numbers_strength}) but negative tone ({tone}). "
            "This divergence can be a bearish reversal signal."
        )
    # Bad numbers + good tone => bullish reversal
    elif numbers_strength <= -1 and tone >= 1:
        direction = 1
        strength = 1.0 if (numbers_strength <= -2 or tone >= 2) else 0.6
        explanation = (
            f"Weak numbers (strength={numbers_strength}) but positive tone ({tone}). "
            "This divergence can be a bullish reversal signal."
        )

    score = _to_score(direction, strength)
    return SingleSignal(
        name="Tone-Numbers Divergence",
        score=score,
        explanation=explanation,
    )


def calc_prepared_vs_qa_asymmetry(
    features: SemanticFeatures,
    day0_return: float
) -> SingleSignal:
    """
    Signal 2: Prepared vs. Q&A Asymmetry

    Detects when Q&A tone differs significantly from prepared remarks,
    combined with stock price reaction.

    Score: 0-10 scale
    - Q&A worse than prepared + price up => bearish reversal (score < 5)
    - Q&A better than prepared + price down => bullish reversal (score > 5)
    - Otherwise => neutral (score = 5)
    """
    prepared = features.tone.prepared_tone
    qa = features.tone.qa_tone
    delta = qa - prepared

    direction = 0
    strength = 0.0
    explanation = f"Prepared remarks and Q&A tone are broadly aligned (delta={delta:+d}, return={day0_return:.1%})."

    # Bearish: Q&A worse, price up
    if delta <= -1 and day0_return > 0.05:
        direction = -1
        strong = (delta <= -1.5 and day0_return >= 0.10)
        strength = 1.0 if strong else 0.6
        explanation = (
            f"Q&A tone ({qa}) is meaningfully worse than prepared remarks ({prepared}) "
            f"while the stock jumped {day0_return:.1%} on earnings. "
            "Investors may be too optimistic; bearish reversal risk."
        )
    # Bullish: Q&A better, price down
    elif delta >= 1 and day0_return < -0.05:
        direction = 1
        strong = (delta >= 1.5 and day0_return <= -0.10)
        strength = 1.0 if strong else 0.6
        explanation = (
            f"Q&A tone ({qa}) is meaningfully better than prepared remarks ({prepared}) "
            f"while the stock sold off {day0_return:.1%} on earnings. "
            "Investors may be too pessimistic; bullish reversal opportunity."
        )

    score = _to_score(direction, strength)
    return SingleSignal(
        name="Prepared vs. Q&A Asymmetry",
        score=score,
        explanation=explanation,
    )


def calc_regime_shift(
    current_risk_score: int,
    historical_risk_scores: Sequence[int],
    day0_return: float,
    min_history: int = 4
) -> SingleSignal:
    """
    Signal 3: Language Regime Shift

    Detects sudden changes in risk language intensity compared to historical pattern.

    Score: 0-10 scale
    - Risk spike + price didn't fall => bearish (score < 5)
    - Risk drop + price didn't rise => bullish (score > 5)
    - Otherwise => neutral (score = 5)
    """
    if historical_risk_scores is None:
        historical_risk_scores = []

    if len(historical_risk_scores) < min_history:
        return SingleSignal(
            name="Language Regime Shift",
            score=BASE_SCORE,
            explanation=f"Insufficient history (< {min_history} events) to compute regime shift.",
        )

    try:
        hist_mean = mean(historical_risk_scores)
        hist_std = stdev(historical_risk_scores)
    except Exception:
        return SingleSignal(
            name="Language Regime Shift",
            score=BASE_SCORE,
            explanation="Unable to compute z-score for risk language (degenerate history).",
        )

    if hist_std == 0:
        return SingleSignal(
            name="Language Regime Shift",
            score=BASE_SCORE,
            explanation="Risk language history has zero variance; no detectable regime shift.",
        )

    z = (current_risk_score - hist_mean) / hist_std

    direction = 0
    strength = 0.0
    explanation = f"Risk language z-score is {z:.2f}, within normal range; no clear regime shift."

    if z >= 1.5 and day0_return >= 0:
        direction = -1
        strength = 1.0 if z >= 2.0 else 0.6
        explanation = (
            f"Risk language spiked (z={z:.2f}) compared to history, "
            f"yet the stock did not fall (Day 0 return {day0_return:.1%}). "
            "Rising risk but complacent price -> bearish."
        )
    elif z <= -1.5 and day0_return <= 0:
        direction = 1
        strength = 1.0 if z <= -2.0 else 0.6
        explanation = (
            f"Risk language dropped sharply (z={z:.2f}) compared to history, "
            f"yet the stock did not rally (Day 0 return {day0_return:.1%}). "
            "Falling risk but depressed price -> bullish."
        )

    score = _to_score(direction, strength)
    return SingleSignal(
        name="Language Regime Shift",
        score=score,
        explanation=explanation,
    )


def calc_temp_vs_struct(
    features: SemanticFeatures,
    raw: EarningsRaw
) -> SingleSignal:
    """
    Signal 4: Temporary vs. Structural Story

    Analyzes whether management attributes results to temporary or structural factors.

    Score: 0-10 scale
    - EPS miss + high neg_temporary_ratio => bullish (score > 5)
    - EPS beat + high pos_temporary_ratio => bearish (score < 5)
    - Otherwise => neutral (score = 5)
    """
    eps = raw.eps
    eps_est = raw.eps_estimated

    # Handle missing data
    if eps is None or eps_est is None:
        return SingleSignal(
            name="Temporary vs. Structural Story",
            score=BASE_SCORE,
            explanation="EPS actual/estimate not available; cannot compute EPS surprise.",
        )

    eps_surprise = eps - eps_est
    neg_temp = features.narrative.neg_temporary_ratio
    pos_temp = features.narrative.pos_temporary_ratio

    direction = 0
    strength = 0.0
    explanation = f"Temporary vs structural narrative is balanced (EPS surprise={eps_surprise:+.2f}, neg_temp={neg_temp:.0%}, pos_temp={pos_temp:.0%}); no clear asymmetry."

    # EPS miss, most negatives temporary => bullish
    if eps_surprise < 0 and neg_temp >= 0.7:
        direction = 1
        strength = 1.0 if neg_temp >= 0.85 else 0.6
        explanation = (
            f"EPS missed expectations (surprise {eps_surprise:+.2f}), but about "
            f"{neg_temp:.0%} of negative factors are described as temporary. "
            "Likely downside overreaction -> bullish."
        )
    # EPS beat, most positives temporary => bearish
    elif eps_surprise > 0 and pos_temp >= 0.7:
        direction = -1
        strength = 1.0 if pos_temp >= 0.85 else 0.6
        explanation = (
            f"EPS beat expectations (surprise {eps_surprise:+.2f}), but about "
            f"{pos_temp:.0%} of positive factors are described as temporary. "
            "Likely upside overreaction -> bearish."
        )

    score = _to_score(direction, strength)
    return SingleSignal(
        name="Temporary vs. Structural Story",
        score=score,
        explanation=explanation,
    )


def calc_analyst_skepticism(
    features: SemanticFeatures,
    day0_return: float
) -> SingleSignal:
    """
    Signal 5: Analyst Skepticism

    Detects disconnect between analyst questioning behavior and stock price reaction.

    Score: 0-10 scale
    - Price up + high skepticism => bearish reversal (score < 5)
    - Price down + low skepticism => bullish reversal (score > 5)
    - Otherwise => neutral (score = 5)
    """
    skepticism = features.skepticism.skeptical_question_ratio

    direction = 0
    strength = 0.0
    explanation = f"Analyst skepticism is not in clear conflict with the price move (return={day0_return:.1%}, skepticism={skepticism:.0%})."

    # price up, high skepticism => bearish
    if day0_return > 0.05 and skepticism >= 0.4:
        direction = -1
        strong = (day0_return >= 0.10 and skepticism >= 0.6)
        strength = 1.0 if strong else 0.6
        explanation = (
            f"The stock jumped {day0_return:.1%} on earnings, "
            f"but about {skepticism:.0%} of analyst questions were skeptical. "
            "Rally despite doubts -> bearish reversal risk."
        )
    # price down, low skepticism => bullish
    elif day0_return < -0.05 and skepticism <= 0.2:
        direction = 1
        strong = (day0_return <= -0.10 and skepticism <= 0.1)
        strength = 1.0 if strong else 0.6
        explanation = (
            f"The stock sold off {day0_return:.1%} on earnings, "
            f"but only about {skepticism:.0%} of analyst questions were skeptical. "
            "Selloff despite calm analysts -> bullish reversal opportunity."
        )

    score = _to_score(direction, strength)
    return SingleSignal(
        name="Analyst Skepticism",
        score=score,
        explanation=explanation,
    )


def calc_final_signal(signals: list[SingleSignal]) -> SingleSignal:
    """
    Aggregate individual signals into final trading signal.

    Each sub-signal score is converted to a signed value in [-1, 1]:
        signed_i = (score_i - 5) / 5

    Then summed: raw_sum in [-5, 5] for 5 signals.

    Final score = 5 + raw_sum, clamped to [0, 10].
    """
    valid = [s for s in signals if s is not None]
    if not valid:
        return SingleSignal(
            name="Final Signal",
            score=BASE_SCORE,
            explanation="No valid semantic signals available.",
        )

    # Convert each 0-10 score to signed value in [-1, 1]
    signed_values = [(s.score - BASE_SCORE) / BASE_SCORE for s in valid]
    raw_sum = sum(signed_values)

    final_score = 5.0 + raw_sum
    final_score = max(0.0, min(10.0, final_score))

    # Collect which signals are bullish/bearish for explanation
    bullish = [s.name for s in valid if s.score > 5.5]
    bearish = [s.name for s in valid if s.score < 4.5]

    direction = "bullish" if final_score > 5.5 else "bearish" if final_score < 4.5 else "neutral"

    if bullish and bearish:
        explanation = (
            f"Aggregate semantic score is {final_score:.1f} ({direction}); "
            f"raw sum = {raw_sum:+.2f}. "
            f"Bullish: {', '.join(bullish)}. Bearish: {', '.join(bearish)}."
        )
    elif bullish:
        explanation = (
            f"Aggregate semantic score is {final_score:.1f} ({direction}); "
            f"raw sum = {raw_sum:+.2f}. "
            f"Bullish signals: {', '.join(bullish)}."
        )
    elif bearish:
        explanation = (
            f"Aggregate semantic score is {final_score:.1f} ({direction}); "
            f"raw sum = {raw_sum:+.2f}. "
            f"Bearish signals: {', '.join(bearish)}."
        )
    else:
        explanation = (
            f"Aggregate semantic score is {final_score:.1f} ({direction}); "
            f"raw sum = {raw_sum:+.2f}. No strong individual signals."
        )

    return SingleSignal(
        name="Final Signal",
        score=final_score,
        explanation=explanation,
    )


def calculate_all_signals(
    raw: EarningsRaw,
    features: SemanticFeatures,
    day0_return: float,
    historical_risk_scores: list[int]
) -> AllSignals:
    """
    Calculate all five signals plus final aggregated signal.

    Args:
        raw: Raw earnings data (EPS, revenue, etc.)
        features: Semantic features from LLM
        day0_return: Stock return on earnings day
        historical_risk_scores: Risk scores from previous quarters (for regime shift)

    Returns:
        AllSignals object containing all signal calculations
    """
    # Calculate individual signals
    tone_numbers = calc_tone_numbers_divergence(features, raw)
    prepared_vs_qa = calc_prepared_vs_qa_asymmetry(features, day0_return)
    regime_shift = calc_regime_shift(
        features.risk_focus_score,
        historical_risk_scores,
        day0_return
    )
    temp_vs_struct = calc_temp_vs_struct(features, raw)
    analyst_skepticism = calc_analyst_skepticism(features, day0_return)

    # Calculate final signal from the five individual signals
    individual_signals = [
        tone_numbers,
        prepared_vs_qa,
        regime_shift,
        temp_vs_struct,
        analyst_skepticism
    ]
    final = calc_final_signal(individual_signals)

    return AllSignals(
        tone_numbers=tone_numbers,
        prepared_vs_qa=prepared_vs_qa,
        regime_shift=regime_shift,
        temp_vs_struct=temp_vs_struct,
        analyst_skepticism=analyst_skepticism,
        final_signal=final
    )


# =============================================================================
# Price and Return Calculations
# =============================================================================

def find_price_index_on_or_after(prices: list[PriceBar], target_date: str) -> Optional[int]:
    """
    Find the index of the first price bar on or after target_date.

    Args:
        prices: List of PriceBar sorted by date ascending
        target_date: Target date string (YYYY-MM-DD)

    Returns:
        Index in prices list, or None if not found
    """
    for i, bar in enumerate(prices):
        if bar.date >= target_date:
            return i
    return None


def find_price_index_before(prices: list[PriceBar], target_date: str) -> Optional[int]:
    """
    Find the index of the last price bar before target_date.

    Args:
        prices: List of PriceBar sorted by date ascending
        target_date: Target date string (YYYY-MM-DD)

    Returns:
        Index in prices list, or None if not found
    """
    result = None
    for i, bar in enumerate(prices):
        if bar.date < target_date:
            result = i
        else:
            break
    return result


def compute_day0_return(
    prices: list[PriceBar],
    event_date: str,
    call_time: str = "unknown"
) -> Optional[float]:
    """
    Compute the Day 0 return (pre-announcement close to post-announcement close).

    The T0 definition depends on call_time:
    - BMO (before market open): T0 = event_date (market reacts same day)
    - AMC (after market close): T0 = next trading day (market reacts next day)
    - unknown: defaults to event_date (same as BMO)

    For BMO:
        T-1: Last trading day before event_date
        T0: event_date
    For AMC:
        T-1: event_date (close before announcement)
        T0: First trading day after event_date

    Return = (Close_T0 - Close_T-1) / Close_T-1

    Args:
        prices: List of PriceBar sorted by date ascending
        event_date: Earnings announcement date (YYYY-MM-DD)
        call_time: "BMO", "AMC", or "unknown"

    Returns:
        Day 0 return as decimal, or None if prices not available
    """
    if call_time == "AMC":
        # AMC: T-1 is event_date, T0 is next trading day
        t_minus_1_idx = find_price_index_on_or_after(prices, event_date)
        if t_minus_1_idx is None or t_minus_1_idx + 1 >= len(prices):
            return None
        t0_idx = t_minus_1_idx + 1
    else:
        # BMO or unknown: T-1 is day before event_date, T0 is event_date
        t_minus_1_idx = find_price_index_before(prices, event_date)
        t0_idx = find_price_index_on_or_after(prices, event_date)

    if t_minus_1_idx is None or t0_idx is None:
        return None

    p_before = prices[t_minus_1_idx].close
    p_after = prices[t0_idx].close

    if p_before <= 0:
        return None

    return (p_after - p_before) / p_before


def compute_forward_returns(
    prices: list[PriceBar],
    event_date: str,
    final_signal_score: float,
    call_time: str = "unknown",
    horizons: tuple[int, ...] = (5, 10, 30, 60)
) -> list[ForwardReturn]:
    """
    Compute forward returns at specified horizons.

    The T0 definition depends on call_time:
    - BMO (before market open): T0 = event_date (market reacts same day)
    - AMC (after market close): T0 = next trading day (market reacts next day)
    - unknown: defaults to event_date (same as BMO)

    T+N is the N-th trading day after T0.

    Args:
        prices: List of PriceBar sorted by date ascending
        event_date: Earnings announcement date (YYYY-MM-DD)
        final_signal_score: Final signal score (0-10 scale) for hit calculation
        call_time: "BMO", "AMC", or "unknown"
        horizons: Tuple of horizon days to compute

    Returns:
        List of ForwardReturn objects for each horizon
    """
    if call_time == "AMC":
        # AMC: T0 is the next trading day after event_date
        event_idx = find_price_index_on_or_after(prices, event_date)
        if event_idx is None or event_idx + 1 >= len(prices):
            return []
        t0_idx = event_idx + 1
    else:
        # BMO or unknown: T0 is event_date
        t0_idx = find_price_index_on_or_after(prices, event_date)

    if t0_idx is None:
        return []

    results: list[ForwardReturn] = []

    for horizon in horizons:
        end_idx = t0_idx + horizon

        if end_idx >= len(prices):
            # Not enough data for this horizon
            continue

        start_bar = prices[t0_idx]
        end_bar = prices[end_idx]

        if start_bar.close <= 0:
            continue

        return_pct = (end_bar.close - start_bar.close) / start_bar.close

        # Determine hit using 0-10 scale:
        # score > 5.5 = bullish, score < 4.5 = bearish, otherwise neutral
        if 4.5 <= final_signal_score <= 5.5:
            # Neutral signal - no trade
            hit = None
        elif (final_signal_score > 5.5 and return_pct > 0) or (final_signal_score < 4.5 and return_pct < 0):
            hit = True
        else:
            hit = False

        results.append(ForwardReturn(
            horizon=horizon,
            start_date=start_bar.date,
            end_date=end_bar.date,
            return_pct=return_pct,
            hit=hit
        ))

    return results


def compute_summary_hit_rates(
    all_forward_returns: list[list[ForwardReturn]]
) -> dict[str, HitRateStat]:
    """
    Compute aggregate hit rates across all events for each horizon.

    Args:
        all_forward_returns: List of ForwardReturn lists (one per event)

    Returns:
        Dictionary mapping horizon (as string) to HitRateStat
    """
    # Collect all returns by horizon
    by_horizon: dict[int, list[ForwardReturn]] = {}
    for event_returns in all_forward_returns:
        for fr in event_returns:
            if fr.horizon not in by_horizon:
                by_horizon[fr.horizon] = []
            by_horizon[fr.horizon].append(fr)

    # Calculate hit rates
    result: dict[str, HitRateStat] = {}

    for horizon in [5, 10, 30, 60]:
        returns = by_horizon.get(horizon, [])

        # Only count trades where hit is not None (signal != 0)
        valid_trades = [fr for fr in returns if fr.hit is not None]
        num_trades = len(valid_trades)
        num_hits = sum(1 for fr in valid_trades if fr.hit is True)

        hit_rate = (num_hits / num_trades) if num_trades > 0 else None

        result[str(horizon)] = HitRateStat(
            num_trades=num_trades,
            num_hits=num_hits,
            hit_rate=hit_rate
        )

    return result


# =============================================================================
# High-Level Analysis Function
# =============================================================================

async def analyze_ticker(symbol: str, max_events: int = 8) -> TickerAnalysisResult:
    """
    High-level function to analyze a single ticker's earnings history.

    This is the main entry point for the analysis pipeline:
    1. Fetch historical earnings data (DB first, FMP fallback)
    2. Fetch price history (DB first, FMP fallback)
    3. For each earnings event:
       - Fetch transcript (DB first, FMP fallback)
       - Call LLM to extract semantic features
       - Calculate day0 return
       - Calculate five signals + final signal
       - Calculate T+5/10/30/60 forward returns
    4. Compute summary hit rates

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
        max_events: Maximum number of recent earnings events to analyze

    Returns:
        TickerAnalysisResult with all events and summary statistics

    Raises:
        ValueError: If no earnings data found or all events failed
    """
    # Import here to avoid circular imports
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

    symbol = symbol.upper().strip()
    logger.info(f"Starting analysis for ticker: {symbol}")

    # Step 1: Fetch earnings history (DB first, then FMP)
    logger.info(f"Fetching earnings history for {symbol}")
    db_events = get_earnings_events_from_db(symbol, limit=max_events)

    if db_events:
        logger.info(f"Using DB: found {len(db_events)} earnings events for {symbol}")
        # Convert DB events to EarningsRaw format
        earnings_list = []
        for ev in db_events:
            earning_date = str(ev.get('earning_date', '')) if ev.get('earning_date') else None
            if earning_date:
                earnings_list.append(EarningsRaw(
                    date=earning_date,
                    symbol=symbol,
                    eps=None,  # DB doesn't have EPS estimates
                    eps_estimated=None,
                    revenue=None,
                    revenue_estimated=None,
                ))
    else:
        # Fallback to FMP
        logger.info(f"DB empty, falling back to FMP for {symbol}")
        try:
            earnings_list = await get_historical_earnings(symbol, limit=max_events)
        except Exception as e:
            logger.error(f"Failed to fetch earnings for {symbol}: {e}")
            raise ValueError(f"Failed to fetch earnings data for {symbol}: {e}")

    if not earnings_list:
        logger.warning(f"No earnings data found for {symbol}")
        raise ValueError(f"No earnings data found for ticker: {symbol}")

    total_events_found = len(earnings_list)
    logger.info(f"Found {total_events_found} earnings events for {symbol}")

    # Step 2: Fetch price history (DB first, then FMP)
    logger.info(f"Fetching price history for {symbol}")
    prices = get_price_history_from_db(symbol)

    if not prices:
        # Fallback to FMP
        logger.info(f"DB prices empty, falling back to FMP for {symbol}")
        try:
            prices = await get_price_history(symbol)
        except Exception as e:
            logger.error(f"Failed to fetch prices for {symbol}: {e}")
            raise ValueError(f"Failed to fetch price data for {symbol}: {e}")

    if not prices:
        logger.warning(f"No price data found for {symbol}")
        raise ValueError(f"No price data found for ticker: {symbol}")

    logger.info(f"Using {len(prices)} price bars for {symbol}")

    # Sort earnings by date (oldest first for regime shift calculation)
    earnings_list.sort(key=lambda x: x.date)

    # Step 2.5: Fetch transcript dates once to build fiscal year/quarter lookup
    # This is needed because FMP uses fiscal quarters, not calendar quarters
    logger.info(f"Fetching transcript dates for {symbol}")
    try:
        transcript_dates_list = await get_transcript_dates(symbol)
    except Exception as e:
        logger.warning(f"Failed to fetch transcript dates for {symbol}: {e}")
        transcript_dates_list = []

    # Build lookup: earning_date -> (fiscal_year, fiscal_quarter)
    # FMP transcript dates format: {'quarter': 3, 'fiscalYear': 2025, 'date': '2025-11-06'}
    transcript_date_lookup: dict[str, tuple[int, int]] = {}
    for td in transcript_dates_list:
        td_date = td.get("date", "")
        td_year = td.get("fiscalYear") or td.get("year")
        td_quarter = td.get("quarter")
        if td_date and td_year and td_quarter:
            transcript_date_lookup[td_date] = (int(td_year), int(td_quarter))

    logger.info(f"Found {len(transcript_date_lookup)} transcript dates for {symbol}")

    # Step 3: Process each earnings event
    events: list[EarningsEventResult] = []
    all_forward_returns: list[list[ForwardReturn]] = []
    historical_risk_scores: list[int] = []
    events_with_signals = 0

    for i, earning in enumerate(earnings_list):
        event_num = i + 1
        logger.info(f"Processing earnings event {event_num}/{len(earnings_list)}: {earning.date}")

        # Get fiscal year and quarter for transcript lookup
        # First try exact match from transcript dates, then fallback to calendar quarter
        if earning.date in transcript_date_lookup:
            year, quarter = transcript_date_lookup[earning.date]
            logger.info(f"Using fiscal year/quarter from transcript dates: {year} Q{quarter}")
        else:
            # Fallback to calendar-based quarter (may not find transcript)
            year, quarter = date_to_quarter(earning.date)
            logger.info(f"No transcript date match, using calendar quarter: {year} Q{quarter}")

        # Initialize event result with basic info
        event_result = EarningsEventResult(
            earning_date=earning.date,
            year=year,
            quarter=quarter,
            eps=earning.eps,
            eps_estimate=earning.eps_estimated,
            revenue=earning.revenue,
            revenue_estimate=earning.revenue_estimated,
            status=EventAnalysisStatus()
        )

        # Fetch transcript FIRST to detect call_time (needed for day0 calculation)
        transcript = get_transcript_from_db(symbol, year, quarter)
        if not transcript:
            # Fallback to FMP
            try:
                transcript = await get_transcript(symbol, year, quarter)
            except Exception as e:
                logger.warning(f"Failed to fetch transcript for {earning.date}: {e}")
                transcript = None

        # Detect call time from transcript (needed for correct day0 calculation)
        call_time = "unknown"
        if transcript:
            call_time = detect_call_time(transcript)
            event_result.call_time = call_time

        # Calculate day0 return using call_time for correct T0 definition
        day0_return = compute_day0_return(prices, earning.date, call_time)
        if day0_return is None:
            logger.warning(f"Could not calculate day0 return for {earning.date}, skipping signal analysis")
            event_result.status.success = False
            event_result.status.error_message = "Could not calculate day0 return (missing price data)"
            events.append(event_result)
            continue

        event_result.day0_return = day0_return

        if not transcript:
            logger.warning(f"No transcript available for {earning.date} Q{quarter} {year}")
            event_result.status.transcript_available = False
            # Use default features and continue
            features = create_default_features()
            event_result.status.llm_success = False
        else:
            # call_time already detected above
            # Create event with transcript for LLM analysis
            event_with_transcript = EarningsEventWithTranscript(
                symbol=symbol,
                earning_date=earning.date,
                eps=earning.eps,
                eps_estimated=earning.eps_estimated,
                revenue=earning.revenue,
                revenue_estimated=earning.revenue_estimated,
                day0_return=day0_return,
                transcript=transcript,
                year=year,
                quarter=quarter
            )

            # Extract semantic features using Azure OpenAI
            try:
                logger.info(f"Extracting semantic features for {earning.date}")
                features = await extract_semantic_features(event_with_transcript)
            except Exception as e:
                logger.error(f"LLM extraction failed for {earning.date}: {e}")
                event_result.status.llm_success = False
                event_result.status.error_message = f"LLM analysis failed: {str(e)}"
                features = create_default_features()

        event_result.semantic_features = features

        # Calculate signals
        signals = calculate_all_signals(
            raw=earning,
            features=features,
            day0_return=day0_return,
            historical_risk_scores=historical_risk_scores.copy()
        )
        event_result.signals = signals

        # Track if this event has a non-neutral signal (outside 4.5-5.5 range)
        if signals.final_signal.score < 4.5 or signals.final_signal.score > 5.5:
            events_with_signals += 1

        # Add current risk score to history for future events
        historical_risk_scores.append(features.risk_focus_score)

        # Calculate forward returns (using call_time for correct T0 definition)
        forward_returns = compute_forward_returns(
            prices=prices,
            event_date=earning.date,
            final_signal_score=signals.final_signal.score,
            call_time=call_time
        )
        event_result.forward_returns = forward_returns
        all_forward_returns.append(forward_returns)

        events.append(event_result)

    events_analyzed = len([e for e in events if e.signals is not None])

    if events_analyzed == 0:
        logger.error(f"Could not analyze any events for {symbol}")
        raise ValueError(f"Could not process any earnings events for ticker: {symbol}")

    # Sort events by date (most recent first) for display
    events.sort(key=lambda x: x.earning_date, reverse=True)

    # Compute summary hit rates
    hit_rates = compute_summary_hit_rates(all_forward_returns)

    logger.info(
        f"Analysis complete for {symbol}: "
        f"{events_analyzed}/{total_events_found} events analyzed, "
        f"{events_with_signals} with signals"
    )

    return TickerAnalysisResult(
        ticker=symbol,
        events=events,
        summary=SummaryStats(hit_rates=hit_rates),
        total_events_found=total_events_found,
        events_analyzed=events_analyzed,
        events_with_signals=events_with_signals
    )
