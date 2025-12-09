"""
FMP (Financial Modeling Prep) API Client.

Provides functions to fetch:
- Historical earnings data (EPS/Revenue estimates and actuals)
- Historical stock prices
- Earnings call transcripts

All endpoints use the stable API base URL.
"""

import httpx
from typing import Optional
from datetime import datetime

from app.config import get_settings
from app.models import EarningsRaw, PriceBar
from app.fmp_endpoints import FMP_BASE_URL, ENDPOINTS, get_url


async def get_historical_earnings(symbol: str, limit: int = 8) -> list[EarningsRaw]:
    """
    Fetch historical earnings data for a symbol.

    Uses FMP stable endpoint: /stable/earnings

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
        limit: Maximum number of earnings events to retrieve

    Returns:
        List of EarningsRaw objects sorted by date (most recent first)

    Note: FMP field names may vary. Current implementation handles:
        - eps / epsEstimated
        - revenue / revenueEstimated
        Adjust field access if FMP response structure changes.
    """
    settings = get_settings()
    url = get_url("earnings")

    params = {
        "symbol": symbol,
        "limit": limit,
        "apikey": settings.fmp_api_key
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    if not isinstance(data, list):
        return []

    earnings_list: list[EarningsRaw] = []
    for item in data:
        try:
            # FMP stable/earnings uses: epsActual, epsEstimated, revenueActual, revenueEstimated
            earnings = EarningsRaw(
                date=item.get("date", ""),
                symbol=item.get("symbol", symbol),
                eps=item.get("epsActual") or item.get("eps"),
                eps_estimated=item.get("epsEstimated"),
                revenue=item.get("revenueActual") or item.get("revenue"),
                revenue_estimated=item.get("revenueEstimated")
            )
            # Only include entries with valid dates and at least some actual data
            if earnings.date and (earnings.eps is not None or earnings.revenue is not None):
                earnings_list.append(earnings)
        except Exception:
            # Skip malformed entries
            continue

    return earnings_list


async def get_price_history(symbol: str) -> list[PriceBar]:
    """
    Fetch historical daily price data for a symbol.

    Uses FMP stable endpoint: /stable/historical-price-eod/full

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")

    Returns:
        List of PriceBar objects sorted by date (oldest first for easier processing)
    """
    settings = get_settings()
    url = get_url("historical_price_eod_full")

    params = {
        "symbol": symbol,
        "apikey": settings.fmp_api_key
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    # Stable endpoint returns array directly or may have "historical" wrapper
    if isinstance(data, dict):
        historical = data.get("historical", [])
    elif isinstance(data, list):
        historical = data
    else:
        return []

    if not isinstance(historical, list):
        return []

    price_bars: list[PriceBar] = []
    for item in historical:
        try:
            bar = PriceBar(
                date=item.get("date", ""),
                open=float(item.get("open", 0)),
                high=float(item.get("high", 0)),
                low=float(item.get("low", 0)),
                close=float(item.get("close", 0)),
                volume=item.get("volume")
            )
            if bar.date and bar.close > 0:
                price_bars.append(bar)
        except (ValueError, TypeError):
            continue

    # Sort by date ascending (oldest first) for forward return calculations
    price_bars.sort(key=lambda x: x.date)

    return price_bars


async def get_transcript(symbol: str, year: int, quarter: int) -> Optional[str]:
    """
    Fetch earnings call transcript for a specific quarter.

    Uses FMP stable endpoint: /stable/earning-call-transcript

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
        year: Fiscal year (e.g., 2023)
        quarter: Fiscal quarter (1-4)

    Returns:
        Full transcript text if available, None otherwise

    Note: FMP may use different field names for transcript content.
        Current implementation checks: content, transcript, text
    """
    settings = get_settings()
    url = get_url("earning_call_transcript")

    params = {
        "symbol": symbol,
        "year": year,
        "quarter": quarter,
        "apikey": settings.fmp_api_key
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    # Response is typically a list with one item
    if not isinstance(data, list) or len(data) == 0:
        return None

    item = data[0]

    # Try different possible field names for transcript content
    transcript = (
        item.get("content") or
        item.get("transcript") or
        item.get("text") or
        None
    )

    return transcript


async def get_transcript_dates(symbol: str) -> list[dict]:
    """
    Get available transcript dates for a symbol.

    Uses FMP stable endpoint: /stable/earning-call-transcript-dates

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")

    Returns:
        List of available transcript info with year, quarter, date
    """
    settings = get_settings()
    url = get_url("earning_call_transcript_dates")

    params = {
        "symbol": symbol,
        "apikey": settings.fmp_api_key
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    if not isinstance(data, list):
        return []

    return data


async def get_company_profile(symbol: str) -> Optional[dict]:
    """
    Fetch company profile information.

    Uses FMP stable endpoint: /stable/profile

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")

    Returns:
        Company profile dict or None if not found
    """
    settings = get_settings()
    url = get_url("profile")

    params = {
        "symbol": symbol,
        "apikey": settings.fmp_api_key
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    if isinstance(data, list) and len(data) > 0:
        return data[0]
    elif isinstance(data, dict):
        return data

    return None


def detect_call_time(transcript: str) -> str:
    """
    Detect if earnings call was pre-market or after-market.

    Detection strategy:
    1. First check intro (first 5000 chars) for strong signals
    2. If unknown, search entire transcript for analyst greetings in Q&A

    Args:
        transcript: Full transcript text

    Returns:
        "BMO" (before market open), "AMC" (after market close), or "unknown"
    """
    import re

    if not transcript:
        return "unknown"

    # Check first 5000 chars (greeting/time may come after operator intro and disclaimers)
    intro = transcript[:5000].lower()

    # Priority 1: Traditional greetings in intro (most reliable)
    if "good morning" in intro:
        return "BMO"
    if "good afternoon" in intro or "good evening" in intro:
        return "AMC"

    # Priority 2: Time patterns like "8:00 a.m." or "4:30 p.m."
    # Match patterns: "8:00 a.m.", "8 a.m.", "08:30 am", "4:30 p.m.", etc.
    time_pattern = r'\b(\d{1,2}):?(\d{2})?\s*(a\.?m\.?|p\.?m\.?)\b'
    time_matches = re.findall(time_pattern, intro)

    for match in time_matches:
        hour = int(match[0])
        am_pm = match[2].replace('.', '').lower()

        if am_pm.startswith('a'):
            # AM times: before noon -> BMO
            if 5 <= hour <= 11:
                return "BMO"
        else:
            # PM times: after 4pm typically -> AMC
            # Note: 12pm-3pm could be either, skip those
            if hour >= 4 or hour == 12:
                # 4pm, 5pm, etc. or 12pm (noon calls are rare)
                if hour >= 4 and hour != 12:
                    return "AMC"

    # Priority 3: Contextual phrases in intro
    if "this morning" in intro:
        return "BMO"
    if "this afternoon" in intro or "this evening" in intro:
        return "AMC"

    # Priority 4: Check for common conference call time phrases
    # "after the close", "after market", "after hours" -> AMC
    if "after the close" in intro or "after market" in intro or "after hours" in intro:
        return "AMC"
    # "before the open", "pre-market" -> BMO
    if "before the open" in intro or "pre-market" in intro or "premarket" in intro:
        return "BMO"

    # Priority 5: Search ENTIRE transcript for analyst greetings in Q&A
    # Analysts often say "Good afternoon" or "Good morning" when starting their questions
    full_text = transcript.lower()

    morning_count = full_text.count("good morning")
    afternoon_count = full_text.count("good afternoon")
    evening_count = full_text.count("good evening")

    # If we found greetings anywhere in transcript, use majority vote
    total_bmo = morning_count
    total_amc = afternoon_count + evening_count

    if total_bmo > 0 or total_amc > 0:
        if total_bmo > total_amc:
            return "BMO"
        elif total_amc > total_bmo:
            return "AMC"
        # If tied, can't determine

    return "unknown"


def date_to_quarter(date_str: str) -> tuple[int, int]:
    """
    Convert a date string to fiscal year and quarter.

    Simple approximation: Uses calendar quarters.
    Q1: Jan-Mar, Q2: Apr-Jun, Q3: Jul-Sep, Q4: Oct-Dec

    For more accurate fiscal year handling, company-specific
    fiscal year calendars would be needed.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        Tuple of (year, quarter)
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        month = dt.month
        year = dt.year

        if month <= 3:
            quarter = 1
        elif month <= 6:
            quarter = 2
        elif month <= 9:
            quarter = 3
        else:
            quarter = 4

        return year, quarter
    except ValueError:
        # Default fallback
        return datetime.now().year, 1
