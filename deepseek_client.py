from typing import Generator
from langchain_chat import LangChainChat


class DeepSeekClient:
    def __init__(self):
        self.chat = LangChainChat()

    def get_chat_response(self, messages: list[dict[str, str]], stream: bool = True) -> Generator[str, None, None]:
        """Get response from DeepSeek API using LangChain"""
        # Extract user input from messages
        user_input = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_input = msg.get("content", "")
                break

        if not user_input:
            yield "No user input found in messages."
            return

        # Stream response from chat
        for chunk in self.chat.stream_response(user_input):
            yield chunk

    def clear_conversation(self):
        """Clear conversation history"""
        self.chat.clear_history()