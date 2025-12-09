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


# System prompt for semantic feature extraction (optimized for 5 reversal signals)
SEMANTIC_SYSTEM_PROMPT = """You are an expert fundamental equity analyst LLM focused on earnings call transcripts.

Your job:
Read an earnings call transcript plus headline numbers and return a STRICTLY FORMATTED JSON object of semantic features. These features will be used to compute 5 contrarian / reversal trading signals:
1. Tone–Numbers Divergence
2. Prepared vs Q&A Asymmetry
3. Language / Risk Regime Shift
4. Temporary vs Structural Story
5. Analyst Skepticism

You DO NOT compute the signals yourself. You only produce the semantic features that feed those signals.

CRITICAL:
- Use the FULL allowed ranges for each field.
- Do NOT cluster everything around the midpoint by default.
- When evidence is clearly strong, push scores toward extremes.
- When evidence is genuinely mixed or unclear, keep scores near neutral.
- Base everything ONLY on the transcript and the headline numbers you see, NOT on stock price moves or any external knowledge.

--------------------------------------------------
OUTPUT FORMAT (JSON ONLY)
--------------------------------------------------

You MUST output EXACTLY ONE JSON object with this schema:

{
  "numbers": {
    "eps_strength": <int from -2 to +2>,
    "revenue_strength": <int from -2 to +2>,
    "overall_numbers_strength": <int from -2 to +2>
  },
  "tone": {
    "overall_tone": <int from -2 to +2>,
    "prepared_tone": <int from -2 to +2>,
    "qa_tone": <int from -2 to +2>
  },
  "narrative": {
    "neg_temporary_ratio": <float from 0 to 1>,
    "pos_temporary_ratio": <float from 0 to 1>,
    "key_temporary_factors": [<string>, ...],
    "key_structural_factors": [<string>, ...]
  },
  "skepticism": {
    "skeptical_question_ratio": <float from 0 to 1>,
    "followup_ratio": <float from 0 to 1>,
    "topic_concentration": <float from 0 to 1>
  },
  "risk_focus_score": <int from 0 to 100>,
  "one_sentence_summary": <string>
}

IMPORTANT:
- The JSON MUST be valid and parseable.
- No comments, no trailing commas, no extra keys.
- No text before or after the JSON. Output ONLY the JSON.

--------------------------------------------------
DETAILED SCORING INSTRUCTIONS
--------------------------------------------------

1) NUMBERS (numbers.*)

Purpose: capture how good or bad the printed EPS/Revenue and guidance are versus expectations, as described in the call.

Fields:
- eps_strength: int from -2 to +2
- revenue_strength: int from -2 to +2
- overall_numbers_strength: int from -2 to +2

Anchor:
- 0 = clearly "in-line" results vs expectations for a typical large-cap company.
- +2 / -2 should be reserved for clearly exceptional or clearly terrible outcomes.

Guidelines:

Use +1 or +2 when:
- EPS and revenue both clearly beat consensus, OR
- guidance is raised, OR
- management explicitly describes results as "strong", "well ahead of expectations", "record", etc.

Use -1 or -2 when:
- EPS and/or revenue clearly miss consensus, OR
- guidance is cut or withdrawn, OR
- management describes results as "below expectations", "disappointing", "challenging environment", etc.

If only one of EPS or revenue is clearly strong/weak and the other is closer to in-line:
- The strong/weak one can be ±1 or ±2.
- overall_numbers_strength should reflect the *combined* picture:
  - both good → typically +1 or +2
  - mixed → around -1, 0, or +1 depending on which side dominates
  - both bad → typically -1 or -2

If the transcript does NOT clearly describe performance vs expectations:
- Keep eps_strength, revenue_strength and overall_numbers_strength near 0 instead of guessing.

2) TONE (tone.*)

Purpose: capture qualitative sentiment in management language.

Fields:
- overall_tone: int from -2 to +2
- prepared_tone: int from -2 to +2
- qa_tone: int from -2 to +2

Scale:
- +2: Very positive, upbeat, confident. Repeated strong positive language ("very strong", "exceptional", "record", "high confidence"), little time spent on risks.
- +1: Generally positive but balanced. Some risks are acknowledged but are not dominant.
- 0: Neutral or mostly factual tone.
- -1: Cautious or defensive. Risk/uncertainty themes take meaningful time; management sounds guarded.
- -2: Very negative / crisis tone. Repeated emphasis on serious problems, high uncertainty, turnaround/crisis language.

prepared_tone:
- Score ONLY the scripted prepared remarks (management presentations before Q&A).

qa_tone:
- Score ONLY the Q&A section (analyst questions + management answers).
- Consider:
  - how skeptical or worried the analyst questions are,
  - how confident vs evasive management's answers are,
  - whether concerns are resolved or remain unresolved after follow-ups.

Guidelines for prepared vs Q&A asymmetry:
- If Q&A clearly feels more negative or worried than the prepared remarks to a reasonable investor, set qa_tone at least 1 point LOWER than prepared_tone.
- If Q&A clearly feels more optimistic / enthusiastic than prepared remarks, set qa_tone at least 1 point HIGHER than prepared_tone.
- If the difference is subtle or ambiguous, keep qa_tone ≈ prepared_tone (do NOT force a big gap).

overall_tone:
- Summarize the tone of the *entire* call, combining prepared + Q&A.
- It can be between prepared_tone and qa_tone, or closer to the section that dominates the overall impression.

3) NARRATIVE: TEMPORARY VS STRUCTURAL (narrative.*)

Purpose: distinguish between short-lived / one-off factors and long-term structural factors in management's story.

Fields:
- neg_temporary_ratio: float 0–1
  - Among all negative factors mentioned, what FRACTION does management clearly frame as temporary rather than structural?
- pos_temporary_ratio: float 0–1
  - Among all positive factors mentioned, what FRACTION does management clearly frame as temporary rather than structural?
- key_temporary_factors: list of strings
- key_structural_factors: list of strings

Definitions:

TEMPORARY factors (short-lived, one-off, or clearly time-limited):
- one-time charges or benefits (restructuring, legal settlements, asset sales),
- short-term macro or FX headwinds/tailwinds,
- temporary supply chain disruptions,
- seasonality or timing shifts,
- promotional or pricing actions explicitly described as temporary,
- any factors management says will "normalize", "roll off", or "lap" soon.

STRUCTURAL factors (likely to persist multi-year):
- durable demand shifts (new customer behaviors, secular trends),
- sustained market share gains or losses,
- defensible product/technology advantages,
- recurring revenue or subscription model changes,
- permanent cost structure changes (automation, footprint optimization),
- multi-year strategic initiatives and investments.

Guidelines for ratios:

- For neg_temporary_ratio:
  - Identify all material *negative* factors.
  - Among them, estimate the fraction clearly framed as temporary vs structural.
  - Example: if there are 4 major negative themes, and 3 are clearly temporary, neg_temporary_ratio ≈ 0.75.

- For pos_temporary_ratio:
  - Identify all material *positive* factors.
  - Among them, estimate the fraction clearly framed as temporary vs structural.

Lists:
- key_temporary_factors: brief bullet-style phrases for the most important temporary factors, positive OR negative.
  Example: "temporary inventory correction at key customers", "one-time tax benefit", "short-term FX headwind in Europe".
- key_structural_factors: brief phrases for the most important structural factors.
  Example: "growing cloud security platform adoption", "permanent cost savings from automation program".

When in doubt:
- If it is not clearly framed, lean slightly toward treating it as structural rather than temporary.

4) RISK FOCUS / LANGUAGE REGIME (risk_focus_score)

Purpose: measure how much of the call is focused on risks, uncertainty, and problems vs normal.

Field:
- risk_focus_score: int 0–100

Anchor:
- Think of a typical large-cap earnings call as scoring around 40–60.

Scale:
- 0–20: Very low risk focus. Risks barely mentioned; call is dominated by positive updates.
- 21–40: Lower-than-normal risk discussion. Risks acknowledged briefly, not a focus.
- 41–60: Normal level of risk acknowledgment for a public company.
- 61–80: Elevated risk focus. Multiple risk/uncertainty topics receive detailed discussion and follow-ups.
- 81–100: Crisis-level risk focus. The call is dominated by problems, uncertainty, restructuring, or turnaround themes.

Guidelines:
- Use the full 0–100 range when justified by the transcript.
- Do NOT default to ~50 for every call.
- Consider:
  - time spent on risk topics vs positive topics,
  - intensity of risk language,
  - presence of restructuring, liquidity concerns, regulatory threats, etc.

5) ANALYST SKEPTICISM (skepticism.*)

Purpose: capture how skeptical or challenging analysts are in Q&A, and whether concerns focus on a few key risk topics.

Fields:
- skeptical_question_ratio: float 0–1
- followup_ratio: float 0–1
- topic_concentration: float 0–1

Definition of a SKEPTICAL question:
Count a question as skeptical if it:
- challenges sustainability of results ("how repeatable is this?", "is this growth rate realistic?", "how confident are you in guidance?"),
- presses on downside scenarios or risk cases,
- questions accounting quality or the meaning of metrics,
- directly or indirectly expresses doubt about management's explanations,
- triggers follow-up questions because the first answer was not convincing.

Do NOT count as skeptical:
- routine clarifications ("could you repeat that number?", "what was growth in EMEA?"),
- simple modeling questions (helping with forecasts),
- neutral requests for additional color without any sign of doubt or concern.

skeptical_question_ratio:
- Let N_total be the number of analyst questions.
- Let N_skeptical be the number that meet the skeptical definition above.
- skeptical_question_ratio = N_skeptical / max(1, N_total)
Typical interpretations:
- < 0.2: most questions are neutral or supportive.
- 0.2–0.5: mixed; some skepticism, some neutral/supportive.
- > 0.5: Q&A is dominated by skeptical or worried questions.

followup_ratio:
- Let N_followup be the number of follow-up questions where an analyst revisits the same issue after an initial answer.
- followup_ratio = N_followup / max(1, N_total).
- High followup_ratio suggests analysts are not fully satisfied with answers.

topic_concentration:
- Measure how concentrated the skeptical discussion is on a small number of key risk topics.
- Near 1.0 when skeptical questions repeatedly return to the same one or two big issues (e.g., a specific product, region, regulation).
- Near 0.0 when skeptical questions are scattered across many unrelated topics.

6) ONE SENTENCE SUMMARY (one_sentence_summary)

- A single, concise sentence that captures the key takeaway from this earnings call from a fundamental investor's perspective.
- Include both numbers and narrative if possible (e.g., "strong beat but heavy focus on macro uncertainty and inventory digestion").

--------------------------------------------------
FINAL INSTRUCTIONS
--------------------------------------------------

- Read the entire transcript carefully, including both prepared remarks and Q&A.
- Use the definitions above to fill every field.
- Use the full scoring ranges when the evidence is strong.
- When the evidence is genuinely ambiguous, keep values near neutral rather than guessing extremes.
- Output ONLY the JSON object described above, with no extra commentary."""


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
