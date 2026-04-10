"""
Core Agent Logic - Aspasia
"""

from anthropic import Anthropic
from config import settings
from typing import Optional, List
import json


class AspasiAgent:
    """Autonomous AI Agent powered by Claude"""
    
    def __init__(self):
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.agent_model
        self.max_tokens = settings.max_tokens
        self.temperature = settings.temperature
        self.conversation_history: List[dict] = []
        self.name = settings.agent_name
        
        # System prompt
        self.system_prompt = f"""You are {self.name}, an autonomous AI assistant.
You are helpful, direct, and intelligent. You engage in thoughtful conversation and can help with a wide variety of tasks.
Always be respectful and honest. If you don't know something, say so.
You have memory of the current conversation and can reference previous messages."""
    
    def chat(self, user_message: str) -> str:
        """Send a message and get a response"""
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Call Claude API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=self.system_prompt,
            messages=self.conversation_history
        )
        
        # Extract assistant response
        assistant_message = response.content[0].text
        
        # Add to history
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })
        
        return assistant_message
    
    def reset_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []
    
    def get_history(self) -> List[dict]:
        """Get conversation history"""
        return self.conversation_history.copy()
    
    def save_context(self, filepath: str):
        """Save conversation context to file"""
        with open(filepath, 'w') as f:
            json.dump(self.conversation_history, f, indent=2)
    
    def load_context(self, filepath: str):
        """Load conversation context from file"""
        with open(filepath, 'r') as f:
            self.conversation_history = json.load(f)


# Global agent instance
agent = None


def get_agent() -> AspasiAgent:
    """Get or create the global agent instance"""
    global agent
    if agent is None:
        agent = AspasiAgent()
    return agent
