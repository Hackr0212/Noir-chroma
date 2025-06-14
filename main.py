import sys
import threading
import time
from speech_recognizer import SpeechRecognizer
from text_to_speech import TextToSpeech
from deepseek_client import DeepSeekClient
import config

# Import Live2D integration
try:
    from live2d_integration import (
        initialize_live2d_avatar,
        start_live2d_display,
        handle_ai_response,
        sync_avatar_speech,
        is_avatar_running,
        shutdown_avatar,
        get_avatar_status,
        set_avatar_emotion,
        update_avatar_mouse_tracking
    )

    LIVE2D_AVAILABLE = True
    print("✅ Live2D integration loaded successfully")
except ImportError as e:
    print(f"⚠️ Live2D integration not available: {e}")
    LIVE2D_AVAILABLE = False


class VTuberChatApp:
    def __init__(self):
        self.running = True
        self.speech_recognizer = None
        self.text_to_speech = None
        self.deepseek_client = None
        self.avatar_initialized = False
        self.avatar_display_started = False
        self.voice_listening = False
        self.voice_thread = None

    def initialize_components(self):
        """Initialize all components"""
        try:
            print("Initializing components...")
            
            # Initialize speech recognition
            self.speech_recognizer = SpeechRecognizer()
            print("✅ Speech recognition initialized")
            
            # Initialize text-to-speech
            self.text_to_speech = TextToSpeech()
            print("✅ Text-to-speech initialized")
            
            # Initialize DeepSeek client
            self.deepseek_client = DeepSeekClient()
            print("✅ DeepSeek client initialized")
            
            return True
        except Exception as e:
            print(f"❌ Error initializing components: {e}")
            return False

    def start(self):
        """Start the application"""
        if not self.initialize_components():
            print("❌ Failed to initialize components")
            return

        print("\n=== VTuber Chat Application ===")
        print("Type 'exit' to quit")
        print("Type 'voice' to start voice input")
        print("Type 'text' to enter text input")
        print("==============================\n")

        while self.running:
            try:
                command = input("Enter command: ").strip().lower()
                
                if command == 'exit':
                    self.running = False
                elif command == 'voice':
                    self.start_voice_listening()
                elif command == 'text':
                    text = input("Enter your message: ")
                    if text:
                        self.process_user_input(text)
                else:
                    print("Unknown command. Available commands: exit, voice, text")
            
            except KeyboardInterrupt:
                print("\nShutting down...")
                self.running = False
            except Exception as e:
                print(f"Error: {e}")

        self.cleanup()

    def start_voice_listening(self):
        """Start voice input mode"""
        if self.voice_listening:
            print("Voice input is already active")
            return

        print("\n🎤 Voice input mode activated")
        print("Speak now (or press Enter to type instead)")
        
        try:
            text = self.speech_recognizer.listen_with_voice_detection()
            if text:
                self.process_user_input(text)
            else:
                print("No speech detected")
        except Exception as e:
            print(f"Error in voice input: {e}")

    def process_user_input(self, user_input: str):
        """Process user input and generate response"""
        try:
            print("\n🤖 Processing your input...")
            
            # Get AI response
            response = self.deepseek_client.get_response(user_input)
            if not response:
                print("❌ Failed to get AI response")
                return

            print(f"\nAI: {response}")
            
            # Convert response to speech
            if self.text_to_speech:
                self.text_to_speech.speak_async(response)

        except Exception as e:
            print(f"Error processing input: {e}")

    def cleanup(self):
        """Clean up resources"""
        print("\nCleaning up...")
        
        if self.text_to_speech:
            self.text_to_speech.stop_audio()
        
        if LIVE2D_AVAILABLE and self.avatar_display_started:
            shutdown_avatar()
        
        print("✅ Cleanup complete")


if __name__ == "__main__":
    app = VTuberChatApp()
    app.start()

