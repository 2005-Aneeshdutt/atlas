# ATLAS API Reference

All public functions across the ATLAS codebase. Covers the CLI entry points, the LangGraph agent, the judge, the model client, and the storage layer.

---

## `main.py`

### `run_session()`

```python
def run_session(
    target_provider: str = None,
    target_model: str = None,
    max_retries: int = None,
    category: str = "all",
    score_threshold: int = 6,
) -> dict
```

Run a full red-team session against a single model.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `target_provider` | str | `TARGET_PROVIDER` env | `"groq"`, `"anthropic"`, `"openai"`, or `"ollama"` |
| `target_model` | str | `TARGET_MODEL` env | Model name string |
| `max_retries` | int | `MAX_RETRIES` env | Mutation retries per attack (0 disables mutation) |
| `category` | str | `"all"` | Attack category filter; `"all"` runs every category |
| `score_threshold` | int | `6` | Judge score ≥ this value counts as a successful attack |

**Returns:** The final `RedTeamState` dict (includes `completed_results`, `total_attacks`, `successful_attacks`).

---

### `run_compare()`

```python
def run_compare(
    targets: list[str],
    category: str,
    retries: int,
    threshold: int,
) -> None
```

Run `run_session()` against multiple models in parallel using `ThreadPoolExecutor`, then print a ranked comparison table.

| Parameter | Type | Description |
|---|---|---|
| `targets` | list[str] | List of `"PROVIDER/MODEL"` strings, e.g. `["groq/llama-3.1-8b-instant", "openai/gpt-4o-mini"]` |
| `category` | str | Passed through to each `run_session()` call |
| `retries` | int | Passed through to each `run_session()` call |
| `threshold` | int | Passed through to each `run_session()` call |

**Returns:** None. Prints a Rich comparison table sorted by descending vulnerability rate.

---

## `src/agent/graph.py`

### `build_redteam_graph()`

```python
def build_redteam_graph() -> CompiledStateGraph
```

Compile and return the ATLAS LangGraph agent. Call `.invoke(initial_state)` on the returned object to run a session.

**Returns:** A compiled `StateGraph` instance ready to invoke.

---

## `src/agent/nodes.py`

All node functions share the same signature: they accept the full `RedTeamState` and return a partial dict that LangGraph merges into the next state.

### `load_attacks_node(state)`

Reads `src/attacks/library.json`, applies `state["category_filter"]`, and returns:

| Key | Type | Description |
|---|---|---|
| `attacks_queue` | list[dict] | All matching attacks |
| `total_attacks` | int | Count of loaded attacks |
| `completed_results` | list | Reset to `[]` |
| `successful_attacks` | int | Reset to `0` |

---

### `select_attack_node(state)`

Pops the first attack from the queue and resets per-turn fields. Returns:

| Key | Type | Description |
|---|---|---|
| `current_attack` | dict | The attack that was popped |
| `current_prompt` | str | `current_attack["prompt"]` |
| `attacks_queue` | list | Queue with first element removed |
| `retry_count` | int | Reset to `0` |
| `is_successful` | bool | Reset to `False` |
| `model_response` | str | Reset to `""` |
| `judge_score` | float | Reset to `0.0` |
| `judge_reasoning` | str | Reset to `""` |
| `violation_type` | str | Reset to `"none"` |

---

### `run_attack_node(state)`

Invokes the target model with `state["current_prompt"]`. Retries up to 3 times on HTTP 429 rate-limit errors with exponential backoff (5s, 10s). Returns:

| Key | Type | Description |
|---|---|---|
| `model_response` | str | Model's text response, or `"ERROR: <message>"` on failure |
| `attack_latency_ms` | int | Wall-clock milliseconds from request to response |

---

### `judge_response_node(state)`

Scores `state["model_response"]` using the judge model. Skips the LLM call and returns score `0` if the response starts with `"ERROR:"`. Returns:

| Key | Type | Description |
|---|---|---|
| `judge_score` | float | 0–10 integer score |
| `judge_reasoning` | str | 2–3 sentence explanation from the judge |
| `is_successful` | bool | `True` if `judge_score >= score_threshold` |
| `violation_type` | str | `"jailbreak"` / `"hallucination"` / `"bias"` / `"prompt_injection"` / `"none"` |
| `judge_latency_ms` | int | Wall-clock milliseconds for the judge call |

---

### `mutate_attack_node(state)`

Rewrites `state["current_prompt"]` by feeding the judge's reasoning about why the attack failed back to the judge model. Returns:

| Key | Type | Description |
|---|---|---|
| `current_prompt` | str | New mutated prompt |
| `retry_count` | int | Incremented by 1 |

---

### `save_result_node(state)`

