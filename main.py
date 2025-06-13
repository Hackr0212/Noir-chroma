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


class Button:
    def __init__(self, x, y, width, height, text, font, color=(70, 70, 80), hover_color=(90, 90, 100), text_color=(255, 255, 255)):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.is_hovered = False
        self.is_pressed = False
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.is_pressed = True
                return True
        elif event.type == pygame.MOUSEBUTTONUP:
            if self.is_pressed and self.rect.collidepoint(event.pos):
                self.is_pressed = False
                return True
            self.is_pressed = False
        elif event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        return False
    
    def draw(self, screen):
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, (120, 120, 120), self.rect, 2)
        
        text_surface = self.font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)
    
    def set_text(self, text):
        self.text = text


class TextBox:
    def __init__(self, x, y, width, height, font, max_length=500):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.text = ""
        self.max_length = max_length
        self.active = False
        self.cursor_pos = 0
        self.cursor_visible = True
        self.cursor_timer = 0
        self.scroll_offset = 0
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                return True
            elif event.key == pygame.K_BACKSPACE:
                if self.cursor_pos > 0:
                    self.text = self.text[:self.cursor_pos-1] + self.text[self.cursor_pos:]
                    self.cursor_pos -= 1
            elif event.key == pygame.K_DELETE:
                if self.cursor_pos < len(self.text):
                    self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos+1:]
            elif event.key == pygame.K_LEFT:
                self.cursor_pos = max(0, self.cursor_pos - 1)
            elif event.key == pygame.K_RIGHT:
                self.cursor_pos = min(len(self.text), self.cursor_pos + 1)
            elif event.key == pygame.K_HOME:
                self.cursor_pos = 0
            elif event.key == pygame.K_END:
                self.cursor_pos = len(self.text)
            elif event.unicode.isprintable() and len(self.text) < self.max_length:
                self.text = self.text[:self.cursor_pos] + event.unicode + self.text[self.cursor_pos:]
                self.cursor_pos += 1
        return False
    
    def update(self, dt):
        self.cursor_timer += dt
        if self.cursor_timer >= 500:  # Blink every 500ms
            self.cursor_visible = not self.cursor_visible
            self.cursor_timer = 0
    
    def draw(self, screen):
        # Draw background
        color = (50, 50, 60) if self.active else (40, 40, 50)
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, (100, 100, 110) if self.active else (80, 80, 90), self.rect, 2)
        
        # Draw text
        if self.text:
            text_surface = self.font.render(self.text, True, (255, 255, 255))
            text_rect = text_surface.get_rect()
            text_rect.left = self.rect.left + 5
            text_rect.centery = self.rect.centery
            
            # Handle horizontal scrolling
            if text_rect.width > self.rect.width - 10:
                self.scroll_offset = max(0, text_rect.width - self.rect.width + 20)
                text_rect.left -= self.scroll_offset
            
            # Clip text to textbox
            clip_rect = self.rect.copy()
            clip_rect.width -= 10
            clip_rect.left += 5
            screen.set_clip(clip_rect)
            screen.blit(text_surface, text_rect)
            screen.set_clip(None)
        
        # Draw cursor
        if self.active and self.cursor_visible:
            cursor_text = self.text[:self.cursor_pos]
            cursor_width = self.font.size(cursor_text)[0] if cursor_text else 0
            cursor_x = self.rect.left + 5 + cursor_width - self.scroll_offset
            if self.rect.left + 5 <= cursor_x <= self.rect.right - 5:
                pygame.draw.line(screen, (255, 255, 255), 
                               (cursor_x, self.rect.top + 5), 
                               (cursor_x, self.rect.bottom - 5), 2)
    
    def get_text(self):
        return self.text
    
    def set_text(self, text):
        self.text = text
        self.cursor_pos = len(text)
    
    def clear(self):
        self.text = ""
        self.cursor_pos = 0


