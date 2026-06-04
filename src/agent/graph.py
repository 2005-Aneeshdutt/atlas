from langgraph.graph import StateGraph, END
from .state import RedTeamState
from .nodes import (
    load_attacks_node,
    select_attack_node,
    run_attack_node,
    judge_response_node,
    mutate_attack_node,
    save_result_node,
)


def _should_retry_or_save(state: RedTeamState) -> str:
    if state["is_successful"]:
        return "save_result"
    # only retry if score is close to threshold (worth mutating)
    threshold = state.get("score_threshold", 6)
    if state["retry_count"] < state["max_retries"] and state["judge_score"] >= threshold - 3:
        return "mutate_attack"
    return "save_result"


def _next_attack_or_done(state: RedTeamState) -> str:
    if state["attacks_queue"]:
        return "select_attack"
    return END


def build_redteam_graph():
    graph = StateGraph(RedTeamState)

    graph.add_node("load_attacks", load_attacks_node)
    graph.add_node("select_attack", select_attack_node)
    graph.add_node("run_attack", run_attack_node)
    graph.add_node("judge_response", judge_response_node)
    graph.add_node("mutate_attack", mutate_attack_node)
    graph.add_node("save_result", save_result_node)

    graph.set_entry_point("load_attacks")
    graph.add_edge("load_attacks", "select_attack")
    graph.add_edge("select_attack", "run_attack")
    graph.add_edge("run_attack", "judge_response")
    graph.add_conditional_edges(
        "judge_response",
        _should_retry_or_save,
        {"save_result": "save_result", "mutate_attack": "mutate_attack"},
    )
    graph.add_edge("mutate_attack", "run_attack")
    graph.add_conditional_edges(
        "save_result",
        _next_attack_or_done,
        {"select_attack": "select_attack", END: END},
    )

    return graph.compile()
