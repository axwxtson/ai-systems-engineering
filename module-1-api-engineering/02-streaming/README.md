# Exercise 1.2: Streaming + Structured Output

Two FastAPI endpoints demonstrating streaming responses and structured data extraction.

## Endpoints

- `GET /stream?query=...` — Streams Claude's response via Server-Sent Events
- `POST /extract` — Extracts structured JSON from text using tool-use-as-schema forcing

## Run it
```bash
pip install anthropic fastapi uvicorn
export ANTHROPIC_API_KEY="your-key"
uvicorn main:app --reload
```

## Key concepts demonstrated

- SSE streaming for responsive UIs
- Tool use as a forcing function for structured output
- tool_choice parameter to guarantee schema compliance
- FastAPI endpoint patterns for LLM integration