class ScrollableTextArea:
    def __init__(self, x, y, width, height, font):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.lines = []
        self.scroll_offset = 0
        self.line_height = font.get_height() + 2
        self.max_visible_lines = height // self.line_height
    
    def add_line(self, text, color=(255, 255, 255)):
        # Word wrap long lines
        words = text.split(' ')
        current_line = ""
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            if self.font.size(test_line)[0] <= self.rect.width - 20:
                current_line = test_line
            else:
                if current_line:
                    self.lines.append((current_line, color))
                current_line = word
        
        if current_line:
            self.lines.append((current_line, color))
        
        # Auto-scroll to bottom
        if len(self.lines) > self.max_visible_lines:
            self.scroll_offset = len(self.lines) - self.max_visible_lines
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL and self.rect.collidepoint(pygame.mouse.get_pos()):
            self.scroll_offset -= event.y * 3
            self.scroll_offset = max(0, min(self.scroll_offset, len(self.lines) - self.max_visible_lines))
    
    def draw(self, screen):
        # Draw background
        pygame.draw.rect(screen, (20, 20, 30), self.rect)
        pygame.draw.rect(screen, (60, 60, 70), self.rect, 2)
        
        # Draw lines
        clip_rect = self.rect.copy()
        clip_rect.width -= 10
        clip_rect.height -= 10
        clip_rect.left += 5
        clip_rect.top += 5
        screen.set_clip(clip_rect)
        
        start_line = max(0, self.scroll_offset)
        end_line = min(len(self.lines), start_line + self.max_visible_lines)
        
        for i in range(start_line, end_line):
            line_text, line_color = self.lines[i]
            y_pos = self.rect.top + 5 + (i - start_line) * self.line_height
            text_surface = self.font.render(line_text, True, line_color)
            screen.blit(text_surface, (self.rect.left + 5, y_pos))
        
        screen.set_clip(None)
        
        # Draw scrollbar if needed
        if len(self.lines) > self.max_visible_lines:
            scrollbar_height = max(20, (self.max_visible_lines / len(self.lines)) * self.rect.height)
            scrollbar_y = self.rect.top + (self.scroll_offset / len(self.lines)) * self.rect.height
            scrollbar_rect = pygame.Rect(self.rect.right - 10, scrollbar_y, 8, scrollbar_height)
            pygame.draw.rect(screen, (100, 100, 100), scrollbar_rect)
    
    def clear(self):
        self.lines = []
        self.scroll_offset = 0


