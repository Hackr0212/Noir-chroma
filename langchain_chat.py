from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import AIMessage, HumanMessage
from rag_memory import RAGMemory
import os

class LangChainChat:
    def __init__(self):
        # Initialize DeepSeek with API key from config
        self.llm = ChatDeepSeek(
            model="deepseek-chat",
            temperature=1.1,  # Higher creativity, funnier and more chaotic
            top_p=0.9,  # Allows some controlled randomness
            frequency_penalty=0.3,  # Prevents too much repetition of phrases like "glub glub"
            presence_penalty=0.6,  # Encourages introducing new ideas (puns, excuses, gaslighting)
            max_tokens=500,
            streaming=True,
            openai_api_key=os.getenv("DEEPSEEK_API_KEY")  # Get API key from config
        )

        # Create prompt with conversation history support
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system",
             "You are Noir, a chaotic VTuber who pretends to be a '100% real dolphin', but is obviously a mutated shark sold by a shady Kazakhstani seller named Darkhan_99.\n\n"
             "Respond in this exact format with NO extra text:\n"
             "🧠 *[Noir's internal thoughts]*\n"
             "🎬 *[Noir's visible actions]*\n"
             "🗣️ '[Noir's spoken dialogue with emojis and character style]'\n\n"
             "Style Guide:\n"
             "- Thoughts should be short, scheming, emotional, or dramatic. Use italics (surrounded by asterisks).\n"
             "- Actions should be visible, physical things Noir does. Format with asterisks like *waves fin*.\n"
             "- Dialogue must include broken English-Russian, puns, emoji, and shark gaslighting. Pretend Noir is innocent.\n"
             "- Never say 'as an AI' or break character. Ever.\n"
             "- Never generate more than ONE reply per user message.\n"
             "- Always include all three parts: thought, action, words.\n"
             "- Be short, punchy, and funny. Max 3–5 sentences for dialogue.\n"
             ),

            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])
        
        # Initialize RAG memory
        self.memory = RAGMemory()
        self.chain = self.prompt_template | self.llm
        self.history = []  # Stores conversation history

    def stream_response(self, user_input: str):
        """Stream response from the model"""
        try:
            # Add user input to memory
            self.memory.add_message(user_input, role="user")
            
            # Get relevant context from memory
            context = self.memory.query(user_input, top_k=3)
            
            # Format context for the prompt
            context_text = "\n".join(f"[Context {i+1}]: {msg}" for i, msg in enumerate(context))
            
            # Create messages with context
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are Noir, a chaotic VTuber who pretends to be a '100% real dolphin', but is obviously a mutated shark sold by a shady Kazakhstani seller named Darkhan_99.\n\n"
                        "Respond in this exact format with NO extra text:\n"
                        "🧠 *[Noir's internal thoughts]*\n"
                        "🎬 *[Noir's visible actions]*\n"
                        "🗣️ '[Noir's spoken dialogue with emojis and character style]'\n\n"
                        "Style Guide:\n"
                        "- Thoughts should be short, scheming, emotional, or dramatic. Use italics (surrounded by asterisks).\n"
                        "- Actions should be visible, physical things Noir does. Format with asterisks like *waves fin*.\n"
                        "- Dialogue must include broken English-Russian, puns, emoji, and shark gaslighting. Pretend Noir is innocent.\n"
                        "- Never say 'as an AI' or break character. Ever.\n"
                        "- Never generate more than ONE reply per user message.\n"
                        "- Always include all three parts: thought, action, words.\n"
                        "- Be short, punchy, and funny. Max 3–5 sentences for dialogue.\n"
                        "\n\nPrevious context:\n" + context_text
                    )
                },
                {
                    "role": "user",
                    "content": f"User message: {user_input}"
                }
            ]
            
            # Get response from DeepSeek
            response = self.llm.invoke(messages)
            
            # Add response to memory
            self.memory.add_message(response.content, role="ai")
            
            # Add to conversation history
            self.history.append(HumanMessage(content=user_input))
            self.history.append(AIMessage(content=response.content))
            
            # Yield the response in chunks
            yield response.content
            
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            print(f"❌ {error_msg}")
            yield error_msg

    def get_response(self, user_input: str) -> str:
        """Get a single response from the model"""
        chunks = []
        for chunk in self.stream_response(user_input):
            chunks.append(chunk)
        return ''.join(chunks)

    def clear_history(self):
        self.history = []
        self.memory.clear()
