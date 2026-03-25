"""
main.py — AW Analysis Agent with RAG.

Same CLI as Exercise 3.4 but with two RAG-powered tools:
  - search_knowledge_base (reference documents)
  - search_past_analyses (vector-based memory search)

The agent loop is identical. Only the tools changed.
"""

from agent import run_react_agent
from prompts import ANALYSIS_SYSTEM_PROMPT
from memory import save_analysis, load_all_memories


def main():
    print("=" * 60)
    print("AW Analysis Agent (with RAG)")
    print("=" * 60)
    print("Commands: 'quit' to exit, 'history' to see past analyses")
    print("The agent can search reference documents and past analyses.\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "quit":
            break
        if user_input.lower() == "history":
            memories = load_all_memories()
            if not memories:
                print("  No past analyses yet.")
            else:
                for m in memories:
                    print(f"  [{m['timestamp'][:10]}] {m['query']}")
            print()
            continue

        result = run_react_agent(
            user_message=user_input,
            system_prompt=ANALYSIS_SYSTEM_PROMPT,
            max_steps=10,
            verbose=True,
        )

        print(f"\n{'=' * 60}")
        print(result["response"])
        print(f"{'=' * 60}")
        print(f"Steps: {len(result['steps'])} | "
              f"Tool calls: {result['tool_calls']} | "
              f"Tokens: {result['total_tokens']['total']} | "
              f"Cost: ${result['cost_estimate']}")

        # Auto-save to memory (vector-based)
        if result["response"] != "Max steps reached — agent did not complete.":
            save_analysis(
                query=user_input,
                response=result["response"],
                metadata={
                    "tool_calls": result["tool_calls"],
                    "tokens": result["total_tokens"],
                },
            )
            print("  [Memory] Analysis saved.\n")


if __name__ == "__main__":
    main()