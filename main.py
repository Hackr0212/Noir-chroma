import groq
import gradio as gr
import soundfile as sf
from dataclasses import dataclass, field
import os

# Initialize Groq client securely
api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    raise ValueError("Please set the GROQ_API_KEY environment variable.")
client = groq.Client(api_key=api_key)
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
            # Add audio input with automatic voice detection (VAD)
            audio_input = gr.Audio(
                sources=["microphone"],
                type="filepath",
                label="🎤 Speak to Noir (click to record, auto-transcribe)",
                streaming=False,
                show_label=True
            )
        with gr.Row():
            message = gr.Textbox(
                placeholder="Type your message here...",
                container=False,
                scale=7
            )
            submit_btn = gr.Button("Send", variant="primary")
            
        # Handler for audio input
        def handle_audio(audio_file):
            if audio_file is None:
                return gr.update()
            try:
                # Use Gradio's built-in Whisper API for transcription
                result = gr.Audio.transcribe(audio_file)
                transcript = result["text"]
                chat_result = get_response(transcript)
                return chat_result
            except Exception as e:
                return [{"role": "system", "content": f"Audio error: {e}"}]

        # Optimize event handlers
        message.submit(get_response, inputs=[message], outputs=[chatbot])
        submit_btn.click(get_response, inputs=[message], outputs=[chatbot])
        audio_input.stop_recording(handle_audio, inputs=[audio_input], outputs=[chatbot])
    
    return demo

if __name__ == '__main__':
    # Create and launch interface
    demo = create_interface()
    demo.launch(share=False)
