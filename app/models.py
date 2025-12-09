"""
Pydantic models for the Semantic Earnings Analysis application.

Defines data structures for:
- FMP API responses (EarningsRaw, PriceBar)
- Azure OpenAI semantic features extraction
- Signal calculations and forward returns
- API response schemas
"""

from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


# =============================================================================
# FMP API Response Models
# =============================================================================

class EarningsRaw(BaseModel):
    """
    Raw earnings data from FMP stable/earnings endpoint.
    Uses FMP field names: epsActual, epsEstimated, revenueActual, revenueEstimated
    """
    date: str  # YYYY-MM-DD format
    symbol: str
    eps: Optional[float] = Field(default=None, alias="epsActual")
    eps_estimated: Optional[float] = Field(default=None, alias="epsEstimated")
    revenue: Optional[float] = Field(default=None, alias="revenueActual")
    revenue_estimated: Optional[float] = Field(default=None, alias="revenueEstimated")

    class Config:
        populate_by_name = True


class PriceBar(BaseModel):
    """
    Single day price bar from FMP historical-price-full endpoint.
    """
    date: str  # YYYY-MM-DD format
    open: float
    high: float
    low: float
    close: float
    volume: Optional[int] = None

    class Config:
        populate_by_name = True


# =============================================================================
# Azure OpenAI Semantic Features Models
# =============================================================================

class NumbersView(BaseModel):
    """
    Assessment of EPS/Revenue performance vs expectations.
    Scale: -2 (very bad) to +2 (very good)
    """
    eps_strength: int = Field(ge=-2, le=2, description="EPS vs expectation: -2 to +2")
    revenue_strength: int = Field(ge=-2, le=2, description="Revenue vs expectation: -2 to +2")
    overall_numbers_strength: int = Field(ge=-2, le=2, description="Overall numerical performance: -2 to +2")


class ToneView(BaseModel):
    """
    Sentiment analysis of transcript sections.
    Scale: -2 (very negative) to +2 (very positive)
    """
    overall_tone: int = Field(ge=-2, le=2, description="Overall transcript tone: -2 to +2")
    prepared_tone: int = Field(ge=-2, le=2, description="Prepared remarks tone: -2 to +2")
    qa_tone: int = Field(ge=-2, le=2, description="Q&A session tone: -2 to +2")


class NarrativeView(BaseModel):
    """
    Analysis of temporary vs structural factors in management narrative.
    """
    neg_temporary_ratio: float = Field(ge=0, le=1, description="Ratio of negative factors that are temporary")
    pos_temporary_ratio: float = Field(ge=0, le=1, description="Ratio of positive factors that are temporary")
    key_temporary_factors: list[str] = Field(default_factory=list, description="Key temporary factors mentioned")
    key_structural_factors: list[str] = Field(default_factory=list, description="Key structural factors mentioned")


class SkepticismView(BaseModel):
    """
    Analysis of analyst questioning behavior during Q&A.
    """
    skeptical_question_ratio: float = Field(ge=0, le=1, description="Ratio of skeptical/challenging questions")
    followup_ratio: float = Field(ge=0, le=1, description="Ratio of follow-up questions (indicating dissatisfaction)")
    topic_concentration: float = Field(ge=0, le=1, description="Degree to which questions concentrate on single risk topic")


class SemanticFeatures(BaseModel):
    """
    Complete semantic features extracted from earnings transcript by Azure OpenAI.
    """
    numbers: NumbersView
    tone: ToneView
    narrative: NarrativeView
    skepticism: SkepticismView
    risk_focus_score: int = Field(ge=0, le=100, description="Overall risk/uncertainty focus intensity (0-100)")
    one_sentence_summary: str = Field(description="One sentence summary of the earnings call")


# =============================================================================
# Signal Calculation Models
# =============================================================================

class SingleSignal(BaseModel):
    """
    Individual signal output with score and explanation.
    """
    name: str
    score: float = Field(ge=0, le=10, description="Signal score: 0 (strong bearish) to 10 (strong bullish), 5 = neutral")
    explanation: str


class AllSignals(BaseModel):
    """
    Complete set of five signals plus the aggregated final signal.
    """
    tone_numbers: SingleSignal
    prepared_vs_qa: SingleSignal
    regime_shift: SingleSignal
    temp_vs_struct: SingleSignal
    analyst_skepticism: SingleSignal
    final_signal: SingleSignal


# =============================================================================
# Forward Returns Models
# =============================================================================

class ForwardReturn(BaseModel):
    """
    Forward return calculation for a specific horizon.
    """
    horizon: int  # 5, 10, 30, or 60 trading days
    start_date: str  # T0 date (first trading day after earnings)
    end_date: str  # T+horizon date
    return_pct: float  # (P_end - P_start) / P_start
    hit: Optional[bool] = None  # True if signal direction matches return direction; None if signal=0


# =============================================================================
# Event and API Response Models
# =============================================================================

class EarningsEventWithTranscript(BaseModel):
    """
    Enriched earnings event with transcript for LLM analysis.
    """
    symbol: str
    earning_date: str
    eps: Optional[float] = None
    eps_estimated: Optional[float] = None
    revenue: Optional[float] = None
    revenue_estimated: Optional[float] = None
    day0_return: float
    transcript: str
    year: int
    quarter: int


class EventAnalysisStatus(BaseModel):
    """
    Status information for event analysis.
    """
    success: bool = True
    transcript_available: bool = True
    llm_success: bool = True
    error_message: Optional[str] = None


class EarningsEventResult(BaseModel):
    """
    Complete analysis result for a single earnings event.
    """
    earning_date: str
    year: int
    quarter: int
    eps: Optional[float] = None
    eps_estimate: Optional[float] = None
    revenue: Optional[float] = None
    revenue_estimate: Optional[float] = None
    day0_return: Optional[float] = None
    call_time: str = Field(default="unknown", description="BMO (before market open), AMC (after market close), or unknown")
    signals: Optional[AllSignals] = None
    semantic_features: Optional[SemanticFeatures] = None
    forward_returns: list[ForwardReturn] = Field(default_factory=list)
    status: EventAnalysisStatus = Field(default_factory=EventAnalysisStatus)


class HitRateStat(BaseModel):
    """
    Hit rate statistics for a single horizon.
    """
    num_trades: int
    num_hits: int
    hit_rate: Optional[float] = None  # None if num_trades == 0


class SummaryStats(BaseModel):
    """
    Summary statistics across all horizons.
    """
    hit_rates: dict[str, HitRateStat]  # key: "5", "10", "30", "60"


class TickerAnalysisResult(BaseModel):
    """
    Complete analysis result for a single ticker.
    Used by analyze_ticker() function and API response.
    """
    ticker: str
    events: list[EarningsEventResult]
    summary: SummaryStats
    total_events_found: int = 0
    events_analyzed: int = 0
    events_with_signals: int = 0


# Alias for backward compatibility
AnalysisResponse = TickerAnalysisResult
