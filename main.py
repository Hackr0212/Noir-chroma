import gradio as gr
from langchain_chat import LangChainChat
from deepseek_client import DeepSeekClient
import threading
import time

# Initialize chat once
chat = LangChainChat()
deepseek = DeepSeekClient()

# Cache welcome message
WELCOME_MESSAGE = [
    {
        "role": "system",
        "content": "Welcome to Noir-chroma! Type your message below to start..."
    }
]

def get_response(message: str) -> list[dict]:
    """Get response from the AI with optimized memory usage"""
    try:
        # Get response from LangChain
        response = chat.get_response(message)
        return [
            {
                "role": "user",
                "content": message
            },
            {
                "role": "assistant",
                "content": response
            }
        ]
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")
        return [
            {
                "role": "user",
                "content": message
            },
            {
                "role": "assistant",
                "content": error_msg
            }
        ]

# Create Gradio interface with optimized settings
def create_interface():
    with gr.Blocks(theme=gr.themes.Default()) as demo:
        gr.Markdown("# Noir-chroma: AI Assistant")
        
        with gr.Row():
            chatbot = gr.Chatbot(
                value=WELCOME_MESSAGE,
                height=400,
                type="messages"  # Use proper message format
            )
            
        with gr.Row():
            message = gr.Textbox(
                placeholder="Type your message here...",
                container=False,
                scale=7
            )
            submit_btn = gr.Button("Send", variant="primary")
            
        # Optimize event handlers
        message.submit(get_response, inputs=[message], outputs=[chatbot])
        submit_btn.click(get_response, inputs=[message], outputs=[chatbot])
    
    return demo

if __name__ == '__main__':
    # Create and launch interface
    demo = create_interface()
    demo.launch(share=False)
