"""LLM provider management with automatic fallback support.

Supports:
- Google Gemini (primary)
- AWS Bedrock (fallback when Gemini rate limited)
"""

from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from backend.config import settings

# Track rate limit state
_gemini_rate_limited = False


def reset_rate_limit():
    """Reset the rate limit flag (call after waiting)."""
    global _gemini_rate_limited
    _gemini_rate_limited = False


def mark_gemini_rate_limited():
    """Mark Gemini as rate limited to trigger fallback."""
    global _gemini_rate_limited
    _gemini_rate_limited = True


def get_gemini_llm(temperature: float = 0.3) -> Optional[BaseChatModel]:
    """Get Google Gemini LLM if available."""
    if not settings.has_gemini_credentials():
        return None

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.model_id,
            google_api_key=settings.google_api_key,
            temperature=temperature,
            max_output_tokens=8192,
        )
    except Exception:
        return None


def get_bedrock_llm(temperature: float = 0.3) -> Optional[BaseChatModel]:
    """Get AWS Bedrock LLM if available."""
    if not settings.has_bedrock_credentials():
        return None

    try:
        from langchain_aws import ChatBedrock
        import boto3

        # Create boto3 client with credentials
        bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )

        return ChatBedrock(
            client=bedrock_client,
            model_id=settings.bedrock_model_id,
            model_kwargs={"temperature": temperature},
        )
    except Exception:
        return None


def get_llm(temperature: float = 0.3) -> BaseChatModel:
    """Get the best available LLM based on configuration and rate limits.

    Order of preference:
    1. If provider is "gemini" - use Gemini only
    2. If provider is "bedrock" - use Bedrock only
    3. If provider is "auto" - try Gemini first, fall back to Bedrock if rate limited

    Args:
        temperature: LLM temperature setting

    Returns:
        Configured LLM instance

    Raises:
        RuntimeError: If no LLM is available
    """
    global _gemini_rate_limited

    provider = settings.llm_provider.lower()

    if provider == "gemini":
        llm = get_gemini_llm(temperature)
        if llm:
            return llm
        raise RuntimeError("Gemini LLM not available. Check GOOGLE_API_KEY.")

    if provider == "bedrock":
        llm = get_bedrock_llm(temperature)
        if llm:
            return llm
        raise RuntimeError(
            "Bedrock LLM not available. Check AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY."
        )

    # Auto mode - try Gemini first, fall back to Bedrock
    if not _gemini_rate_limited:
        llm = get_gemini_llm(temperature)
        if llm:
            return llm

    # Try Bedrock as fallback
    llm = get_bedrock_llm(temperature)
    if llm:
        return llm

    # Last resort - try Gemini even if rate limited
    llm = get_gemini_llm(temperature)
    if llm:
        return llm

    raise RuntimeError(
        "No LLM available. Configure either GOOGLE_API_KEY or AWS Bedrock credentials."
    )


def invoke_with_fallback(llm: BaseChatModel, messages: list, tools: list = None):
    """Invoke LLM with automatic fallback on rate limit errors.

    Args:
        llm: The LLM to use
        messages: Messages to send
        tools: Optional list of tools to bind

    Returns:
        LLM response

    Raises:
        Exception: If all providers fail
    """
    global _gemini_rate_limited

    llm_to_use = llm
    if tools:
        llm_to_use = llm.bind_tools(tools)

    try:
        return llm_to_use.invoke(messages)
    except Exception as e:
        error_str = str(e).lower()

        # Check if this is a rate limit error
        if "rate" in error_str or "quota" in error_str or "429" in error_str:
            mark_gemini_rate_limited()

            # Try fallback to Bedrock
            if settings.has_bedrock_credentials():
                fallback_llm = get_bedrock_llm()
                if fallback_llm:
                    if tools:
                        fallback_llm = fallback_llm.bind_tools(tools)
                    return fallback_llm.invoke(messages)

        # Re-raise if no fallback available
        raise
