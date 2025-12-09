"""
PostgreSQL Database Client for accessing AWS RDS data.

Provides functions to fetch:
- Earnings transcripts from transcript_content table
- Historical prices from historical_prices table
- Earnings events from earnings_transcripts table

Primary data source; falls back to FMP API if DB unavailable.
"""

import logging
from typing import Optional
from datetime import date

import psycopg2
from psycopg2.extras import RealDictCursor

from app.config import get_settings
from app.models import PriceBar

logger = logging.getLogger(__name__)


def get_db_connection():
    """Create and return a database connection."""
    settings = get_settings()

    if not settings.database_host:
        return None

    try:
        conn = psycopg2.connect(
            host=settings.database_host,
            port=settings.database_port,
            user=settings.database_user,
            password=settings.database_password,
            database=settings.database_name,
            connect_timeout=10
        )
        return conn
    except Exception as e:
        logger.warning(f"Failed to connect to database: {e}")
        return None


def get_transcript_from_db(symbol: str, year: int, quarter: int) -> Optional[str]:
    """
    Fetch earnings transcript from database.

    Args:
        symbol: Stock ticker symbol
        year: Fiscal year
        quarter: Fiscal quarter (1-4)

    Returns:
        Transcript content if found, None otherwise
    """
    conn = get_db_connection()
    if not conn:
        return None

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT content
                FROM transcript_content
                WHERE symbol = %s AND year = %s AND quarter = %s
                LIMIT 1
            """, (symbol.upper(), year, quarter))

            row = cur.fetchone()
            if row and row[0]:
                logger.info(f"Found transcript in DB for {symbol} Q{quarter} {year}")
                return row[0]
            return None
    except Exception as e:
        logger.warning(f"DB query failed for transcript {symbol} Q{quarter} {year}: {e}")
        return None
    finally:
        conn.close()


def get_earnings_events_from_db(symbol: str, limit: int = 20) -> list[dict]:
    """
    Fetch earnings events from database.

    Args:
        symbol: Stock ticker symbol
        limit: Maximum number of events to retrieve

    Returns:
        List of earnings event dicts with date, year, quarter info
    """
    conn = get_db_connection()
    if not conn:
        return []

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    symbol,
                    year,
                    quarter,
                    t_day as earning_date,
                    transcript_date,
                    market_timing
                FROM earnings_transcripts
                WHERE symbol = %s
                ORDER BY year DESC, quarter DESC
                LIMIT %s
            """, (symbol.upper(), limit))

            rows = cur.fetchall()
            logger.info(f"Found {len(rows)} earnings events in DB for {symbol}")
            return [dict(row) for row in rows]
    except Exception as e:
        logger.warning(f"DB query failed for earnings events {symbol}: {e}")
        return []
    finally:
        conn.close()


def get_price_history_from_db(symbol: str) -> list[PriceBar]:
    """
    Fetch historical price data from database.

    Args:
        symbol: Stock ticker symbol

    Returns:
        List of PriceBar objects sorted by date (oldest first)
    """
    conn = get_db_connection()
    if not conn:
        return []

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    date,
                    open,
                    high,
                    low,
                    close,
                    adj_close,
                    volume
                FROM historical_prices
                WHERE symbol = %s
                ORDER BY date ASC
            """, (symbol.upper(),))

            rows = cur.fetchall()

            price_bars = []
            for row in rows:
                try:
                    bar = PriceBar(
                        date=str(row['date']),
                        open=float(row['open']) if row['open'] else 0,
                        high=float(row['high']) if row['high'] else 0,
                        low=float(row['low']) if row['low'] else 0,
                        close=float(row['close']) if row['close'] else 0,
                        volume=int(row['volume']) if row['volume'] else None
                    )
                    if bar.close > 0:
                        price_bars.append(bar)
                except (ValueError, TypeError):
                    continue

            logger.info(f"Found {len(price_bars)} price bars in DB for {symbol}")
            return price_bars
    except Exception as e:
        logger.warning(f"DB query failed for price history {symbol}: {e}")
        return []
    finally:
        conn.close()


def check_db_available() -> bool:
    """Check if database connection is available."""
    conn = get_db_connection()
    if conn:
        conn.close()
        return True
    return False


def get_available_symbols() -> list[str]:
    """Get list of all symbols available in the database."""
    conn = get_db_connection()
    if not conn:
        return []

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT symbol FROM companies ORDER BY symbol")
            return [row[0] for row in cur.fetchall()]
    except Exception as e:
        logger.warning(f"Failed to get available symbols: {e}")
        return []
    finally:
        conn.close()
