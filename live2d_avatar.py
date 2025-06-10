# live2d_avatar.py
import pygame
import OpenGL.GL as gl
from OpenGL.GL import *
import live2d.v3 as live2d  # Assuming you're using Cubism 3.0+ models
import numpy as np
import threading
import time
import re
import json
import os
from typing import Optional, Dict, List, Tuple


class Live2DAvatar:
    def __init__(self, model_path: str, window_size: Tuple[int, int] = (800, 600)):
        """
        Initialize Live2D Avatar

        Args:
            model_path: Path to the Live2D model directory
            window_size: (width, height) of the display window
        """
        self.model_path = model_path
        self.window_size = window_size
        self.model = None
        self.is_initialized = False

        # Animation states
        self.current_motion = None
        self.is_speaking = False
        self.mouse_pos = (0, 0)
        self.blink_timer = 0
        self.breathing_timer = 0

        # Expression mapping for Noir's responses
        self.expression_patterns = {
            'happy': r'(laugh|lol|haha|😄|😊|🎉|poggers?|awesome)',
            'surprised': r'(wow|omg|whoa|😮|🤯|what\?!)',
            'angry': r'(grr|angry|mad|😠|rage|ugh)',
            'sad': r'(sad|cry|😢|😭|oof|rip)',
            'confused': r'(confused|what|huh|\?{2,}|🤔)',
            'mischievous': r'(hehe|scheme|plan|evil|😈|sus)',
            'embarrassed': r'(blush|embarrass|shy|awkward|😳)',
        }

        # Parameter control ranges
        self.param_ranges = {
            'ParamAngleX': (-30, 30),  # Head rotation X
            'ParamAngleY': (-30, 30),  # Head rotation Y
            'ParamAngleZ': (-30, 30),  # Head rotation Z
            'ParamEyeLOpen': (0, 1),  # Left eye open
            'ParamEyeROpen': (0, 1),  # Right eye open
            'ParamEyeBallX': (-1, 1),  # Eye ball X
            'ParamEyeBallY': (-1, 1),  # Eye ball Y
            'ParamMouthOpenY': (0, 1),  # Mouth open
            'ParamMouthForm': (-1, 1),  # Mouth form
            'ParamBodyAngleX': (-10, 10),  # Body angle X
            'ParamBreath': (0, 1),  # Breathing
        }

    def initialize(self) -> bool:
        """Initialize Live2D model and OpenGL context"""
        try:
            # Initialize pygame and OpenGL
            pygame.init()
            pygame.display.set_mode(self.window_size, pygame.OPENGL | pygame.DOUBLEBUF)
            pygame.display.set_caption("Noir VTuber Avatar")

            # Initialize OpenGL settings
            self._setup_opengl()

            # Load Live2D model
            model_json_path = self._find_model_json()
            if not model_json_path:
                print("❌ Could not find model.json file")
                return False

            print(f"📁 Loading Live2D model from: {model_json_path}")
            self.model = live2d.LAppModel()

            if not self.model.LoadModelJson(model_json_path):
                print("❌ Failed to load Live2D model")
                return False

            print("✅ Live2D model loaded successfully")

            # Setup model parameters
            self._setup_model_parameters()

            self.is_initialized = True
            return True

        except Exception as e:
            print(f"❌ Error initializing Live2D avatar: {e}")
            return False

    def _setup_opengl(self):
        """Setup OpenGL rendering context"""
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(0.0, 0.0, 0.0, 0.0)  # Transparent background

        # Setup projection matrix
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(-1.0, 1.0, -1.0, 1.0, -1.0, 1.0)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def _find_model_json(self) -> Optional[str]:
        """Find the model.json file in the model directory"""
        if not os.path.exists(self.model_path):
            print(f"❌ Model directory not found: {self.model_path}")
            return None

        # Look for model3.json (Cubism 3.0+) or model.json (Cubism 2.x)
        for filename in ['model3.json', 'model.json']:
            json_path = os.path.join(self.model_path, filename)
            if os.path.exists(json_path):
                return json_path

        # If not found directly, search recursively
        for root, dirs, files in os.walk(self.model_path):
            for file in files:
                if file.endswith(('.model3.json', '.model.json')):
                    return os.path.join(root, file)

        return None

    def _setup_model_parameters(self):
        """Setup initial model parameters"""
        if not self.model:
            return

        # Set initial neutral pose
        try:
            # Neutral head position
            self.model.SetParameterValue("ParamAngleX", 0)
            self.model.SetParameterValue("ParamAngleY", 0)
            self.model.SetParameterValue("ParamAngleZ", 0)

            # Eyes open
            self.model.SetParameterValue("ParamEyeLOpen", 1.0)
            self.model.SetParameterValue("ParamEyeROpen", 1.0)

            # Neutral mouth
            self.model.SetParameterValue("ParamMouthOpenY", 0)
            self.model.SetParameterValue("ParamMouthForm", 0)

            # Neutral body
            self.model.SetParameterValue("ParamBodyAngleX", 0)

            print("✅ Model parameters initialized")

        except Exception as e:
            print(f"⚠️ Some parameters may not be available: {e}")

    def update_mouse_tracking(self, mouse_pos: Tuple[int, int]):
        """Update eye tracking based on mouse position"""
        if not self.model or not self.is_initialized:
            return

        self.mouse_pos = mouse_pos

        # Convert mouse position to parameter values
        screen_width, screen_height = self.window_size

        # Normalize mouse position (-1 to 1)
        mouse_x = (mouse_pos[0] / screen_width) * 2 - 1
        mouse_y = 1 - (mouse_pos[1] / screen_height) * 2

        # Apply to eye tracking parameters
        try:
            eye_x = np.clip(mouse_x * 0.5, -1, 1)
            eye_y = np.clip(mouse_y * 0.3, -1, 1)

            self.model.SetParameterValue("ParamEyeBallX", eye_x)
            self.model.SetParameterValue("ParamEyeBallY", eye_y)

            # Subtle head tracking
            head_x = np.clip(mouse_x * 10, -15, 15)
            head_y = np.clip(mouse_y * 8, -10, 10)

            self.model.SetParameterValue("ParamAngleX", head_y)
            self.model.SetParameterValue("ParamAngleY", head_x)

        except Exception as e:
            print(f"⚠️ Mouse tracking parameter error: {e}")

    def analyze_emotion_from_text(self, text: str) -> str:
        """Analyze text to determine emotional expression"""
        text_lower = text.lower()

        # Check for emotion patterns
        for emotion, pattern in self.expression_patterns.items():
            if re.search(pattern, text_lower):
                return emotion

        # Default to neutral if no emotion detected
        return 'neutral'

    def set_expression(self, emotion: str, intensity: float = 1.0):
        """Set facial expression based on emotion"""
        if not self.model or not self.is_initialized:
            return

        try:
            intensity = np.clip(intensity, 0, 1)

            if emotion == 'happy':
                # Happy expression - smile
                self.model.SetParameterValue("ParamMouthForm", 1.0 * intensity)
                self.model.SetParameterValue("ParamEyeLOpen", 0.6 + 0.4 * intensity)
                self.model.SetParameterValue("ParamEyeROpen", 0.6 + 0.4 * intensity)

            elif emotion == 'surprised':
                # Surprised - wide eyes, open mouth
                self.model.SetParameterValue("ParamEyeLOpen", 1.0)
                self.model.SetParameterValue("ParamEyeROpen", 1.0)
                self.model.SetParameterValue("ParamMouthOpenY", 0.8 * intensity)

            elif emotion == 'angry':
                # Angry - narrow eyes, frown
                self.model.SetParameterValue("ParamEyeLOpen", 0.3)
                self.model.SetParameterValue("ParamEyeROpen", 0.3)
                self.model.SetParameterValue("ParamMouthForm", -0.8 * intensity)

            elif emotion == 'sad':
                # Sad - droopy eyes, down mouth
                self.model.SetParameterValue("ParamEyeLOpen", 0.5)
                self.model.SetParameterValue("ParamEyeROpen", 0.5)
                self.model.SetParameterValue("ParamMouthForm", -0.5 * intensity)

            elif emotion == 'mischievous':
                # Mischievous - wink and smirk
                self.model.SetParameterValue("ParamEyeLOpen", 0.2)  # Wink
                self.model.SetParameterValue("ParamEyeROpen", 1.0)
                self.model.SetParameterValue("ParamMouthForm", 0.6 * intensity)

            elif emotion == 'confused':
                # Confused - tilted head, slight frown
                self.model.SetParameterValue("ParamAngleZ", 10 * intensity)
                self.model.SetParameterValue("ParamMouthForm", -0.2 * intensity)

            elif emotion == 'embarrassed':
                # Embarrassed - eyes looking away
                self.model.SetParameterValue("ParamEyeBallX", 0.5 * intensity)
                self.model.SetParameterValue("ParamMouthForm", 0.3 * intensity)

            else:  # neutral
                # Reset to neutral
                self.model.SetParameterValue("ParamMouthForm", 0)
                self.model.SetParameterValue("ParamEyeLOpen", 1.0)
                self.model.SetParameterValue("ParamEyeROpen", 1.0)
                self.model.SetParameterValue("ParamAngleZ", 0)

        except Exception as e:
            print(f"⚠️ Expression parameter error: {e}")

    def start_lip_sync(self, text: str):
        """Start lip sync animation for speech"""
        if not self.model or not self.is_initialized:
            return

        self.is_speaking = True

        # Create lip sync thread
        def lip_sync_animation():
            try:
                # Simple lip sync based on text length and vowels
                words = text.split()
                vowels = 'aeiouAEIOU'

                for word in words:
                    if not self.is_speaking:
                        break

                    # Count vowels for mouth movement intensity
                    vowel_count = sum(1 for char in word if char in vowels)
                    mouth_open = min(vowel_count * 0.3, 1.0)

                    # Animate mouth movement
                    frames = max(10, len(word) * 2)  # Animation frames per word
                    for frame in range(frames):
                        if not self.is_speaking:
                            break

                        # Create mouth movement pattern
                        progress = frame / frames
                        mouth_value = mouth_open * np.sin(progress * np.pi * 2) * 0.5 + 0.5

                        self.model.SetParameterValue("ParamMouthOpenY", mouth_value)
                        time.sleep(0.05)  # 50ms per frame

                # Close mouth when done
                self.model.SetParameterValue("ParamMouthOpenY", 0)
                self.is_speaking = False

            except Exception as e:
                print(f"⚠️ Lip sync error: {e}")
                self.is_speaking = False

        # Start lip sync in background thread
        threading.Thread(target=lip_sync_animation, daemon=True).start()

    def stop_lip_sync(self):
        """Stop lip sync animation"""
        self.is_speaking = False
        if self.model:
            try:
                self.model.SetParameterValue("ParamMouthOpenY", 0)
            except:
                pass

    def update_idle_animations(self):
        """Update idle animations like blinking and breathing"""
        if not self.model or not self.is_initialized:
            return

        current_time = time.time()

        try:
            # Blinking animation
            if current_time - self.blink_timer > 3.0:  # Blink every 3 seconds
                self.blink_timer = current_time

                # Quick blink animation
                def blink_animation():
                    try:
                        # Close eyes
                        self.model.SetParameterValue("ParamEyeLOpen", 0.0)
                        self.model.SetParameterValue("ParamEyeROpen", 0.0)
                        time.sleep(0.1)

                        # Open eyes
                        self.model.SetParameterValue("ParamEyeLOpen", 1.0)
                        self.model.SetParameterValue("ParamEyeROpen", 1.0)
                    except:
                        pass

                threading.Thread(target=blink_animation, daemon=True).start()

            # Breathing animation
            breath_cycle = np.sin(current_time * 0.5) * 0.3 + 0.7  # Slow breathing
            self.model.SetParameterValue("ParamBreath", breath_cycle)

        except Exception as e:
            print(f"⚠️ Idle animation error: {e}")

    def render(self):
        """Render the Live2D model"""
        if not self.model or not self.is_initialized:
            return False

        try:
            # Clear screen
            glClear(GL_COLOR_BUFFER_BIT)

            # Update model
            self.model.Update()

            # Draw model
            self.model.Draw()

            # Update idle animations
            self.update_idle_animations()

            # Swap buffers
            pygame.display.flip()

            return True

        except Exception as e:
            print(f"❌ Render error: {e}")
            return False

    def handle_response(self, response_text: str):
        """Handle AI response - set emotion and start lip sync"""
        if not self.is_initialized:
            return

        # Analyze emotion from response
        emotion = self.analyze_emotion_from_text(response_text)
        print(f"🎭 Detected emotion: {emotion}")

        # Set facial expression
        self.set_expression(emotion, intensity=0.8)

        # Extract speech content for lip sync
        speech_content = self._extract_speech_content(response_text)
        if speech_content:
            self.start_lip_sync(speech_content)

    def _extract_speech_content(self, text: str) -> Optional[str]:
        """Extract speech content from AI response (similar to TTS extraction)"""
        # Look for speech markers like 🗣️ followed by quoted text
        speech_pattern = r"🗣️\s*['\"]([^'\"]+)['\"]"
        matches = re.findall(speech_pattern, text)

        if matches:
            return " ".join(matches)

        # Fallback to full text if no speech marker
        return text

    def cleanup(self):
        """Cleanup resources"""
        try:
            self.stop_lip_sync()
            if self.model:
                self.model = None
            pygame.quit()
            print("✅ Live2D avatar cleaned up")
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")

    def run_display_loop(self):
        """Main display loop for the Live2D avatar"""
        if not self.is_initialized:
            print("❌ Avatar not initialized, cannot start display loop")
            return

        print("🎬 Starting Live2D avatar display loop")
        clock = pygame.time.Clock()
        running = True

        while running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEMOTION:
                    self.update_mouse_tracking(event.pos)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

            # Render frame
            if not self.render():
                print("❌ Render failed, stopping display loop")
                break

            # Maintain 60 FPS
            clock.tick(60)

        self.cleanup()
        print("🎬 Live2D avatar display loop ended")