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
from elevenlabs_tts import create_tts_client
import threading
import time

# Initialize chat and TTS
chat = LangChainChat()
deepseek = DeepSeekClient()
tts_client = create_tts_client()

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
        
        # Generate speech if TTS is available
        if tts_client and response:
            # Extract just the dialogue part for TTS (remove formatting)
            dialogue_text = extract_dialogue_for_tts(response)
            if dialogue_text:
                # Generate speech in background thread to avoid blocking UI
                threading.Thread(
                    target=lambda: tts_client.speak(dialogue_text, voice_name="Rachel"),
                    daemon=True
                ).start()
        
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

def extract_dialogue_for_tts(response: str) -> str:
    """Extract clean dialogue text for TTS from Noir's formatted response"""
    try:
        lines = response.split('\n')
        dialogue_parts = []
        
        for line in lines:
            line = line.strip()
            # Look for dialogue lines (🗣️ format)
            if line.startswith('🗣️'):
                # Remove emoji and quotes, clean up the text
                dialogue = line.replace('🗣️', '').strip()
                if dialogue.startswith("'") and dialogue.endswith("'"):
                    dialogue = dialogue[1:-1]  # Remove quotes
                elif dialogue.startswith('"') and dialogue.endswith('"'):
                    dialogue = dialogue[1:-1]  # Remove quotes
                
                # Clean up some common patterns for better TTS
                dialogue = dialogue.replace('glub glub', 'glub glub')  # Keep character sounds
                dialogue = dialogue.replace('🐬', 'dolphin')
                dialogue = dialogue.replace('🦈', 'shark')
                dialogue = dialogue.replace('✨', '')
                dialogue = dialogue.replace('💧', '')
                
                if dialogue:
                    dialogue_parts.append(dialogue)
        
        return ' '.join(dialogue_parts) if dialogue_parts else response
        
    except Exception as e:
        print(f"❌ Error extracting dialogue: {e}")
        return response

# Create Gradio interface with optimized settings
def create_interface():
    with gr.Blocks(theme=gr.themes.Default()) as demo:
        gr.Markdown("# Noir-chroma: AI Assistant with Voice")
        
        # Add TTS status indicator
        tts_status = "🔊 ElevenLabs TTS Enabled" if tts_client else "🔇 TTS Disabled (No API Key)"
        gr.Markdown(f"**Status:** {tts_status}")
        
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
        
        # Add TTS controls
        with gr.Row():
            if tts_client:
                with gr.Column():
                    gr.Markdown("### 🎵 Voice Settings")
                    voice_dropdown = gr.Dropdown(
                        choices=list(tts_client.get_voices().keys()) if tts_client else [],
                        value="Rachel",
                        label="Voice",
                        interactive=True
                    )
                    
                    test_tts_btn = gr.Button("🧪 Test Voice", size="sm")
                    
                    def test_voice(voice_name):
                        if tts_client:
                            test_text = "Hello! I am Noir, totally real dolphin! Glub glub!"
                            success = tts_client.speak(test_text, voice_name=voice_name)
                            return f"✅ Voice test completed!" if success else "❌ Voice test failed"
                        return "❌ TTS not available"
                    
                    test_tts_btn.click(test_voice, inputs=[voice_dropdown], outputs=[])
            
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
    # Test TTS on startup
    if tts_client:
        print("🎵 ElevenLabs TTS initialized successfully!")
        # Uncomment to test on startup:
        # tts_client.speak("Noir-chroma is ready! Glub glub!", voice_name="Rachel")
    else:
        print("⚠️ TTS not available. Set ELEVENLABS_API_KEY to enable voice features.")
    
    # Create and launch interface
    demo = create_interface()
    demo.launch(share=False)