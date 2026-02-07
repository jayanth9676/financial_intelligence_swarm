"""Configuration settings loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Google AI (primary)
    google_api_key: str = ""
    model_id: str = "gemini-2.0-flash"

    # AWS Bedrock (fallback when Gemini rate limited)
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v2:0"

    # LLM Provider: "gemini", "bedrock", or "auto" (tries gemini first, falls back to bedrock)
    llm_provider: str = "auto"

    # Embedding Provider: "local" (fastembed) or "bedrock"
    embedding_provider: str = "local"

    # Neo4j Graph Database
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = ""

    # Qdrant Vector Store
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    # Mem0 Agent Memory
    mem0_api_key: str = ""

    def has_bedrock_credentials(self) -> bool:
        """Check if AWS Bedrock credentials are configured."""
        return bool(self.aws_access_key_id and self.aws_secret_access_key)

    def has_gemini_credentials(self) -> bool:
        """Check if Google Gemini credentials are configured."""
        return bool(self.google_api_key)


settings = Settings()
