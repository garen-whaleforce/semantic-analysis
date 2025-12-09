# Semantic Earnings Reversal Framework

A web application for backtesting semantic reversal signals on US stock earnings calls. This tool analyzes historical earnings transcripts using AI to extract semantic features, then calculates five specialized trading signals designed to identify potential price reversals.

## Quick Start

### 1. Setup Environment

```bash
# Clone and enter project
cd semantic-analysis

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .\.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure `.env`

Create a `.env` file in the project root:

```bash
# FMP Premium API (required for transcripts)
FMP_API_KEY=your_fmp_api_key

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_azure_openai_key
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_DEPLOYMENT=gpt-4o  # or your deployment name
```

### 3. Run the Application

```bash
# Start the web server
uvicorn app.main:app --reload

# Open http://localhost:8000 in your browser
```

### 4. CLI Testing (Optional)

Test a ticker from the command line:

```bash
python scripts/quick_test.py AAPL
python scripts/quick_test.py MSFT
python scripts/quick_test.py NVDA
```

## Features

- **FMP Integration**: Fetches historical earnings data, stock prices, and earnings call transcripts
- **AI-Powered Analysis**: Uses Azure OpenAI to extract semantic features from transcripts
- **Five Reversal Signals**:
  1. **Tone-Numbers Divergence**: Detects when management tone contradicts headline numbers
  2. **Prepared vs Q&A Asymmetry**: Identifies gaps between scripted remarks and Q&A responses
  3. **Language Regime Shift**: Spots sudden changes in risk language intensity
  4. **Temporary vs Structural**: Analyzes whether factors are one-time or ongoing
  5. **Analyst Skepticism**: Measures professional doubt during Q&A
- **Forward Return Analysis**: Calculates T+5, T+10, T+30, T+60 returns and hit rates
- **Interactive Web UI**: Clean interface for analyzing any US stock ticker

## Project Structure

```
semantic-analysis/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application entry point
│   ├── config.py         # Environment variable configuration
│   ├── models.py         # Pydantic data models
│   ├── fmp_client.py     # FMP API client
│   ├── fmp_endpoints.py  # FMP stable API endpoints
│   ├── llm_client.py     # Azure OpenAI client
│   └── earnings_logic.py # Signal calculation + analyze_ticker()
├── scripts/
│   └── quick_test.py     # CLI testing tool
├── templates/
│   └── index.html        # Main web interface
├── static/
│   └── app.js            # Frontend JavaScript
├── requirements.txt
├── .env.example
└── README.md
```

## Prerequisites

- Python 3.11+
- FMP Premium API key (for earnings transcripts)
- Azure OpenAI deployment (GPT-4 or higher recommended)

## Zeabur Deployment

### Required Environment Variables

Set these in Zeabur console → Variables:

| Variable | Description |
|----------|-------------|
| `FMP_API_KEY` | FMP Premium API key |
| `AZURE_OPENAI_ENDPOINT` | e.g., `https://your-resource.openai.azure.com/` |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_API_VERSION` | e.g., `2024-12-01-preview` |
| `AZURE_OPENAI_DEPLOYMENT` | Your deployment name (e.g., `gpt-4o`) |

### Deploy Steps

1. Push code to GitHub
2. Connect repository to Zeabur
3. Zeabur auto-detects Python and uses `requirements.txt`
4. Add all environment variables above
5. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Optional: Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## API Endpoints

### GET /
Main web interface for entering ticker and viewing results.

### GET /api/health
Health check endpoint. Returns configuration status.

### GET /api/analyze?ticker=AAPL
Run semantic analysis for a ticker. Returns JSON with:
- All earnings events with signals and forward returns
- Summary hit rates for each horizon

## Signal Calculation Rules

### 1. Tone-Numbers Divergence
- Good numbers + Bad tone → Bearish (-1)
- Bad numbers + Good tone → Bullish (+1)

### 2. Prepared vs Q&A Asymmetry
- Q&A worse than prepared + Price up >5% → Bearish (-1)
- Q&A better than prepared + Price down <-5% → Bullish (+1)

### 3. Language Regime Shift
- Risk language spike (z ≥ 1.5) + Price not down → Bearish (-1)
- Risk language drop (z ≤ -1.5) + Price not up → Bullish (+1)

### 4. Temporary vs Structural
- EPS miss + High neg_temporary_ratio (≥70%) → Bullish (+1)
- EPS beat + High pos_temporary_ratio (≥70%) → Bearish (-1)

### 5. Analyst Skepticism
- Price up >5% + High skepticism (≥40%) → Bearish (-1)
- Price down <-5% + Low skepticism (≤20%) → Bullish (+1)

### Final Signal
- Sum of all 5 signals ≥ 2 → Bullish (+1)
- Sum of all 5 signals ≤ -2 → Bearish (-1)
- Otherwise → Neutral (0)

## Assumptions and Limitations

1. **Fiscal Calendar**: Uses calendar quarters (Q1=Jan-Mar, etc.) for transcript lookup. Companies with non-standard fiscal years may have mismatched transcripts.

2. **Transcript Availability**: FMP Premium required for transcripts. Analysis falls back to default features if transcript unavailable.

3. **Trading Days**: Forward returns count actual trading days from price data, not calendar days.

4. **Sample Size**: Regime Shift signal requires 4+ prior quarters for z-score calculation.

5. **Token Limits**: Very long transcripts are truncated to fit Azure OpenAI context limits.

## License

MIT
