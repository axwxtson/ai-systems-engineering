import anthropic
import json

class ConversationManager:
    def __init__(self, model, system_prompt, max_context_tokens=100000, recent_to_keep=10):
        self.client = anthropic.Anthropic()
        self.model = model
        self.system_prompt = system_prompt
        self.max_context_tokens = max_context_tokens
        self.recent_to_keep = recent_to_keep
        self.messages = []
        self.total_turns = 0
        self.summaries_performed = 0

    def chat(self, user_input):
        self.messages.append({"role": "user", "content": user_input})

        # Check if we need to summarise before calling the API
        self._manage_context()

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=self.system_prompt,
            messages=self.messages
        )
        
        assistant_text = response.content[0].text
        self.messages.append({"role": "assistant", "content": response.content})
        self.total_turns += 1
        
        return assistant_text

    def _count_tokens(self):
        response = self.client.messages.count_tokens(
            model=self.model,
            messages=self.messages
        )
        return response.input_tokens

    def _summarise_old_messages(self, old_messages) -> str:
        summary_response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system="Summarise this conversation concisely. Preserve key facts, decisions, and context.",
            messages=old_messages
        )
        return summary_response.content[0].text

    def _manage_context(self) -> list:
        token_count = self._count_tokens()
        
        if token_count <= self.max_context_tokens:
            return 
        
        # Keep the last 10 messages intact, summarise everything before
        recent = self.messages[-self.recent_to_keep:]
        old = self.messages[:-self.recent_to_keep]
        
        if not old:
            return
        
        summary = self._summarise_old_messages(old)
        
        self.messages = [
            {"role": "user", "content": f"[Previous conversation summary: {summary}]"},
            {"role": "assistant", "content": "Understood, I have the context from our previous conversation."},
            *recent
        ] 
        self.summaries_performed += 1


    def get_stats(self):
        if not self.messages:
            return {
                "total_turns": self.total_turns,
                "current_tokens": 0,
                "summaries_performed": self.summaries_performed
            }
        
        token_count = self.client.messages.count_tokens(
            model=self.model,
            messages=self.messages
        ).input_tokens
        
        return {
            "total_turns": self.total_turns,
            "current_tokens": token_count,
            "summaries_performed": self.summaries_performed
        }