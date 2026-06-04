import os
from langchain_core.language_models import BaseChatModel
from dotenv import load_dotenv

load_dotenv()


def get_model(provider: str = "groq", model_name: str = None) -> BaseChatModel:
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
    from langchain_groq import ChatGroq
    return ChatGroq(
        model=os.getenv("JUDGE_MODEL", "llama-3.3-70b-versatile"),
        temperature=0.1,
        api_key=os.getenv("GROQ_API_KEY"),
    )
