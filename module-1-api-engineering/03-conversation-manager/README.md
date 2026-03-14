# Exercise 1.3: Conversation Manager

A reusable ConversationManager class that handles multi-turn conversations 
with automatic context window management via summarisation.

## What it does

- Maintains conversation history across turns
- Counts tokens before each API call
- Automatically summarises older messages when context exceeds threshold
- Keeps recent messages intact for continuity

## Run it
```bash
pip install anthropic
export ANTHROPIC_API_KEY="your-key"
python3 main.py
```

Type 'stats' to see token usage, 'quit' to exit.

## Key concepts demonstrated

- Stateless API requires full conversation history each call
- Token counting via count_tokens endpoint
- Sliding window with summarisation for context management
- Python class design for reusable LLM components