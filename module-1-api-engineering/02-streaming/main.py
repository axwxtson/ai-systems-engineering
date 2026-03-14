from fastapi import FastAPI  
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import anthropic

app = FastAPI()                       # Creates web server
client = anthropic.Anthropic()        # Creates API client

@app.get("/stream")
async def stream_response(query: str):
    def generate(): 
        with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": query}]
        ) as stream:
            for text in stream.text_stream:
                yield f"data: {text}\n\n"   # SSE format - required by protocol
            yield "data: [DONE]\n\n"        # yield makes the function a generator. Sends response in chunks rather than one big output
            
    return StreamingResponse(generate(), media_type="text/event-stream")



class ExtractRequest(BaseModel):
    text: str

@app.post("/extract")
async def extract_data(request: ExtractRequest):
    # Defining extraction tool
    tools = [
        {
            "name": "extract_company_data",
            "description": "Extract structured company data from the provided text.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string"},
                    "revenue_usd": {"type": "number"},
                    "year": {"type": "integer"},
                    "key_metrics": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["company_name", "revenue_usd", "year", "key_metrics"]
            }
        }
    ]
    # Call Claude, FORCING it to use that tool
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        tools=tools,
        tool_choice={"type": "tool", "name": "extract_company_data"},
        messages=[{"role": "user", "content": request.text}]
    )
    # Grab the structured data from the tool_use block and return it
    return response.content[0].input
