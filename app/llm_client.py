"""
Azure OpenAI LLM Client for semantic feature extraction.

Uses Azure OpenAI to analyze earnings call transcripts and extract
structured semantic features for signal calculation.
"""

import asyncio
import json
from typing import Optional

from openai import AzureOpenAI

# 並發控制：限制同時最多 10 個 LLM 請求 (Azure RPM = 850)
LLM_SEMAPHORE = asyncio.Semaphore(10)

from app.config import get_settings
from app.models import (
    EarningsEventWithTranscript,
    SemanticFeatures,
    NumbersView,
    ToneView,
    NarrativeView,
    SkepticismView,
)


# System prompt for semantic feature extraction
SEMANTIC_SYSTEM_PROMPT = """You are an expert financial analyst specializing in earnings call transcript analysis. Your task is to analyze a company's earnings call transcript and extract structured semantic features.

You will receive:
1. Company symbol and earnings date
2. Actual and estimated EPS/Revenue figures
3. Day 0 stock price return (percentage)
4. The full earnings call transcript (including prepared remarks and Q&A)

You must output a JSON object with the following structure:

{
  "numbers": {
    "eps_strength": <int -2 to +2>,
    "revenue_strength": <int -2 to +2>,
    "overall_numbers_strength": <int -2 to +2>
  },
  "tone": {
    "overall_tone": <int -2 to +2>,
    "prepared_tone": <int -2 to +2>,
    "qa_tone": <int -2 to +2>
  },
  "narrative": {
    "neg_temporary_ratio": <float 0-1>,
    "pos_temporary_ratio": <float 0-1>,
    "key_temporary_factors": [<list of strings>],
    "key_structural_factors": [<list of strings>]
  },
  "skepticism": {
    "skeptical_question_ratio": <float 0-1>,
    "followup_ratio": <float 0-1>,
    "topic_concentration": <float 0-1>
  },
  "risk_focus_score": <int 0-100>,
  "one_sentence_summary": "<string>"
}

Field definitions:

NUMBERS (based on EPS/Revenue vs estimates):
- eps_strength: -2 (significant miss), -1 (slight miss), 0 (in-line), +1 (slight beat), +2 (significant beat)
- revenue_strength: Same scale as eps_strength
- overall_numbers_strength: Holistic assessment combining EPS, revenue, and guidance

TONE (based on language sentiment):
- overall_tone: -2 (very negative/defensive), -1 (cautious), 0 (neutral), +1 (confident), +2 (very optimistic)
- prepared_tone: Tone in the prepared remarks/presentation section only
- qa_tone: Tone during analyst Q&A, considering management responses

NARRATIVE:
- neg_temporary_ratio: Of all negative factors mentioned, what fraction are positioned as temporary/one-time (0-1)
- pos_temporary_ratio: Of all positive factors mentioned, what fraction are positioned as temporary/one-time (0-1)
- key_temporary_factors: List 2-4 main temporary factors mentioned (headwinds or tailwinds)
- key_structural_factors: List 2-4 main structural/ongoing factors mentioned

SKEPTICISM (analyst behavior in Q&A):
- skeptical_question_ratio: Fraction of analyst questions that challenge, probe, or express doubt (0-1)
- followup_ratio: Fraction of analysts who asked follow-up questions indicating unsatisfactory first answers (0-1)
- topic_concentration: How concentrated questions are on a single risk topic (0=diverse, 1=single topic dominates)

RISK_FOCUS_SCORE (0-100):
- Overall intensity of risk/uncertainty discussion relative to typical earnings calls
- 0-20: Very low risk focus, mostly positive
- 21-40: Normal level of risk acknowledgment
- 41-60: Elevated risk discussion
- 61-80: High risk focus, multiple concerns raised
- 81-100: Extremely high uncertainty, crisis-level concerns

ONE_SENTENCE_SUMMARY:
- A single sentence capturing the key takeaway from this earnings call

Important guidelines:
1. Be objective and base assessments on actual content, not stock price reaction
2. For tone analysis, focus on word choice, hedging language, and certainty of statements
3. Distinguish between management's spin and substantive information
4. Consider both what is said and what is notably absent/avoided
5. Output ONLY valid JSON, no additional text or explanation"""


def get_llm_client() -> AzureOpenAI:
    """Create and return an Azure OpenAI client instance."""
    settings = get_settings()
    return AzureOpenAI(
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        azure_endpoint=settings.azure_openai_endpoint,
    )


