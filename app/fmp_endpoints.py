"""
FMP (Financial Modeling Prep) Stable API Endpoints Configuration.

All endpoints use the stable base URL: https://financialmodelingprep.com/stable
Generated: 2025-11-16

Usage:
    from app.fmp_endpoints import FMP_BASE_URL, ENDPOINTS
    url = f"{FMP_BASE_URL}/{ENDPOINTS['profile']}"
"""

# Stable API Base URL
FMP_BASE_URL = "https://financialmodelingprep.com/stable"

# All available stable endpoints organized by category
ENDPOINTS = {
    # =========================================================================
    # Company Search
    # =========================================================================
    "search_symbol": "search-symbol",
    "search_name": "search-name",
    "search_cik": "search-cik",
    "search_cusip": "search-cusip",
    "search_isin": "search-isin",
    "company_screener": "company-screener",
    "search_exchange_variants": "search-exchange-variants",

    # =========================================================================
    # Stock Directory
    # =========================================================================
    "stock_list": "stock-list",
    "financial_statement_symbol_list": "financial-statement-symbol-list",
    "cik_list": "cik-list",
    "symbol_change": "symbol-change",
    "etf_list": "etf-list",
    "actively_trading_list": "actively-trading-list",
    "earnings_transcript_list": "earnings-transcript-list",
    "available_exchanges": "available-exchanges",
    "available_sectors": "available-sectors",
    "available_industries": "available-industries",
    "available_countries": "available-countries",

    # =========================================================================
    # Company Information
    # =========================================================================
    "profile": "profile",
    "profile_cik": "profile-cik",
    "company_notes": "company-notes",
    "stock_peers": "stock-peers",
    "delisted_companies": "delisted-companies",
    "employee_count": "employee-count",
    "historical_employee_count": "historical-employee-count",
    "market_capitalization": "market-capitalization",
    "market_capitalization_batch": "market-capitalization-batch",
    "historical_market_capitalization": "historical-market-capitalization",
    "shares_float": "shares-float",
    "shares_float_all": "shares-float-all",
    "mergers_acquisitions_latest": "mergers-acquisitions-latest",
    "mergers_acquisitions_search": "mergers-acquisitions-search",
    "key_executives": "key-executives",
    "governance_executive_compensation": "governance-executive-compensation",
    "executive_compensation_benchmark": "executive-compensation-benchmark",

    # =========================================================================
    # Quotes
    # =========================================================================
    "quote": "quote",
    "quote_short": "quote-short",
    "aftermarket_trade": "aftermarket-trade",
    "aftermarket_quote": "aftermarket-quote",
    "stock_price_change": "stock-price-change",
    "batch_quote": "batch-quote",
    "batch_quote_short": "batch-quote-short",
    "batch_aftermarket_trade": "batch-aftermarket-trade",
    "batch_aftermarket_quote": "batch-aftermarket-quote",
    "batch_exchange_quote": "batch-exchange-quote",
    "batch_mutualfund_quotes": "batch-mutualfund-quotes",
    "batch_etf_quotes": "batch-etf-quotes",
    "batch_commodity_quotes": "batch-commodity-quotes",
    "batch_crypto_quotes": "batch-crypto-quotes",
    "batch_forex_quotes": "batch-forex-quotes",
    "batch_index_quotes": "batch-index-quotes",

    # =========================================================================
    # Financial Statements
    # =========================================================================
    "income_statement": "income-statement",
    "balance_sheet_statement": "balance-sheet-statement",
    "cash_flow_statement": "cash-flow-statement",
    "latest_financial_statements": "latest-financial-statements",
    "income_statement_ttm": "income-statement-ttm",
    "balance_sheet_statement_ttm": "balance-sheet-statement-ttm",
    "cash_flow_statement_ttm": "cash-flow-statement-ttm",
    "key_metrics": "key-metrics",
    "ratios": "ratios",
    "key_metrics_ttm": "key-metrics-ttm",
    "ratios_ttm": "ratios-ttm",
    "financial_scores": "financial-scores",
    "owner_earnings": "owner-earnings",
    "enterprise_values": "enterprise-values",
    "income_statement_growth": "income-statement-growth",
    "balance_sheet_statement_growth": "balance-sheet-statement-growth",
    "cash_flow_statement_growth": "cash-flow-statement-growth",
    "financial_growth": "financial-growth",
    "financial_reports_dates": "financial-reports-dates",
    "financial_reports_json": "financial-reports-json",
    "financial_reports_xlsx": "financial-reports-xlsx",
    "revenue_product_segmentation": "revenue-product-segmentation",
    "revenue_geographic_segmentation": "revenue-geographic-segmentation",
    "income_statement_as_reported": "income-statement-as-reported",
    "balance_sheet_statement_as_reported": "balance-sheet-statement-as-reported",
    "cash_flow_statement_as_reported": "cash-flow-statement-as-reported",
    "financial_statement_full_as_reported": "financial-statement-full-as-reported",

    # =========================================================================
    # Charts / Historical Prices
    # =========================================================================
    "historical_price_eod_light": "historical-price-eod/light",
    "historical_price_eod_full": "historical-price-eod/full",
    "historical_price_eod_non_split_adjusted": "historical-price-eod/non-split-adjusted",
    "historical_price_eod_dividend_adjusted": "historical-price-eod/dividend-adjusted",
    "historical_chart_1min": "historical-chart/1min",
    "historical_chart_5min": "historical-chart/5min",
    "historical_chart_15min": "historical-chart/15min",
    "historical_chart_30min": "historical-chart/30min",
    "historical_chart_1hour": "historical-chart/1hour",
    "historical_chart_4hour": "historical-chart/4hour",

    # =========================================================================
    # Economics
    # =========================================================================
    "treasury_rates": "treasury-rates",
    "economic_indicators": "economic-indicators",
    "economic_calendar": "economic-calendar",
    "market_risk_premium": "market-risk-premium",

    # =========================================================================
    # Earnings, Dividends, Splits
    # =========================================================================
    "dividends": "dividends",
    "dividends_calendar": "dividends-calendar",
    "earnings": "earnings",
    "earnings_calendar": "earnings-calendar",
    "ipos_calendar": "ipos-calendar",
    "ipos_disclosure": "ipos-disclosure",
    "ipos_prospectus": "ipos-prospectus",
    "splits": "splits",
    "splits_calendar": "splits-calendar",

    # =========================================================================
    # Earnings Transcripts
    # =========================================================================
    "earning_call_transcript_latest": "earning-call-transcript-latest",
    "earning_call_transcript": "earning-call-transcript",
    "earning_call_transcript_dates": "earning-call-transcript-dates",

    # =========================================================================
    # News
    # =========================================================================
    "fmp_articles": "fmp-articles",
    "news_general_latest": "news/general-latest",
    "news_press_releases_latest": "news/press-releases-latest",
    "news_stock_latest": "news/stock-latest",
    "news_crypto_latest": "news/crypto-latest",
    "news_forex_latest": "news/forex-latest",
    "news_press_releases": "news/press-releases",
    "news_stock": "news/stock",
    "news_crypto": "news/crypto",
    "news_forex": "news/forex",

    # =========================================================================
    # Form 13F / Institutional Ownership
    # =========================================================================
    "institutional_ownership_latest": "institutional-ownership/latest",
    "institutional_ownership_extract": "institutional-ownership/extract",
    "institutional_ownership_dates": "institutional-ownership/dates",
    "institutional_ownership_holder_analytics": "institutional-ownership/extract-analytics/holder",
    "institutional_ownership_holder_performance": "institutional-ownership/holder-performance-summary",
    "institutional_ownership_holder_industry": "institutional-ownership/holder-industry-breakdown",
    "institutional_ownership_symbol_positions": "institutional-ownership/symbol-positions-summary",
    "institutional_ownership_industry_summary": "institutional-ownership/industry-summary",

    # =========================================================================
    # Analyst
    # =========================================================================
    "analyst_estimates": "analyst-estimates",
    "ratings_snapshot": "ratings-snapshot",
    "ratings_historical": "ratings-historical",
    "price_target_summary": "price-target-summary",
    "price_target_consensus": "price-target-consensus",
    "price_target_news": "price-target-news",
    "price_target_latest_news": "price-target-latest-news",
    "grades": "grades",
    "grades_historical": "grades-historical",
    "grades_consensus": "grades-consensus",
    "grades_news": "grades-news",
    "grades_latest_news": "grades-latest-news",

    # =========================================================================
    # Market Performance
    # =========================================================================
    "sector_performance_snapshot": "sector-performance-snapshot",
    "industry_performance_snapshot": "industry-performance-snapshot",
    "historical_sector_performance": "historical-sector-performance",
    "historical_industry_performance": "historical-industry-performance",
    "sector_pe_snapshot": "sector-pe-snapshot",
    "industry_pe_snapshot": "industry-pe-snapshot",
    "historical_sector_pe": "historical-sector-pe",
    "historical_industry_pe": "historical-industry-pe",
    "biggest_gainers": "biggest-gainers",
    "biggest_losers": "biggest-losers",
    "most_actives": "most-actives",

    # =========================================================================
    # Technical Indicators
    # =========================================================================
    "technical_sma": "technical-indicators/sma",
    "technical_ema": "technical-indicators/ema",
    "technical_wma": "technical-indicators/wma",
    "technical_dema": "technical-indicators/dema",
    "technical_tema": "technical-indicators/tema",
    "technical_rsi": "technical-indicators/rsi",
    "technical_stddev": "technical-indicators/standarddeviation",
    "technical_williams": "technical-indicators/williams",
    "technical_adx": "technical-indicators/adx",

    # =========================================================================
    # ETF and Funds
    # =========================================================================
    "etf_holdings": "etf/holdings",
    "etf_info": "etf/info",
    "etf_country_weightings": "etf/country-weightings",
    "etf_asset_exposure": "etf/asset-exposure",
    "etf_sector_weightings": "etf/sector-weightings",
    "funds_disclosure_holders_latest": "funds/disclosure-holders-latest",
    "funds_disclosure": "funds/disclosure",
    "funds_disclosure_holders_search": "funds/disclosure-holders-search",
    "funds_disclosure_dates": "funds/disclosure-dates",

    # =========================================================================
    # SEC Filings
    # =========================================================================
    "sec_filings_8k": "sec-filings-8k",
    "sec_filings_financials": "sec-filings-financials",
    "sec_filings_search_form_type": "sec-filings-search/form-type",
    "sec_filings_search_symbol": "sec-filings-search/symbol",
    "sec_filings_search_cik": "sec-filings-search/cik",
    "sec_filings_company_search_name": "sec-filings-company-search/name",
    "sec_filings_company_search_symbol": "sec-filings-company-search/symbol",
    "sec_profile": "sec-profile",
    "sic_list": "standard-industrial-classification-list",
    "industry_classification_search": "industry-classification-search",
    "all_industry_classification": "all-industry-classification",

    # =========================================================================
    # Insider Trades
    # =========================================================================
    "insider_trading_latest": "insider-trading/latest",
    "insider_trading_search": "insider-trading/search",
    "insider_trading_reporting_name": "insider-trading/reporting-name",
    "insider_trading_transaction_type": "insider-trading-transaction-type",
    "insider_trading_statistics": "insider-trading/statistics",
    "acquisition_beneficial_ownership": "acquisition-of-beneficial-ownership",

    # =========================================================================
    # Indexes
    # =========================================================================
    "index_list": "index-list",
    "sp500_constituent": "sp500-constituent",
    "nasdaq_constituent": "nasdaq-constituent",
    "dowjones_constituent": "dowjones-constituent",
    "historical_sp500_constituent": "historical-sp500-constituent",
    "historical_nasdaq_constituent": "historical-nasdaq-constituent",
    "historical_dowjones_constituent": "historical-dowjones-constituent",

    # =========================================================================
    # Market Hours
    # =========================================================================
    "exchange_market_hours": "exchange-market-hours",
    "holidays_by_exchange": "holidays-by-exchange",
    "all_exchange_market_hours": "all-exchange-market-hours",

    # =========================================================================
    # Commodities
    # =========================================================================
    "commodities_list": "commodities-list",

    # =========================================================================
    # DCF (Discounted Cash Flow)
    # =========================================================================
    "discounted_cash_flow": "discounted-cash-flow",
    "levered_dcf": "levered-discounted-cash-flow",
    "custom_dcf": "custom-discounted-cash-flow",
    "custom_levered_dcf": "custom-levered-discounted-cash-flow",

    # =========================================================================
    # Forex
    # =========================================================================
    "forex_list": "forex-list",

    # =========================================================================
    # Crypto
    # =========================================================================
    "cryptocurrency_list": "cryptocurrency-list",

    # =========================================================================
    # Congress Disclosures
    # =========================================================================
    "senate_latest": "senate-latest",
    "house_latest": "house-latest",
    "senate_trades": "senate-trades",
    "senate_trades_by_name": "senate-trades-by-name",
    "house_trades": "house-trades",
    "house_trades_by_name": "house-trades-by-name",

    # =========================================================================
    # ESG
    # =========================================================================
    "esg_disclosures": "esg-disclosures",
    "esg_ratings": "esg-ratings",
    "esg_benchmark": "esg-benchmark",

    # =========================================================================
    # COT (Commitment of Traders)
    # =========================================================================
    "cot_report": "commitment-of-traders-report",
    "cot_analysis": "commitment-of-traders-analysis",
    "cot_list": "commitment-of-traders-list",

    # =========================================================================
    # Fundraisers
    # =========================================================================
    "crowdfunding_offerings_latest": "crowdfunding-offerings-latest",
    "crowdfunding_offerings_search": "crowdfunding-offerings-search",
    "crowdfunding_offerings": "crowdfunding-offerings",
    "fundraising_latest": "fundraising-latest",
    "fundraising_search": "fundraising-search",
    "fundraising": "fundraising",

    # =========================================================================
    # Bulk Endpoints
    # =========================================================================
    "profile_bulk": "profile-bulk",
    "rating_bulk": "rating-bulk",
    "dcf_bulk": "dcf-bulk",
    "scores_bulk": "scores-bulk",
    "price_target_summary_bulk": "price-target-summary-bulk",
    "etf_holder_bulk": "etf-holder-bulk",
    "upgrades_downgrades_consensus_bulk": "upgrades-downgrades-consensus-bulk",
    "key_metrics_ttm_bulk": "key-metrics-ttm-bulk",
    "ratios_ttm_bulk": "ratios-ttm-bulk",
    "peers_bulk": "peers-bulk",
    "earnings_surprises_bulk": "earnings-surprises-bulk",
    "income_statement_bulk": "income-statement-bulk",
    "income_statement_growth_bulk": "income-statement-growth-bulk",
    "balance_sheet_statement_bulk": "balance-sheet-statement-bulk",
    "balance_sheet_statement_growth_bulk": "balance-sheet-statement-growth-bulk",
    "cash_flow_statement_bulk": "cash-flow-statement-bulk",
    "cash_flow_statement_growth_bulk": "cash-flow-statement-growth-bulk",
    "eod_bulk": "eod-bulk",
}


def get_url(endpoint_key: str) -> str:
    """
    Get the full URL for an endpoint.

    Args:
        endpoint_key: Key from ENDPOINTS dict (e.g., "earnings", "profile")

    Returns:
        Full URL string

    Raises:
        KeyError: If endpoint_key not found
    """
    if endpoint_key not in ENDPOINTS:
        raise KeyError(f"Unknown endpoint: {endpoint_key}. Available: {list(ENDPOINTS.keys())}")
    return f"{FMP_BASE_URL}/{ENDPOINTS[endpoint_key]}"
