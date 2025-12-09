"""
Configuration module for environment variables.

Reads API keys and settings from environment variables.
Use .env file for local development (loaded by python-dotenv).
"""

import os
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv

# Load .env file if present
load_dotenv()


class Settings:
    """
    Application settings loaded from environment variables.
    """

    def __init__(self) -> None:
        # FMP API Configuration
        self.fmp_api_key: str = os.getenv("FMP_API_KEY", "")

        # Azure OpenAI Configuration
        self.azure_openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        self.azure_openai_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
        self.azure_openai_api_version: str = os.getenv(
            "AZURE_OPENAI_API_VERSION",
            "2024-10-01-preview"
        )
        self.azure_openai_deployment: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

        # PostgreSQL Database Configuration (optional - falls back to FMP if not set)
        self.database_host: str = os.getenv("DATABASE_HOST", "")
        self.database_port: str = os.getenv("DATABASE_PORT", "5432")
        self.database_user: str = os.getenv("DATABASE_USER", "")
        self.database_password: str = os.getenv("DATABASE_PASSWORD", "")
        self.database_name: str = os.getenv("DATABASE_NAME", "")

    def has_database(self) -> bool:
        """Check if database configuration is available."""
        return bool(self.database_host and self.database_user and self.database_name)

    def validate(self) -> list[str]:
        """
        Validate that all required settings are present.
        Returns a list of missing configuration keys.
        """
        missing: list[str] = []

        # FMP is optional if database is configured
        if not self.fmp_api_key and not self.has_database():
            missing.append("FMP_API_KEY (or DATABASE_HOST)")

        if not self.azure_openai_endpoint:
            missing.append("AZURE_OPENAI_ENDPOINT")
        if not self.azure_openai_api_key:
            missing.append("AZURE_OPENAI_API_KEY")
        if not self.azure_openai_deployment:
            missing.append("AZURE_OPENAI_DEPLOYMENT")

        return missing

    def is_valid(self) -> bool:
        """Check if all required settings are configured."""
        return len(self.validate()) == 0


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()