def build_user_message(event: EarningsEventWithTranscript) -> str:
    """
    Build the user message containing earnings data and transcript.

    Args:
        event: Earnings event with transcript data

    Returns:
        Formatted user message string
    """
    eps_str = f"{event.eps:.4f}" if event.eps is not None else "N/A"
    eps_est_str = f"{event.eps_estimated:.4f}" if event.eps_estimated is not None else "N/A"
    rev_str = f"${event.revenue:,.0f}" if event.revenue is not None else "N/A"
    rev_est_str = f"${event.revenue_estimated:,.0f}" if event.revenue_estimated is not None else "N/A"

    message = f"""EARNINGS CALL ANALYSIS REQUEST

Symbol: {event.symbol}
Earnings Date: {event.earning_date}
Quarter: Q{event.quarter} {event.year}

HEADLINE NUMBERS:
- EPS Actual: {eps_str}
- EPS Estimated: {eps_est_str}
- Revenue Actual: {rev_str}
- Revenue Estimated: {rev_est_str}

DAY 0 STOCK PRICE REACTION: {event.day0_return:+.2%}

--- FULL TRANSCRIPT ---

{event.transcript}

--- END TRANSCRIPT ---

Please analyze this transcript and provide the semantic features JSON."""

    return message


async def extract_semantic_features(event: EarningsEventWithTranscript) -> SemanticFeatures:
    """
    Extract semantic features from an earnings event using Azure OpenAI.

    Args:
        event: Earnings event with transcript

    Returns:
        SemanticFeatures object with extracted features

    Raises:
        ValueError: If LLM response cannot be parsed
        Exception: If API call fails
    """
    async with LLM_SEMAPHORE:
        settings = get_settings()
        client = get_llm_client()

        user_message = build_user_message(event)

        # Truncate transcript if too long (Azure OpenAI has token limits)
        # GPT-4/5 can handle ~128k tokens, but we'll be conservative
        max_chars = 100000
        if len(user_message) > max_chars:
            # Keep first 80% and last 10% of transcript to preserve Q&A
            transcript = event.transcript
            keep_start = int(len(transcript) * 0.75)
            keep_end = int(len(transcript) * 0.15)
            truncated_transcript = (
                transcript[:keep_start] +
                "\n\n[... TRANSCRIPT TRUNCATED FOR LENGTH ...]\n\n" +
                transcript[-keep_end:]
            )
            event_copy = event.model_copy()
            event_copy.transcript = truncated_transcript
            user_message = build_user_message(event_copy)

        response = client.chat.completions.create(
            model=settings.azure_openai_deployment,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SEMANTIC_SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,  # Lower temperature for more consistent analysis
            max_completion_tokens=2000,  # GPT-5.1 uses max_completion_tokens instead of max_tokens
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from Azure OpenAI")

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")

        # Parse into Pydantic models with validation
        try:
            features = SemanticFeatures(
                numbers=NumbersView(**data.get("numbers", {})),
                tone=ToneView(**data.get("tone", {})),
                narrative=NarrativeView(**data.get("narrative", {})),
                skepticism=SkepticismView(**data.get("skepticism", {})),
                risk_focus_score=data.get("risk_focus_score", 50),
                one_sentence_summary=data.get("one_sentence_summary", "No summary available.")
            )
        except Exception as e:
            raise ValueError(f"Failed to validate LLM response structure: {e}")

        return features


def create_default_features() -> SemanticFeatures:
    """
    Create default semantic features when transcript is unavailable.

    Returns neutral/middle values for all features.
    """
    return SemanticFeatures(
        numbers=NumbersView(
            eps_strength=0,
            revenue_strength=0,
            overall_numbers_strength=0
        ),
        tone=ToneView(
            overall_tone=0,
            prepared_tone=0,
            qa_tone=0
        ),
        narrative=NarrativeView(
            neg_temporary_ratio=0.5,
            pos_temporary_ratio=0.5,
            key_temporary_factors=[],
            key_structural_factors=[]
        ),
        skepticism=SkepticismView(
            skeptical_question_ratio=0.3,
            followup_ratio=0.2,
            topic_concentration=0.3
        ),
        risk_focus_score=40,
        one_sentence_summary="Transcript not available for analysis."
    )
