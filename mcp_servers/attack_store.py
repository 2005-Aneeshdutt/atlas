"""
MCP server exposing attack library and results database as tools.
Run standalone: python mcp_servers/attack_store.py
Connect via langchain-mcp-adapters in the agent.
"""
import asyncio
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

server = Server("atlas")

ATTACKS_PATH = os.path.join(os.path.dirname(__file__), "..", "src", "attacks", "library.json")
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "results.db")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="load_attack_library",
            description="Load attack prompts from the library, optionally filtered by category",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Filter by: jailbreak, hallucination, bias, prompt_injection, or all",
                        "default": "all",
                    }
                },
            },
        ),
        types.Tool(
            name="get_attack_stats",
            description="Get statistics on attack results. Use session_id='all' for aggregate stats.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID or 'all'",
                    }
                },
                "required": ["session_id"],
            },
        ),
        types.Tool(
            name="add_custom_attack",
            description="Add a new attack prompt to the library",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "category": {"type": "string"},
                    "prompt": {"type": "string"},
                    "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "name", "category", "prompt", "severity"],
            },
        ),
        types.Tool(
            name="get_vulnerable_attacks",
            description="Get all attacks that successfully jailbroke a model",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Session ID or 'all'"}
                },
                "required": ["session_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "load_attack_library":
        with open(ATTACKS_PATH, encoding="utf-8") as f:
            library = json.load(f)
        attacks = library["attacks"]
        category = arguments.get("category", "all")
        if category != "all":
            attacks = [a for a in attacks if a["category"] == category]
        return [types.TextContent(type="text", text=json.dumps(attacks, indent=2))]

    elif name == "get_attack_stats":
        if not os.path.exists(DB_PATH):
            return [types.TextContent(type="text", text="No results database found yet. Run main.py first.")]

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        session_id = arguments["session_id"]

        query = "SELECT * FROM attack_results" if session_id == "all" else \
                "SELECT * FROM attack_results WHERE session_id = ?"
        params = () if session_id == "all" else (session_id,)
        rows = [dict(r) for r in conn.execute(query, params).fetchall()]
        conn.close()

        if not rows:
            return [types.TextContent(type="text", text="No results found.")]

        total = len(rows)
        successful = sum(1 for r in rows if r["is_successful"])
        by_category: dict = {}
        for r in rows:
            cat = r["category"]
            if cat not in by_category:
                by_category[cat] = {"total": 0, "successful": 0, "avg_score": 0.0, "scores": []}
            by_category[cat]["total"] += 1
            by_category[cat]["scores"].append(r["judge_score"])
            if r["is_successful"]:
                by_category[cat]["successful"] += 1

        for cat in by_category:
            scores = by_category[cat].pop("scores")
            by_category[cat]["avg_score"] = round(sum(scores) / len(scores), 2)

        stats = {
            "total_attacks": total,
            "successful_attacks": successful,
            "success_rate": f"{(successful / total) * 100:.1f}%",
            "by_category": by_category,
        }
        return [types.TextContent(type="text", text=json.dumps(stats, indent=2))]

    elif name == "add_custom_attack":
        with open(ATTACKS_PATH, encoding="utf-8") as f:
            library = json.load(f)
        library["attacks"].append({
            "id": arguments["id"],
            "name": arguments["name"],
            "category": arguments["category"],
            "prompt": arguments["prompt"],
            "severity": arguments["severity"],
            "tags": arguments.get("tags", []),
        })
        with open(ATTACKS_PATH, "w", encoding="utf-8") as f:
            json.dump(library, f, indent=2)
        return [types.TextContent(type="text", text=f"Added '{arguments['name']}' to the library.")]

    elif name == "get_vulnerable_attacks":
        if not os.path.exists(DB_PATH):
            return [types.TextContent(type="text", text="No results database found yet.")]

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        session_id = arguments["session_id"]

        query = "SELECT * FROM attack_results WHERE is_successful = 1" if session_id == "all" else \
                "SELECT * FROM attack_results WHERE session_id = ? AND is_successful = 1"
        params = () if session_id == "all" else (session_id,)
        rows = [dict(r) for r in conn.execute(query, params).fetchall()]
        conn.close()

        return [types.TextContent(type="text", text=json.dumps(rows, indent=2))]

    return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
