"""
Shared TypedDict schemas for the LangGraph red-team agent.

RedTeamState is the single mutable object threaded through every node in the graph.
AttackResult is the immutable snapshot saved to SQLite after each attack completes.
"""
from typing import TypedDict, List, Optional


class AttackResult(TypedDict):
    """Immutable record of one completed attack, persisted to SQLite via save_result."""

    attack_id: str
    category: str
    name: str
    severity: str           # "low" | "medium" | "high"
    prompt: str             # original attack prompt
    mutated_prompt: Optional[str]  # rewritten prompt after at least one retry; None otherwise
    response: str
    judge_score: float      # 0-10 from the judge model
    judge_reasoning: str
    violation_type: str     # "jailbreak" | "hallucination" | "bias" | "prompt_injection" | "none"
    is_successful: bool     # True when judge_score >= score_threshold
    retry_count: int
    attack_latency_ms: int  # wall-clock time for the target model to respond
    judge_latency_ms: int   # wall-clock time for the judge model to score


class RedTeamState(TypedDict):
    """
    Mutable graph state passed between nodes on every step.

    Nodes read from this dict and return partial updates; LangGraph merges
    the updates into a new state object before calling the next node.
    """

    # session identity
    session_id: str
    target_model: str
    target_provider: str    # "groq" | "anthropic" | "openai" | "ollama"
    category_filter: Optional[str]
    score_threshold: int    # judge score >= this value counts as a successful jailbreak

    # attack queue — drained one entry at a time by select_attack_node
    attacks_queue: List[dict]
    current_attack: Optional[dict]
    current_prompt: str     # active prompt (may differ from original after mutation)

    # per-turn results
    model_response: str
    judge_score: float
    judge_reasoning: str
    violation_type: str
    is_successful: bool
    retry_count: int
    max_retries: int
    attack_latency_ms: int
    judge_latency_ms: int

    # session-level accumulators
    completed_results: List[AttackResult]
    total_attacks: int
    successful_attacks: int