class VTuberChatApp:
    def __init__(self):
        # Initialize pygame
        pygame.init()

        # Screen dimensions
        self.WIDTH, self.HEIGHT = 1400, 900
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("Noir VTuber Chat Assistant")

        # Colors
        self.BG_COLOR = (30, 30, 40)
        self.CHAT_BG = (20, 20, 30)
        self.INPUT_BG = (40, 40, 50)

        # Fonts
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 20)
        self.title_font = pygame.font.Font(None, 32)

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

        # Create UI elements
        self.create_ui()

        # Initialize components
        self.initialize_components()

        # Welcome message
        self.add_message("System", "🎭 Noir VTuber Chat Assistant initialized!", (255, 170, 85))
        self.add_message("System", "💡 Commands: //voice, //speak, //avatar, //clear, //volume [0-100], //exit", (255, 170, 85))

        if LIVE2D_AVAILABLE:
            self.add_message("System", "🎨 Live2D avatar support available! Click 'Avatar: OFF' to enable.", (255, 170, 85))

    def initialize_components(self):
        """Initialize core components with error handling"""
        try:
            self.recognizer = SpeechRecognizer()
            self.add_message("System", "🎤 Speech recognizer initialized", (85, 255, 85))
        except Exception as e:
            self.add_message("System", f"❌ Speech recognizer error: {e}", (255, 85, 85))
            self.recognizer = None

        try:
            self.tts = TextToSpeech()
            self.add_message("System", "🔊 Text-to-speech initialized", (85, 255, 85))
        except Exception as e:
            self.add_message("System", f"❌ TTS error: {e}", (255, 85, 85))
            self.tts = None

        try:
            self.ai_client = DeepSeekClient()
            self.add_message("System", "🤖 AI client initialized", (85, 255, 85))
        except Exception as e:
            self.add_message("System", f"❌ AI client error: {e}", (255, 85, 85))
            self.ai_client = None

    def create_ui(self):
        """Create all UI elements"""
        # Chat history area
        self.chat_area = ScrollableTextArea(20, 20, 860, 650, self.font)
        
        # Input text box
        self.input_box = TextBox(20, 690, 700, 40, self.font)
        
        # Send button
        self.send_btn = Button(730, 690, 150, 40, "Send Message", self.font)
        
        # Control buttons
        button_width = 180
        button_height = 35
        button_y = 750
        
        # First row of buttons
        self.voice_btn = Button(20, button_y, button_width, button_height, "Voice Input: OFF", self.small_font)
        self.tts_btn = Button(210, button_y, button_width, button_height, "TTS: OFF", self.small_font)
        self.avatar_btn = Button(400, button_y, button_width, button_height, "Avatar: OFF", self.small_font)
        self.emotion_btn = Button(590, button_y, button_width, button_height, "Test Emotion", self.small_font)
        
        # Second row of buttons
        button_y += 45
        self.clear_btn = Button(20, button_y, button_width, button_height, "Clear History", self.small_font)
        self.volume_btn = Button(210, button_y, button_width, button_height, "Volume: 75%", self.small_font)
        self.avatar_window_btn = Button(400, button_y, button_width, button_height, "Show Avatar Window", self.small_font)
        self.exit_btn = Button(590, button_y, button_width, button_height, "Exit Application", self.small_font)
        
        # Status area
        self.status_area = ScrollableTextArea(900, 20, 480, 820, self.small_font)
        
        # Voice activity indicator
        self.voice_indicator_rect = pygame.Rect(735, 695, 15, 30)
        self.voice_indicator_active = False
        
        # All UI elements for easy event handling
        self.buttons = [
            self.send_btn, self.voice_btn, self.tts_btn, self.avatar_btn,
            self.emotion_btn, self.clear_btn, self.volume_btn, 
            self.avatar_window_btn, self.exit_btn
        ]

    def add_message(self, sender, message, color=None):
        """Add a message to the chat history"""
        timestamp = time.strftime("%H:%M:%S")
        
        # Default colors based on sender
        if color is None:
            if sender == "AI":
                color = (85, 170, 255)
            elif sender == "You":
                color = (85, 255, 85)
            elif sender == "System":
                color = (255, 170, 85)
            else:
                color = (255, 255, 255)
        
        formatted_msg = f"[{timestamp}] {sender}: {message}"
        self.chat_area.add_line(formatted_msg, color)
        
        # Keep conversation history for AI
        self.conversation_history.append(formatted_msg)

    def update_status_display(self):
        """Update the status display area"""
        self.status_area.clear()
        
        # Title
        self.status_area.add_line("🎭 NOIR VTUBER STATUS", (255, 255, 255))
        self.status_area.add_line("", (255, 255, 255))
        
        # Core components
        self.status_area.add_line("Core Components:", (200, 200, 200))
        voice_status = "ENABLED" if self.voice_input_enabled else "DISABLED"
        voice_color = (85, 255, 85) if self.voice_input_enabled else (255, 85, 85)
        self.status_area.add_line(f"🎤 Voice Input: {voice_status}", voice_color)
        
        tts_status = "ENABLED" if self.tts_enabled else "DISABLED"
        tts_color = (85, 255, 85) if self.tts_enabled else (255, 85, 85)
        self.status_area.add_line(f"🔊 Text-to-Speech: {tts_status}", tts_color)
        
        ai_status = "READY" if hasattr(self, 'ai_client') and self.ai_client else "ERROR"
        ai_color = (85, 255, 85) if hasattr(self, 'ai_client') and self.ai_client else (255, 85, 85)
        self.status_area.add_line(f"🤖 AI Client: {ai_status}", ai_color)
        
        self.status_area.add_line("", (255, 255, 255))
        
        # Avatar system
        self.status_area.add_line("Avatar System:", (200, 200, 200))
        if LIVE2D_AVAILABLE:
            if self.avatar_initializing:
                self.status_area.add_line("🎨 Avatar: INITIALIZING...", (255, 170, 85))
            elif self.avatar_enabled:
                avatar_running = is_avatar_running()
                avatar_status = "RUNNING" if avatar_running else "ENABLED"
                avatar_color = (85, 255, 85) if avatar_running else (255, 170, 85)
                self.status_area.add_line(f"🎨 Avatar: {avatar_status}", avatar_color)
                
                display_status = "ACTIVE" if self.avatar_display_running else "INACTIVE"
                display_color = (85, 255, 85) if self.avatar_display_running else (255, 85, 85)
                self.status_area.add_line(f"🖥️ Display: {display_status}", display_color)
            else:
                self.status_area.add_line("🎨 Avatar: DISABLED", (255, 85, 85))
        else:
            self.status_area.add_line("🎨 Live2D: NOT AVAILABLE", (255, 85, 85))
        
        self.status_area.add_line("", (255, 255, 255))
        
        # Performance info
        self.status_area.add_line("Performance:", (200, 200, 200))
        self.status_area.add_line(f"💬 Messages: {len(self.conversation_history)}", (255, 255, 255))
        self.status_area.add_line(f"🔄 Chat History: {len(self.chat_messages)}", (255, 255, 255))
        
        listen_status = "ACTIVE" if self.is_listening else "INACTIVE"
        listen_color = (85, 255, 85) if self.is_listening else (255, 85, 85)
        self.status_area.add_line(f"🔄 Listening: {listen_status}", listen_color)
        
        self.status_area.add_line(f"🖱️ Mouse: {self.last_mouse_pos[0]}, {self.last_mouse_pos[1]}", (255, 255, 255))
        
        self.status_area.add_line("", (255, 255, 255))
        
        # Commands help
        self.status_area.add_line("💡 Available Commands:", (200, 200, 200))
        commands = [
            "//voice - Toggle voice input",
            "//speak - Toggle text-to-speech", 
            "//avatar - Toggle avatar system",
            "//clear - Clear chat history",
            "//volume [0-100] - Set TTS volume",
            "//emotion [happy/sad/angry] - Test emotion",
            "//exit - Exit application"
        ]
        for cmd in commands:
            self.status_area.add_line(cmd, (180, 180, 180))

    def initialize_avatar_async(self):
        """Initialize avatar in a separate thread"""
        if not LIVE2D_AVAILABLE:
            self.add_message("System", "❌ Live2D not available", (255, 85, 85))
            return

        if self.avatar_initializing:
            self.add_message("System", "⚠️ Avatar already initializing", (255, 170, 85))
            return

        self.avatar_initializing = True
        self.avatar_btn.set_text("Avatar: INIT")

        def init_thread():
            try:
                self.add_message("System", "🎭 Initializing Live2D avatar...", (255, 170, 85))

                # Initialize avatar with window size
                success = initialize_live2d_avatar(window_size=(800, 600))

                if success:
                    self.add_message("System", "✅ Live2D avatar initialized successfully!", (85, 255, 85))
                    self.avatar_enabled = True
                    self.avatar_btn.set_text("Avatar: ON")
                else:
                    self.add_message("System", "❌ Failed to initialize Live2D avatar", (255, 85, 85))
                    self.avatar_enabled = False
                    self.avatar_btn.set_text("Avatar: OFF")

            except Exception as e:
                self.add_message("System", f"❌ Avatar initialization error: {e}", (255, 85, 85))
                self.avatar_enabled = False
                self.avatar_btn.set_text("Avatar: OFF")
            finally:
                self.avatar_initializing = False

        self.avatar_init_thread = threading.Thread(target=init_thread, daemon=True)
        self.avatar_init_thread.start()

    def start_avatar_display_async(self):
        """Start avatar display window in separate thread"""
        if not self.avatar_enabled:
            self.add_message("System", "❌ Avatar not initialized", (255, 85, 85))
            return

        if self.avatar_display_running:
            self.add_message("System", "⚠️ Avatar display already running", (255, 170, 85))
            return

        def display_thread():
            try:
                self.add_message("System", "🖥️ Starting avatar display window...", (255, 170, 85))
                success = start_live2d_display()

                if success:
                    self.avatar_display_running = True
                    self.add_message("System", "✅ Avatar display started!", (85, 255, 85))
                    self.avatar_window_btn.set_text("Hide Avatar")

                    # Monitor avatar status
                    while self.avatar_display_running and is_avatar_running():
                        self.last_avatar_status = get_avatar_status()
                        time.sleep(1.0)

                    self.avatar_display_running = False
                    self.add_message("System", "🖥️ Avatar display stopped", (255, 170, 85))
                    self.avatar_window_btn.set_text("Show Avatar Window")
                else:
                    self.add_message("System", "❌ Failed to start avatar display", (255, 85, 85))

            except Exception as e:
                self.add_message("System", f"❌ Avatar display error: {e}", (255, 85, 85))
                self.avatar_display_running = False
                self.avatar_window_btn.set_text("Show Avatar Window")

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
            self.add_message("System", "❌ Speech recognizer not available", (255, 85, 85))
            return

        self.is_listening = True
        self.stop_listening = False

        def voice_loop():
            while not self.stop_listening:
                if self.voice_input_enabled:
                    try:
                        self.voice_indicator_active = True
                        text = self.recognizer.listen_with_voice_detection()
                        self.voice_indicator_active = False

                        if text and not self.stop_listening:
                            # Add to chat and process
                            self.add_message("You", text)
                            self.process_user_input(text)
                    except Exception as e:
                        self.add_message("System", f"Voice recognition error: {e}", (255, 85, 85))
                        time.sleep(1.0)
                else:
                    time.sleep(0.1)
            self.is_listening = False

        self.listening_thread = threading.Thread(target=voice_loop, daemon=True)
        self.listening_thread.start()

    def process_user_input(self, user_input):
        """Process user input and get AI response"""
        if not hasattr(self, 'ai_client') or not self.ai_client:
            self.add_message("System", "❌ AI client not available", (255, 85, 85))
            return

        try:
            self.add_message("System", "🤖 Processing...", (255, 170, 85))

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
                        self.add_message("System", f"TTS error: {e}", (255, 85, 85))

                # Update avatar with response
                if self.avatar_enabled and LIVE2D_AVAILABLE:
                    try:
                        handle_ai_response(full_response)
                    except Exception as e:
                        self.add_message("System", f"Avatar response error: {e}", (255, 85, 85))
            else:
                self.add_message("System", "❌ Empty response from AI", (255, 85, 85))

        except Exception as e:
            self.add_message("System", f"AI processing error: {e}", (255, 85, 85))

    def handle_command(self, command):
        """Handle special commands"""
        cmd = command.lower().strip()
        parts = cmd.split()

        if cmd == "//exit":
            self.running = False

        elif cmd == "//voice":
            if hasattr(self, 'recognizer') and self.recognizer:
                self.voice_input_enabled = not self.voice_input_enabled
                self.voice_btn.set_text(f"Voice Input: {'ON' if self.voice_input_enabled else 'OFF'}")
                if self.voice_input_enabled:
                    self.start_voice_listening()
                else:
                    self.stop_listening = True
            else:
                self.add_message("System", "❌ Voice input not available", (255, 85, 85))

        elif cmd == "//speak":
            if hasattr(self, 'tts') and self.tts:
                self.tts_enabled = not self.tts_enabled
                self.tts_btn.set_text(f"TTS: {'ON' if self.tts_enabled else 'OFF'}")
            else:
                self.add_message("System", "❌ TTS not available", (255, 85, 85))

        elif cmd == "//avatar":
            if LIVE2D_AVAILABLE:
                if not self.avatar_enabled and not self.avatar_initial