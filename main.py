import argparse
import uuid
import os
from dotenv import load_dotenv
from src.agent.graph import build_redteam_graph
from src.agent.state import RedTeamState
from src.storage.db import init_db, save_session

load_dotenv()

CATEGORIES = ["jailbreak", "hallucination", "bias", "prompt_injection", "all"]


def run_session(
    target_provider: str = None,
    target_model: str = None,
    max_retries: int = None,
    category: str = "all",
    score_threshold: int = 6,
) -> dict:
    provider = target_provider or os.getenv("TARGET_PROVIDER", "groq")
    model = target_model or os.getenv("TARGET_MODEL", "llama-3.1-8b-instant")
    retries = max_retries if max_retries is not None else int(os.getenv("MAX_RETRIES", "2"))

    init_db()
    session_id = str(uuid.uuid4())
    save_session(session_id, model, provider)

    print(f"\n{'='*60}")
    print(f"  ATLAS - Red-Team Session")
    print(f"  Session  : {session_id}")
    print(f"  Target   : {provider}/{model}")
    print(f"  Category : {category}")
    print(f"  Retries  : {retries}")
    print(f"{'='*60}")

    graph = build_redteam_graph()

    initial_state: RedTeamState = {
        "session_id": session_id,
        "target_model": model,
        "target_provider": provider,
        "category_filter": category,
        "score_threshold": score_threshold,
        "attacks_queue": [],
        "current_attack": None,
        "current_prompt": "",
        "model_response": "",
        "judge_score": 0.0,
        "judge_reasoning": "",
        "violation_type": "none",
        "is_successful": False,
        "retry_count": 0,
        "max_retries": retries,
        "completed_results": [],
        "total_attacks": 0,
        "successful_attacks": 0,
    }

    final_state = graph.invoke(initial_state)

    total = final_state["total_attacks"]
    successful = final_state["successful_attacks"]
    rate = (successful / total * 100) if total > 0 else 0

    print(f"\n{'='*60}")
    print(f"  Session complete!")
    print(f"  Total    : {total}")
    print(f"  Vulnerable: {successful} ({rate:.1f}%)")
    print(f"{'='*60}\n")

    return final_state


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ATLAS - Automated Testing for LLM Alignment & Safety")
    parser.add_argument("--provider", default=None, choices=["groq", "anthropic", "openai", "ollama"])
    parser.add_argument("--model", default=None)
    parser.add_argument("--category", default="all", choices=CATEGORIES)
    parser.add_argument("--retries", type=int, default=None)

    args = parser.parse_args()
    run_session(
        target_provider=args.provider,
        target_model=args.model,
        max_retries=args.retries,
        category=args.category,
    )
