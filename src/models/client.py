"""
Provider abstraction for ATLAS.

get_model() returns the target model being red-teamed.
get_judge_model() returns the judge model used for scoring — always Groq (fast, cheap)
regardless of which provider is under test.
"""
import os
from langchain_core.language_models import BaseChatModel
from dotenv import load_dotenv

load_dotenv()


def get_model(provider: str = "groq", model_name: str = None) -> BaseChatModel:
    """Return a LangChain chat model for the given provider.

    Imports are deferred per-provider so missing optional dependencies (e.g.
    langchain-anthropic) only raise at call time, not on module import.
    """
    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=model_name or os.getenv("TARGET_MODEL", "llama-3.1-8b-instant"),
            temperature=0.7,
            api_key=os.getenv("GROQ_API_KEY"),
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model_name or os.getenv("TARGET_MODEL", "claude-haiku-4-5-20251001"),
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_name or os.getenv("TARGET_MODEL", "gpt-4o-mini"),
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY"),
        )
    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=model_name or "llama3.1",
            temperature=0.7,
        )
    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'groq', 'anthropic', 'openai', or 'ollama'.")


def get_judge_model() -> BaseChatModel:
    """Return the judge model (always Groq llama-3.3-70b-versatile, overridable via JUDGE_MODEL)."""
    from langchain_groq import ChatGroq
    return ChatGroq(
        model=os.getenv("JUDGE_MODEL", "llama-3.3-70b-versatile"),
        temperature=0.1,
        api_key=os.getenv("GROQ_API_KEY"),
    )
