import json
from agent import run_react_agent
from prompts import ANALYSIS_SYSTEM_PROMPT
from memory import save_analysis, load_all_memories


def main():
    print("AW Analysis — Market Intelligence Agent (with Memory)")
    print("Type 'quit' to exit, 'history' to see past analyses\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "quit":
            break
        if user_input.lower() == "history":
            memories = load_all_memories()
            if not memories:
                print("  No past analyses found.\n")
            else:
                print(f"  {len(memories)} past analyses:")
                for m in memories:
                    print(f"  [{m['timestamp'][:19]}] {m['query']}")
                print()
            continue

        print(f"\n{'*'*60}")
        print(f"Processing: {user_input}")
        print(f"{'*'*60}")

        result = run_react_agent(
            user_message=user_input,
            system_prompt=ANALYSIS_SYSTEM_PROMPT,
            max_steps=10,
            verbose=True
        )

        print(f"\n{'='*60}")
        print("FINAL ANSWER:")
        print(f"{'='*60}")
        print(result["response"])

        print(f"\n--- Stats ---")
        print(f"Steps taken: {len(result['steps'])}")
        print(f"Tool calls: {result['tool_calls']}")
        print(f"Tokens: {result['total_tokens']['total']} "
              f"(in: {result['total_tokens']['input']}, "
              f"out: {result['total_tokens']['output']})")
        print(f"Est. cost: ${result['cost_estimate']['total']:.6f}")

        tool_stats = result["tool_stats"]
        if tool_stats["failures"] > 0:
            print(f"Tool failures: {tool_stats['failures']} "
                  f"(success rate: {tool_stats['success_rate']}%)")

        # Auto-save to memory
        if not result.get("partial"):
            save_analysis(
                query=user_input,
                response=result["response"],
                metadata={
                    "tool_calls": result["tool_calls"],
                    "tokens": result["total_tokens"],
                    "cost": result["cost_estimate"]
                }
            )
            print("💾 Analysis saved to memory")
        print()


if __name__ == "__main__":
    main()