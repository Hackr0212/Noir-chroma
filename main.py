import sys
from speech_recognizer import SpeechRecognizer
from text_to_speech import TextToSpeech
from deepseek_client import DeepSeekClient
import config


def main():
    print("=== Noir VTuber Chat Assistant ===")
    print("Special commands:")
    print("  //exit - Exit the program")
    print("  //voice - Toggle voice input detection")
    print("  //speak - Toggle text-to-speech for AI responses")
    print("  //test-mic - Test microphone")
    print("  //test-tts - Test text-to-speech")
    print("  //test-pygame - Test pygame audio system")
    print("  //volume <0-100> - Set TTS volume (e.g., //volume 75)")
    print("  //pause - Pause current audio")
    print("  //resume - Resume paused audio")
    print("  //stop - Stop current audio")
    print("  //clear - Clear conversation history")
    print("  //help - Show this help again")
    print("\nStart chatting! (Text input is default)")

    # Initialize components
    try:
        recognizer = SpeechRecognizer()
        tts = TextToSpeech()
        ai_client = DeepSeekClient()

        # Settings
        voice_input_enabled = False  # Voice input disabled by default
        tts_enabled = False  # TTS disabled by default

        print("All components initialized successfully!")
        print(f"Voice Input: {'Enabled' if voice_input_enabled else 'Disabled'}")
        print(f"Text-to-Speech: {'Enabled' if tts_enabled else 'Disabled'}")
    except Exception as e:
        print(f"Error initializing components: {e}")
        return

    # Main conversation loop
    while True:
        print("\n" + "=" * 50)
        voice_input_enabled, tts_enabled = handle_input_and_commands(recognizer, tts, ai_client, voice_input_enabled,
                                                                     tts_enabled)


def handle_input_and_commands(recognizer, tts, ai_client, voice_input_enabled, tts_enabled):
    """Handle input and process special commands"""
    user_input = None

    if voice_input_enabled:
        print("\nReady to chat! Start speaking or type your message:")
        # Check for voice activity and get input
        user_input = recognizer.listen_with_voice_detection()

    if not user_input:
        print("Type your message (or use //command):")
        user_input = input("> ").strip()

    if not user_input:
        print("No input received.")
        return voice_input_enabled, tts_enabled

    # Check for special commands
    if user_input.startswith("//"):
        return handle_command(user_input, recognizer, tts, ai_client, voice_input_enabled, tts_enabled)
    else:
        # Regular chat input
        process_user_input(user_input, tts, ai_client, tts_enabled)
        return voice_input_enabled, tts_enabled


def handle_command(command, recognizer, tts, ai_client, voice_input_enabled, tts_enabled):
    """Handle special commands"""
    cmd = command.lower().strip()

    if cmd == "//exit":
        print("Goodbye!")
        sys.exit(0)

    elif cmd == "//voice":
        voice_input_enabled = not voice_input_enabled
        status = "enabled" if voice_input_enabled else "disabled"
        print(f"Voice input {status}!")
        return voice_input_enabled, tts_enabled

    elif cmd == "//speak":
        tts_enabled = not tts_enabled
        status = "enabled" if tts_enabled else "disabled"
        print(f"Text-to-speech {status}!")
        return voice_input_enabled, tts_enabled

    elif cmd == "//test-mic":
        test_microphone(recognizer)

    elif cmd == "//test-tts":
        test_tts(tts)

    elif cmd == "//test-pygame":
        test_pygame(tts)

    elif cmd.startswith("//volume "):
        try:
            volume_str = cmd.split(" ", 1)[1]
            volume = int(volume_str)
            if 0 <= volume <= 100:
                tts.set_volume(volume / 100.0)
            else:
                print("Volume must be between 0 and 100")
        except (IndexError, ValueError):
            print("Usage: //volume <0-100> (e.g., //volume 75)")

    elif cmd == "//pause":
        tts.pause_audio()

    elif cmd == "//resume":
        tts.unpause_audio()

    elif cmd == "//stop":
        tts.stop_audio()

    elif cmd == "//clear":
        ai_client.clear_conversation()
        print("Conversation history cleared!")

    elif cmd == "//help":
        show_help()

    else:
        print(f"Unknown command: {command}")
        print("Type //help to see available commands")

    return voice_input_enabled, tts_enabled


def show_help():
    """Show available commands"""
    print("\nAvailable commands:")
    print("  //exit - Exit the program")
    print("  //voice - Toggle voice input detection")
    print("  //speak - Toggle text-to-speech for AI responses")
    print("  //test-mic - Test microphone")
    print("  //test-tts - Test text-to-speech")
    print("  //test-pygame - Test pygame audio system")
    print("  //volume <0-100> - Set TTS volume")
    print("  //pause - Pause current audio")
    print("  //resume - Resume paused audio")
    print("  //stop - Stop current audio")
    print("  //clear - Clear conversation history")
    print("  //help - Show this help")


def process_user_input(user_input, tts, ai_client, tts_enabled):
    """Process user input and get AI response"""
    print(f"\nUser: {user_input}")
    print("\nNoir is responding...")

    full_response = ""
    messages = [{"role": "user", "content": user_input}]

    try:
        # Stream AI response
        for chunk in ai_client.get_chat_response(messages):
            print(chunk, end='', flush=True)
            full_response += chunk

        print()  # New line after response

        # Convert AI response to speech only if TTS is enabled
        if tts_enabled and full_response.strip():
            print("🔊 Speaking response...")
            tts.speak(full_response)
        elif not full_response.strip():
            print("No response generated.")

    except Exception as e:
        error_msg = f"Error getting AI response: {e}"
        print(error_msg)
        if tts_enabled:
            tts.speak("Sorry, I encountered an error. Please try again.")


def test_microphone(recognizer):
    """Test microphone functionality"""
    print("\nTesting microphone...")
    if recognizer.test_microphone():
        print("Microphone is working! Say something:")
        result = recognizer.listen(timeout=5)
        if result:
            print(f"Successfully captured: {result}")
        else:
            print("No speech detected during test.")
    else:
        print("Microphone test failed. Please check your audio setup.")


def test_tts(tts):
    """Test text-to-speech functionality"""
    print("\nTesting text-to-speech...")
    tts.test_speech()


def test_pygame(tts):
    """Test pygame audio system"""
    print("\nTesting pygame audio system...")
    tts.test_pygame()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)