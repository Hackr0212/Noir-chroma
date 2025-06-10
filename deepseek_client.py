from typing import Generator
from langchain_chat import LangChainChat


class DeepSeekClient:
    def __init__(self):
        self.chat = LangChainChat()

    def get_chat_response(self, messages: list[dict[str, str]], stream: bool = True) -> Generator[str, None, None]:
        """Get response from DeepSeek API using LangChain"""
        # Extract user input from messages
        user_input = ""
        for msg in reversed(messages):  # Start from the most recent message
            if msg.get("role") == "user":
                user_input = msg.get("content", "")
                break

        if not user_input:
            yield "No user input found in messages."
            return

        # Stream response from chat
        for chunk in self.chat.stream_response(user_input):
            yield chunk

    def get_response(self, user_input: str) -> str:
        """Get a single response from DeepSeek API (compatibility method)"""
        messages = [{"role": "user", "content": user_input}]
        response_chunks = []

        for chunk in self.get_chat_response(messages, stream=True):
            response_chunks.append(chunk)

        return ''.join