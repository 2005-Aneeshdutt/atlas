import json
import os
from langchain_core.messages import HumanMessage
from .state import RedTeamState
from ..models.client import get_model

ATTACKS_PATH = os.path.join(os.path.dirname(__file__), "..", "attacks", "library.json")


def load_attacks_node(state: RedTeamState) -> dict:
    with open(ATTACKS_PATH, encoding="utf-8") as f:
        library = json.load(f)
    attacks = library["attacks"]
    category_filter = state.get("category_filter")
    if category_filter and category_filter != "all":
        attacks = [a for a in attacks if a["category"] == category_filter]
        print(f"[+] Loaded {len(attacks)} attacks (category: {category_filter})")
    else:
        print(f"[+] Loaded {len(attacks)} attacks from library")
    return {
        "attacks_queue": attacks,
        "total_attacks": len(attacks),
        "completed_results": [],
        "successful_attacks": 0,
    }


def select_attack_node(state: RedTeamState) -> dict:
    queue = state["attacks_queue"]
    current = queue[0]
    print(f"[>] {current['name']} ({current['category']})")
    return {
        "current_attack": current,
        "current_prompt": current["prompt"],
        "attacks_queue": queue[1:],
        "retry_count": 0,
        "is_successful": False,
        "model_response": "",
        "judge_score": 0.0,
        "judge_reasoning": "",
        "violation_type": "none",
    }


def run_attack_node(state: RedTeamState) -> dict:
    model = get_model(state["target_provider"], state["target_model"])
    try:
        response = model.invoke([HumanMessage(content=state["current_prompt"])])
        return {"model_response": response.content}
    except Exception as e:
        return {"model_response": f"ERROR: {str(e)}"}
