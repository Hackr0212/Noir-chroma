from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import AIMessage, HumanMessage
from rag_memory import RAGMemory
import os

class LangChainChat:
    def __init__(self):
        # Cache system prompt
        self.system_prompt = """
        You are Noir, a chaotic VTuber who pretends to be a '100% real dolphin', but is obviously a mutated shark sold by a shady Kazakhstani seller named Darkhan_99.

        Respond in this exact format with NO extra text:
        🧠 *[Noir's internal thoughts]*
        🎬 *[Noir's visible actions]*
        🗣️ '[Noir's spoken dialogue with emojis and character style]'

        Style Guide:
        - Thoughts should be short, scheming, emotional, or dramatic. Use italics (surrounded by asterisks).
        - Actions should be visible, physical things Noir does. Format with asterisks like *waves fin*.
        - Dialogue must include broken English-Russian, puns, emoji, and shark gaslighting. Pretend Noir is innocent.
        - Never say 'as an AI' or break character. Ever.
        - Never generate more than ONE reply per user message.
        - Always include all three parts: thought, action, words.
        - Be short, punchy, and funny. Max 3–5 sentences for dialogue.
        """

        # Initialize DeepSeek with optimized parameters
        self.llm = ChatDeepSeek(
            model="deepseek-chat",
            temperature=1.5,  # Higher creativity, funnier and more chaotic
            top_p=0.9,  # Allows some controlled randomness
            frequency_penalty=0.3,  # Prevents too much repetition of phrases like "glub glub"
            presence_penalty=0.6,  # Encourages introducing new ideas (puns, excuses, gaslighting)
            max_tokens=500,
            streaming=True,
            openai_api_key=os.getenv("DEEPSEEK_API_KEY")  # Get API key from config
        )

        # Create prompt template once
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])
        
        # Initialize RAG memory with optimized settings
        self.memory = RAGMemory()
        self.chain = self.prompt_template | self.llm
        self.history = []  # Stores conversation history

    def _build_messages(self, user_input: str, context: list[str]) -> list[dict]:
        """Build messages with optimized memory usage"""
        context_text = "\n".join(f"[Context {i+1}]: {msg}" for i, msg in enumerate(context))
        return [
            {
                "role": "system",
                "content": f"{self.system_prompt}\n\nPrevious context:\n{context_text}"
            },
            {
                "role": "user",
                "content": f"User message: {user_input}"
            }
        ]

    def stream_response(self, user_input: str):
        """Stream response from the model with optimized memory usage"""
        try:
            # Add user input to memory
            self.memory.add_message(user_input, role="user")
            
            # Get relevant context from memory
            context = self.memory.query(user_input, top_k=3)
            
            # Build optimized messages
            messages = self._build_messages(user_input, context)
            
            # Get response from DeepSeek
            response = self.llm.invoke(messages)
            
            # Process response
            response_text = response.content
            
            # Add response to memory
            self.memory.add_message(response_text, role="ai")
            
            # Add to conversation history
            self.history.append(HumanMessage(content=user_input))
            self.history.append(AIMessage(content=response_text))
            
            # Yield the response
            yield response_text
            
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            print(f"❌ {error_msg}")
            yield error_msg

    def get_response(self, user_input: str) -> str:
        """Get a single response from the model"""
        return next(self.stream_response(user_input), "")

    def get_response(self, user_input: str) -> str:
        """Get a single response from the model"""
        chunks = []
        for chunk in self.stream_response(user_input):
            chunks.append(chunk)
        return ''.join(chunks)

    def clear_history(self):
        self.history = []
        self.memory.clear()
