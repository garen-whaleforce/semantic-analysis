"""
FastAPI Application Entry Point.

Provides endpoints for:
- GET /: Main web interface
- GET /api/health: Health check
- GET /api/analyze: Run semantic earnings analysis for a ticker
"""

import logging
from pathlib import Path

from fastapi import FastAPI, Query, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.models import TickerAnalysisResult
from app.earnings_logic import analyze_ticker as run_analysis


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Semantic Earnings Reversal Framework",
    description="Backtest semantic reversal signals on US stock earnings",
    version="1.0.0"
)

# Setup paths
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Mount static files and templates
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.get("/")
async def index(request: Request):
    """
    Render the main web interface.
    """
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
async def health_check():
    """
    Health check endpoint for deployment monitoring.
    """
    settings = get_settings()
    missing = settings.validate()

    if missing:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "message": f"Missing configuration: {', '.join(missing)}"
            }
        )

    return {"status": "healthy"}


@app.get("/api/analyze")
async def analyze_ticker_endpoint(
    ticker: str = Query(..., min_length=1, max_length=10, description="Stock ticker symbol"),
    max_events: int = Query(default=8, ge=1, le=20, description="Maximum events to analyze")
) -> TickerAnalysisResult:
    """
    Run semantic earnings reversal analysis for a single ticker.

    Process:
    1. Fetch historical earnings data from FMP
    2. Fetch historical price data from FMP
    3. For each earnings event:
       - Fetch transcript
       - Extract semantic features via Azure OpenAI
       - Calculate day 0 return
       - Calculate 5 reversal signals
       - Calculate forward returns (T+5, T+10, T+30, T+60)
    4. Compute aggregate hit rates

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL")
        max_events: Maximum number of events to analyze (default: 8)

    Returns:
        TickerAnalysisResult with all events and summary statistics
    """
    # Validate configuration
    settings = get_settings()
    if not settings.is_valid():
        raise HTTPException(
            status_code=500,
            detail={
                "error": "configuration_error",
                "message": f"Server configuration incomplete. Missing: {settings.validate()}"
            }
        )

    # Normalize ticker
    ticker = ticker.upper().strip()

    # Validate ticker format (basic check)
    if not ticker.isalpha() and not ticker.replace(".", "").isalpha():
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_ticker",
                "message": f"Invalid ticker format: {ticker}"
            }
        )

    try:
        # Run the analysis using the centralized function
        result = await run_analysis(symbol=ticker, max_events=max_events)
        return result

    except ValueError as e:
        # Business logic errors (no data found, etc.)
        logger.warning(f"Analysis failed for {ticker}: {e}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "analysis_failed",
                "message": str(e)
            }
        )
    except Exception as e:
        # Unexpected errors
        logger.exception(f"Unexpected error analyzing {ticker}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"Analysis failed: {str(e)}"
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
