from manager import ConversationManager

manager = ConversationManager(
    model="claude-sonnet-4-20250514",
    system_prompt="You are a helpful market analyst. Provide concise analysis of market trends, assets, and economic data.",
    max_context_tokens=2000
)

print("Conversation Manager — type 'quit' to exit, 'stats' to see token usage\n")

while True:
    user_input = input("You: ")
    
    if user_input.lower() == "quit":
        break
    
    if user_input.lower() == "stats":
        print(f"\n{manager.get_stats()}\n")
        continue
    
    response = manager.chat(user_input)
    print(f"\nClaude: {response}\n")