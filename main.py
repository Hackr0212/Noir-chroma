import pygame_gui
import pygame
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
        # Initialize pygame
        pygame.init()

        # Screen dimensions
        self.WIDTH, self.HEIGHT = 1400, 900
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("Noir VTuber Chat Assistant")

        # UI Manager
        self.manager = pygame_gui.UIManager((self.WIDTH, self.HEIGHT))

        # Colors
        self.BG_COLOR = (30, 30, 40)
        self.CHAT_BG = (20, 20, 30)
        self.INPUT_BG = (40, 40, 50)

        # Initialize all instance variables FIRST
        self.conversation_history = []
        self.chat_messages = []  # For AI chat history in proper format
        self.last_mouse_pos = (0, 0)
        self.last_avatar_status = {}

        # Avatar initialization state
        self.avatar_initializing = False
        self.avatar_init_thread = None

        # Settings
        self.voice_input_enabled = False
        self.tts_enabled = False
        self.avatar_enabled = False
        self.avatar_display_running = False

        # Voice recognition thread
        self.listening_thread = None
        self.stop_listening = False
        self.is_listening = False

        # Create UI elements (now safe to call update_status_indicators)
        self.create_ui()

        # Initialize components
        self.initialize_components()

        # Status indicators
        self.update_status_indicators()

        # Welcome message
        self.add_message("System", "🎭 Noir VTuber Chat Assistant initialized!")
        self.add_message("System", "💡 Commands: //voice, //speak, //avatar, //clear, //volume [0-100], //exit")

        if LIVE2D_AVAILABLE:
            self.add_message("System", "🎨 Live2D avatar support available! Click 'Avatar: OFF' to enable.")

    def initialize_components(self):
        """Initialize core components with error handling"""
        try:
            self.recognizer = SpeechRecognizer()
            self.add_message("System", "🎤 Speech recognizer initialized")
        except Exception as e:
            self.add_message("System", f"❌ Speech recognizer error: {e}", is_error=True)
            self.recognizer = None

        try:
            self.tts = TextToSpeech()
            self.add_message("System", "🔊 Text-to-speech initialized")
        except Exception as e:
            self.add_message("System", f"❌ TTS error: {e}", is_error=True)
            self.tts = None

        try:
            self.ai_client = DeepSeekClient()
            self.add_message("System", "🤖 AI client initialized")
        except Exception as e:
            self.add_message("System", f"❌ AI client error: {e}", is_error=True)
            self.ai_client = None

    def create_ui(self):
        """Create all UI elements"""
        # Chat history panel (larger)
        self.chat_history = pygame_gui.elements.UITextBox(
            "",
            relative_rect=pygame.Rect(20, 20, 860, 650),
            manager=self.manager
        )
        self.chat_history.set_active_effect(pygame_gui.TEXT_EFFECT_TYPING_APPEAR)

        # Input text box
        self.input_box = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(20, 690, 700, 40),
            manager=self.manager
        )
        self.input_box.set_text_length_limit(500)

        # Send button
        self.send_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(730, 690, 150, 40),
            text="Send Message",
            manager=self.manager
        )

        # Control buttons
        button_width = 180
        button_height = 35
        button_y = 750

        # First row of buttons
        self.voice_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(20, button_y, button_width, button_height),
            text="Voice Input: OFF",
            manager=self.manager
        )

        self.tts_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(210, button_y, button_width, button_height),
            text="TTS: OFF",
            manager=self.manager
        )

        self.avatar_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(400, button_y, button_width, button_height),
            text="Avatar: OFF",
            manager=self.manager
        )

        self.emotion_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(590, button_y, button_width, button_height),
            text="Test Emotion",
            manager=self.manager
        )

        # Second row of buttons
        button_y += 45

        self.clear_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(20, button_y, button_width, button_height),
            text="Clear History",
            manager=self.manager
        )

        self.volume_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(210, button_y, button_width, button_height),
            text="Volume: 75%",
            manager=self.manager
        )

        self.avatar_window_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(400, button_y, button_width, button_height),
            text="Show Avatar Window",
            manager=self.manager
        )

        self.exit_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(590, button_y, button_width, button_height),
            text="Exit Application",
            manager=self.manager
        )

        # Status and control panel (larger)
        self.status_panel = pygame_gui.elements.UITextBox(
            "Status: Initializing...",
            relative_rect=pygame.Rect(900, 20, 480, 820),
            manager=self.manager
        )

        # Voice activity indicator
        self.voice_indicator = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(735, 695, 15, 15),
            manager=self.manager
        )
        self.voice_indicator.background_colour = pygame.Color(200, 50, 50)

    def add_message(self, sender, message, is_error=False):
        """Add a message to the chat history"""
        timestamp = time.strftime("%H:%M:%S")

        # Format message with color coding
        if is_error:
            color = "#FF5555"
        elif sender == "AI":
            color = "#55AAFF"
        elif sender == "You":
            color = "#55FF55"
        else:  # System
            color = "#FFAA55"

        formatted_msg = f'<font color="#888888">[{timestamp}]</font> <font color="{color}"><b>{sender}:</b></font> {message}'

        # Add to conversation history
        self.conversation_history.append(formatted_msg)

        # Update chat display (show last 30 messages)
        display_text = "<br>".join(self.conversation_history[-30:])
        self.chat_history.set_text(display_text)

    def update_status_indicators(self):
        """Update status indicators and button texts"""
        # Update button texts
        self.voice_btn.set_text(f"Voice Input: {'ON' if self.voice_input_enabled else 'OFF'}")
        self.tts_btn.set_text(f"TTS: {'ON' if self.tts_enabled else 'OFF'}")

        avatar_status = "INIT" if self.avatar_initializing else ("ON" if self.avatar_enabled else "OFF")
        self.avatar_btn.set_text(f"Avatar: {avatar_status}")

        self.avatar_window_btn.set_text("Hide Avatar" if self.avatar_display_running else "Show Avatar Window")

        # Build comprehensive status text
        status_lines = [
            "<b>🎭 NOIR VTUBER STATUS</b>",
            "<br>",
            "<b>Core Components:</b>",
            f"🎤 Voice Input: {'<font color=#55FF55>ENABLED</font>' if self.voice_input_enabled else '<font color=#FF5555>DISABLED</font>'}",
            f"🔊 Text-to-Speech: {'<font color=#55FF55>ENABLED</font>' if self.tts_enabled else '<font color=#FF5555>DISABLED</font>'}",
            f"🤖 AI Client: {'<font color=#55FF55>READY</font>' if hasattr(self, 'ai_client') and self.ai_client else '<font color=#FF5555>ERROR</font>'}",
            "<br>",
            "<b>Avatar System:</b>"
        ]

        if LIVE2D_AVAILABLE:
            if self.avatar_initializing:
                status_lines.append("🎨 Avatar: <font color=#FFAA55>INITIALIZING...</font>")
            elif self.avatar_enabled:
                avatar_running = is_avatar_running()
                status_lines.append(
                    f"🎨 Avatar: {'<font color=#55FF55>RUNNING</font>' if avatar_running else '<font color=#FFAA55>ENABLED</font>'}")
                status_lines.append(
                    f"🖥️ Display: {'<font color=#55FF55>ACTIVE</font>' if self.avatar_display_running else '<font color=#FF5555>INACTIVE</font>'}")

                # Get detailed avatar status
                if hasattr(self, 'last_avatar_status') and self.last_avatar_status:
                    avatar_info = self.last_avatar_status
                    status_lines.extend([
                        f"📁 Model: {'<font color=#55FF55>LOADED</font>' if avatar_info.get('initialized') else '<font color=#FF5555>ERROR</font>'}",
                        f"🧵 Thread: {'<font color=#55FF55>ALIVE</font>' if avatar_info.get('thread_alive') else '<font color=#FF5555>DEAD</font>'}"
                    ])
            else:
                status_lines.append("🎨 Avatar: <font color=#FF5555>DISABLED</font>")

            # Model path info
            try:
                model_path = getattr(config, 'LIVE2D_MODEL_PATH', 'models/noir_model')
                status_lines.append(f"📂 Model Path: {model_path}")
            except:
                status_lines.append("📂 Model Path: <font color=#FF5555>NOT SET</font>")
        else:
            status_lines.append("🎨 Live2D: <font color=#FF5555>NOT AVAILABLE</font>")

        # Performance info
        status_lines.extend([
            "<br>",
            "<b>Performance:</b>",
            f"💬 Messages: {len(self.conversation_history)}",
            f"🔄 Chat History: {len(self.chat_messages)}",
            f"🔄 Listening: {'<font color=#55FF55>ACTIVE</font>' if self.is_listening else '<font color=#FF5555>INACTIVE</font>'}",
            f"🖱️ Mouse: {self.last_mouse_pos[0]}, {self.last_mouse_pos[1]}"
        ])

        # Commands help
        status_lines.extend([
            "<br>",
            "<b>💡 Available Commands:</b>",
            "//voice - Toggle voice input",
            "//speak - Toggle text-to-speech",
            "//avatar - Toggle avatar system",
            "//clear - Clear chat history",
            "//volume [0-100] - Set TTS volume",
            "//emotion [happy/sad/angry] - Test avatar emotion",
            "//exit - Exit application"
        ])

        self.status_panel.set_text("<br>".join(status_lines))

    def initialize_avatar_async(self):
        """Initialize avatar in a separate thread"""
        if not LIVE2D_AVAILABLE:
            self.add_message("System", "❌ Live2D not available", is_error=True)
            return

        if self.avatar_initializing:
            self.add_message("System", "⚠️ Avatar already initializing", is_error=True)
            return

        self.avatar_initializing = True
        self.update_status_indicators()

        def init_thread():
            try:
                self.add_message("System", "🎭 Initializing Live2D avatar...")

                # Initialize avatar with window size
                success = initialize_live2d_avatar(window_size=(800, 600))

                if success:
                    self.add_message("System", "✅ Live2D avatar initialized successfully!")
                    self.avatar_enabled = True
                else:
                    self.add_message("System", "❌ Failed to initialize Live2D avatar", is_error=True)
                    self.avatar_enabled = False

            except Exception as e:
                self.add_message("System", f"❌ Avatar initialization error: {e}", is_error=True)
                self.avatar_enabled = False
            finally:
                self.avatar_initializing = False
                self.update_status_indicators()

        self.avatar_init_thread = threading.Thread(target=init_thread, daemon=True)
        self.avatar_init_thread.start()

    def start_avatar_display_async(self):
        """Start avatar display window in separate thread"""
        if not self.avatar_enabled:
            self.add_message("System", "❌ Avatar not initialized", is_error=True)
            return

        if self.avatar_display_running:
            self.add_message("System", "⚠️ Avatar display already running")
            return

        def display_thread():
            try:
                self.add_message("System", "🖥️ Starting avatar display window...")
                success = start_live2d_display()

                if success:
                    self.avatar_display_running = True
                    self.add_message("System", "✅ Avatar display started!")
                    self.update_status_indicators()

                    # Monitor avatar status
                    while self.avatar_display_running and is_avatar_running():
                        self.last_avatar_status = get_avatar_status()
                        time.sleep(1.0)

                    self.avatar_display_running = False
                    self.add_message("System", "🖥️ Avatar display stopped")
                    self.update_status_indicators()
                else:
                    self.add_message("System", "❌ Failed to start avatar display", is_error=True)

            except Exception as e:
                self.add_message("System", f"❌ Avatar display error: {e}", is_error=True)
                self.avatar_display_running = False
                self.update_status_indicators()

        threading.Thread(target=display_thread, daemon=True).start()

    def handle_mouse_motion(self, pos):
        """Handle mouse motion for avatar eye tracking"""
        self.last_mouse_pos = pos
        if self.avatar_enabled and LIVE2D_AVAILABLE:
            try:
                update_avatar_mouse_tracking(pos[0], pos[1])
            except:
                pass  # Ignore errors to prevent spam

    def start_voice_listening(self):
        """Start voice listening in a separate thread"""
        if self.is_listening:
            return

        if not hasattr(self, 'recognizer') or not self.recognizer:
            self.add_message("System", "❌ Speech recognizer not available", is_error=True)
            return

        self.is_listening = True
        self.stop_listening = False

        def voice_loop():
            while not self.stop_listening:
                if self.voice_input_enabled:
                    try:
                        self.voice_indicator.background_colour = pygame.Color(50, 200, 50)
                        text = self.recognizer.listen_with_voice_detection()
                        self.voice_indicator.background_colour = pygame.Color(200, 50, 50)

                        if text and not self.stop_listening:
                            # Add to chat and process
                            self.add_message("You", text)
                            self.process_user_input(text)
                    except Exception as e:
                        self.add_message("System", f"Voice recognition error: {e}", is_error=True)
                        time.sleep(1.0)
                else:
                    time.sleep(0.1)
            self.is_listening = False

        self.listening_thread = threading.Thread(target=voice_loop, daemon=True)
        self.listening_thread.start()

    def process_user_input(self, user_input):
        """Process user input and get AI response"""
        if not hasattr(self, 'ai_client') or not self.ai_client:
            self.add_message("System", "❌ AI client not available", is_error=True)
            return

        try:
            self.add_message("System", "🤖 Processing...")

            # Add user message to chat history
            self.chat_messages.append({"role": "user", "content": user_input})

            # Keep only the last 20 messages to avoid token limits
            if len(self.chat_messages) > 20:
                self.chat_messages = self.chat_messages[-20:]

            # Get streaming response from AI
            full_response = ""
            for chunk in self.ai_client.get_chat_response(self.chat_messages, stream=True):
                full_response += chunk

            if full_response.strip():
                # Add AI response to chat history
                self.chat_messages.append({"role": "assistant", "content": full_response})

                # Display the response
                self.add_message("AI", full_response)

                # Text-to-speech
                if self.tts_enabled and hasattr(self, 'tts') and self.tts:
                    try:
                        # Extract just the dialogue part for TTS (the part after 🗣️)
                        tts_text = full_response
                        if "🗣️" in full_response:
                            # Find the dialogue part and clean it up
                            dialogue_start = full_response.find("🗣️")
                            if dialogue_start != -1:
                                dialogue_part = full_response[dialogue_start + 2:].strip()
                                # Remove quotes and extra formatting
                                dialogue_part = dialogue_part.strip("'\"")
                                if dialogue_part:
                                    tts_text = dialogue_part

                        self.tts.speak(tts_text)

                        # Sync avatar speech if enabled
                        if self.avatar_enabled and LIVE2D_AVAILABLE:
                            sync_avatar_speech(tts_text)
                    except Exception as e:
                        self.add_message("System", f"TTS error: {e}", is_error=True)

                # Update avatar with response
                if self.avatar_enabled and LIVE2D_AVAILABLE:
                    try:
                        handle_ai_response(full_response)
                    except Exception as e:
                        self.add_message("System", f"Avatar response error: {e}", is_error=True)
            else:
                self.add_message("System", "❌ Empty response from AI", is_error=True)

        except Exception as e:
            self.add_message("System", f"AI processing error: {e}", is_error=True)

    def handle_command(self, command):
        """Handle special commands"""
        cmd = command.lower().strip()
        parts = cmd.split()

        if cmd == "//exit":
            self.running = False

        elif cmd == "//voice":
            if hasattr(self, 'recognizer') and self.recognizer:
                self.voice_input_enabled = not self.voice_input_enabled
                if self.voice_input_enabled:
                    self.start_voice_listening()
                else:
                    self.stop_listening = True
                self.update_status_indicators()
            else:
                self.add_message("System", "❌ Voice input not available", is_error=True)

        elif cmd == "//speak":
            if hasattr(self, 'tts') and self.tts:
                self.tts_enabled = not self.tts_enabled
                self.update_status_indicators()
            else:
                self.add_message("System", "❌ TTS not available", is_error=True)

        elif cmd == "//avatar":
            if LIVE2D_AVAILABLE:
                if not self.avatar_enabled and not self.avatar_initializing:
                    self.initialize_avatar_async()
                elif self.avatar_enabled:
                    self.avatar_enabled = False
                    shutdown_avatar()
                    self.avatar_display_running = False
                    self.add_message("System", "🎭 Avatar disabled")
                    self.update_status_indicators()
            else:
                self.add_message("System", "❌ Live2D integration not available", is_error=True)

        elif cmd == "//clear":
            self.conversation_history = []
            self.chat_messages = []  # Clear AI chat history too
            self.chat_history.set_text("")
            # Clear the AI client's conversation history
            if hasattr(self, 'ai_client') and self.ai_client:
                self.ai_client.clear_conversation()
            self.add_message("System", "🗑️ Chat history cleared")

        elif cmd.startswith("//volume"):
            if hasattr(self, 'tts') and self.tts and len(parts) == 2:
                try:
                    vol = int(parts[1])
                    if 0 <= vol <= 100:
                        self.tts.set_volume(vol)
                        self.volume_btn.set_text(f"Volume: {vol}%")
                        self.add_message("System", f"🔊 Volume set to {vol}%")
                    else:
                        self.add_message("System", "❌ Volume must be 0-100", is_error=True)
                except ValueError:
                    self.add_message("System", "❌ Invalid volume value", is_error=True)
            else:
                self.add_message("System", "❌ Usage: //volume [0-100]", is_error=True)

        elif cmd.startswith("//emotion"):
            if LIVE2D_AVAILABLE and self.avatar_enabled and len(parts) == 2:
                emotion = parts[1]
                try:
                    set_avatar_emotion(emotion, 1.0)
                    self.add_message("System", f"😊 Avatar emotion set to: {emotion}")
                except Exception as e:
                    self.add_message("System", f"❌ Emotion error: {e}", is_error=True)
            else:
                self.add_message("System", "❌ Avatar not available or invalid emotion", is_error=True)

        else:
            self.add_message("System", f"❌ Unknown command: {cmd}", is_error=True)

    def run(self):
        """Main application loop"""
        clock = pygame.time.Clock()
        self.running = True

        # Start voice listening if enabled
        if self.voice_input_enabled:
            self.start_voice_listening()

        self.add_message("System", "🚀 Application ready! Type a message or use //commands")

        while self.running:
            time_delta = clock.tick(60) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                elif event.type == pygame.MOUSEMOTION:
                    self.handle_mouse_motion(event.pos)

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN and self.input_box.is_focused:
                        text = self.input_box.get_text().strip()
                        if text:
                            self.input_box.set_text("")
                            if text.startswith("//"):
                                self.handle_command(text)
                            else:
                                self.add_message("You", text)
                                self.process_user_input(text)

                elif event.type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == self.send_btn:
                        text = self.input_box.get_text().strip()
                        if text:
                            self.input_box.set_text("")
                            if text.startswith("//"):
                                self.handle_command(text)
                            else:
                                self.add_message("You", text)
                                self.process_user_input(text)

                    elif event.ui_element == self.voice_btn:
                        self.handle_command("//voice")

                    elif event.ui_element == self.tts_btn:
                        self.handle_command("//speak")

                    elif event.ui_element == self.avatar_btn:
                        self.handle_command("//avatar")

                    elif event.ui_element == self.emotion_btn:
                        # Cycle through emotions for testing
                        emotions = ['happy', 'surprised', 'sad', 'angry', 'confused', 'neutral']
                        import random
                        emotion = random.choice(emotions)
                        self.handle_command(f"//emotion {emotion}")

                    elif event.ui_element == self.clear_btn:
                        self.handle_command("//clear")

                    elif event.ui_element == self.volume_btn:
                        # Cycle volume between 25%, 50%, 75%, 100%
                        if hasattr(self, 'tts') and self.tts:
                            current_vol = self.tts.get_volume()
                            new_vol = 25 if current_vol >= 100 else current_vol + 25
                            self.handle_command(f"//volume {new_vol}")

                    elif event.ui_element == self.avatar_window_btn:
                        if self.avatar_display_running:
                            shutdown_avatar()
                            self.avatar_display_running = False
                        else:
                            self.start_avatar_display_async()

                    elif event.ui_element == self.exit_btn:
                        self.running = False

                self.manager.process_events(event)

            # Update UI
            self.manager.update(time_delta)

            # Periodic status update
            if int(time.time()) % 5 == 0:  # Every 5 seconds
                self.update_status_indicators()

            # Draw everything
            self.screen.fill(self.BG_COLOR)
            self.manager.draw_ui(self.screen)
            pygame.display.flip()

        # Cleanup
        self.cleanup()

    def cleanup(self):
        """Cleanup all resources"""
        print("🛑 Shutting down application...")

        # Stop voice listening
        self.stop_listening = True
        if hasattr(self, 'listening_thread') and self.listening_thread and self.listening_thread.is_alive():
            self.listening_thread.join(timeout=2.0)

        # Shutdown avatar
        if LIVE2D_AVAILABLE and (self.avatar_enabled or self.avatar_display_running):
            try:
                shutdown_avatar()
                print("✅ Avatar shutdown complete")
            except Exception as e:
                print(f"⚠️ Avatar shutdown error: {e}")

        # Wait for avatar init thread
        if hasattr(self, 'avatar_init_thread') and self.avatar_init_thread and self.avatar_init_thread.is_alive():
            self.avatar_init_thread.join(timeout=2.0)

        pygame.quit()
        print("✅ Application shutdown complete")


if __name__ == "__main__":
    try:
        app = VTuberChatApp()
        app.run()
    except KeyboardInterrupt:
        print("\n🛑 Application interrupted by user")
    except Exception as e:
        print(f"❌ Application error: {e}")
    finally:
        sys.exit(0)