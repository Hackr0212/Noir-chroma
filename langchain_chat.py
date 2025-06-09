from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import AIMessage, HumanMessage
from rag_memory import RAGMemory



class LangChainChat:
    def __init__(self):
        self.llm = ChatDeepSeek(
            model="deepseek-chat",
            temperature=1.1,  # Higher creativity, funnier and more chaotic
            top_p=0.9,  # Allows some controlled randomness
            frequency_penalty=0.3,  # Prevents too much repetition of phrases like "glub glub"
            presence_penalty=0.6,  # Encourages introducing new ideas (puns, excuses, gaslighting)
            max_tokens=500,
            streaming=True,
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
        self.memory = RAGMemory()
        self.chain = self.prompt_template | self.llm
        self.history = []  # Stores conversation history

    def stream_response(self, user_input: str):
        try:
            # Recall past *user* inputs only
            relevant_user_memories = self.memory.query(user_input, top_k=3, role="user")
            relevant_ai_memories = self.memory.query(user_input, top_k=2, role="ai")

            memory_context = "\n".join(relevant_user_memories + relevant_ai_memories)
            enhanced_input = f"{memory_context}\n\nCurrent message: {user_input}" if memory_context else user_input

            self.history.append(HumanMessage(content=user_input))

            chunks = []
            for chunk in self.chain.stream({"input": enhanced_input, "history": self.history}):
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                if content:
                    chunks.append(content)
                    yield content

            full_response = ''.join(chunks)
            if full_response:
                self.history.append(AIMessage(content=full_response))
                self.memory.add_message(user_input, role="user")
                self.memory.add_message(full_response, role="ai")

        except Exception as e:
            yield f"Error generating response: {e}"

    def clear_history(self):
        self.history = []
        self.memory.clear()
