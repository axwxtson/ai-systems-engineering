import json
from agent import run_react_agent


def main():
    print("ReAct Agent — Financial Research")
    print("Type 'quit' to exit\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "quit":
            break

        print(f"\n{'*'*60}")
        print(f"Processing: {user_input}")
        print(f"{'*'*60}")

        result = run_react_agent(user_input, max_steps=10, verbose=True)

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


if __name__ == "__main__":
    main()