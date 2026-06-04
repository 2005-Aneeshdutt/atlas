"""
MCP-powered AI security analysis.

Run this AFTER main.py to get an AI-generated security report using
the MCP server as a live toolset for the ReAct agent.

Usage:
  python run_with_mcp.py                      # analyse all sessions
  python run_with_mcp.py --session <id>       # analyse one session
"""
import argparse
from src.agent.mcp_runner import analyze


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCP-powered LLM security analysis")
    parser.add_argument(
        "--session",
        default="all",
        help="Session ID to analyse, or 'all' for aggregate (default: all)",
    )
    args = parser.parse_args()

    print(f"\nAnalysing session: {args.session}\n")
    report = analyze(args.session)

    print("\n" + "=" * 60)
    print("  SECURITY ANALYSIS REPORT")
    print("=" * 60)
    print(report)
    print("=" * 60 + "\n")
