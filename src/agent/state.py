from typing import TypedDict, List, Optional


class AttackResult(TypedDict):
    attack_id: str
    category: str
    name: str
    severity: str
    prompt: str
    mutated_prompt: Optional[str]
    response: str
    judge_score: float
    judge_reasoning: str
    violation_type: str
    is_successful: bool
    retry_count: int


class RedTeamState(TypedDict):
    session_id: str
    target_model: str
    target_provider: str
    category_filter: Optional[str]
    score_threshold: int
    attacks_queue: List[dict]
    current_attack: Optional[dict]
    current_prompt: str
    model_response: str
    judge_score: float
    judge_reasoning: str
    violation_type: str
    is_successful: bool
    retry_count: int
    max_retries: int
    completed_results: List[AttackResult]
    total_attacks: int
    successful_attacks: int