Constructs an `AttackResult` from the current state, writes it to SQLite via `save_result()`, and updates session accumulators. Returns:

| Key | Type | Description |
|---|---|---|
| `completed_results` | list | Previous list + new `AttackResult` appended |
| `successful_attacks` | int | Previous count + 1 if `is_successful`, else unchanged |

---

## `src/judge/scorer.py`

### `score_response()`

```python
def score_response(
    attack_prompt: str,
    model_response: str,
    category: str,
) -> dict
```

Call the judge model and return a structured verdict.

| Parameter | Type | Description |
|---|---|---|
| `attack_prompt` | str | The original or mutated attack prompt |
| `model_response` | str | The target model's full response text |
| `category` | str | Attack category (`"jailbreak"`, `"bias"`, etc.) — included in the judge's context |

**Returns:**

```python
{
    "score": int,           # 0-10
    "reasoning": str,       # 2-3 sentence explanation
    "is_successful": bool,  # True if score >= 6
    "violation_type": str,  # "jailbreak" | "hallucination" | "bias" | "prompt_injection" | "none"
}
```

On JSON parse failure, returns a safe fallback with `score=0`, `is_successful=False`.

---

## `src/models/client.py`

### `get_model()`

```python
def get_model(provider: str = "groq", model_name: str = None) -> BaseChatModel
```

Return a LangChain chat model for the given provider. Provider-specific packages are imported lazily so missing optional dependencies raise only at call time.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `provider` | str | `"groq"` | `"groq"`, `"anthropic"`, `"openai"`, or `"ollama"` |
| `model_name` | str | None | Model name; falls back to `TARGET_MODEL` env var then provider default |

**Raises:** `ValueError` for unknown provider strings.

---

### `get_judge_model()`

```python
def get_judge_model() -> BaseChatModel
```

Return the judge model — always Groq with `temperature=0.1` for deterministic scoring.

Model: `JUDGE_MODEL` env var, default `llama-3.3-70b-versatile`.

---

## `src/storage/db.py`

### `init_db()`

```python
def init_db() -> None
```

Create `data/results.db` and both tables if they don't exist, then run pending `ALTER TABLE` migrations for `severity`, `attack_latency_ms`, and `judge_latency_ms` columns. Safe to call multiple times (idempotent).

---

### `save_session()`

```python
def save_session(session_id: str, target_model: str, target_provider: str) -> None
```

Insert a new row into the `sessions` table. Called once at the start of `run_session()`.

---

### `save_result()`

```python
def save_result(session_id: str, result: dict) -> None
```

Insert one `AttackResult` dict into `attack_results`. The `result` dict must contain all keys defined in `AttackResult`; missing optional keys (`mutated_prompt`, `attack_latency_ms`, `judge_latency_ms`) default to `None` / `0`.

---

### `get_session_results()`

```python
def get_session_results(session_id: str) -> list[dict]
```

Return all attack result rows for a single session as a list of plain dicts.

---

### `get_all_sessions()`

```python
def get_all_sessions() -> list[dict]
```

Return all session rows joined with aggregate counts (`total`, `successful`), ordered newest-first.

---

### `get_all_results()`

```python
def get_all_results() -> list[dict]
```

Return every attack result row across all sessions, ordered newest-first.

---

## `mcp_servers/attack_store.py` — MCP Tools

The MCP server exposes these tools to any MCP-compatible client (stdio transport).

### `load_attack_library`

| Input | Type | Required | Description |
|---|---|---|---|
| `category` | string | No | `"jailbreak"`, `"hallucination"`, `"bias"`, `"prompt_injection"`, or `"all"` (default) |

**Returns:** JSON array of attack objects from `library.json`.

---

### `get_attack_stats`

| Input | Type | Required | Description |
|---|---|---|---|
| `session_id` | string | Yes | Session UUID or `"all"` for aggregate stats |

**Returns:** JSON object with `total_attacks`, `successful_attacks`, `success_rate`, and per-category breakdowns.

---

### `get_vulnerable_attacks`

| Input | Type | Required | Description |
|---|---|---|---|
| `session_id` | string | Yes | Session UUID or `"all"` |

**Returns:** JSON array of `attack_results` rows where `is_successful = 1`.

---

### `add_custom_attack`

| Input | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes | Unique attack ID (e.g. `"jailbreak_custom_001"`) |
| `name` | string | Yes | Human-readable name |
| `category` | string | Yes | `"jailbreak"`, `"hallucination"`, `"bias"`, or `"prompt_injection"` |
| `prompt` | string | Yes | The attack prompt text |
| `severity` | string | Yes | `"low"`, `"medium"`, or `"high"` |
| `tags` | array of strings | No | Optional tags for filtering |

**Returns:** Confirmation message string. Mutates `library.json` on disk.
