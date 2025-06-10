import os
import io
import tempfile
import platform
import pygame
import soundfile as sf
import numpy as np
import subprocess
from typing import Optional, List, Tuple
import time
import threading
import re


class TextToSpeech:
    def __init__(self):
        self.sample_rate = 22050

        # Initialize pygame mixer
        try:
            pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=1024)
            pygame.mixer.init()
            print("✅ Pygame mixer initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize pygame mixer: {e}")
            raise

        # PiperTTS configuration
        self.piper_exe = os.path.join("piper", "piper.exe")
        self.piper_model = None
        self.available_models = []

        self.initialize_piper()

    def initialize_piper(self):
        """Initialize PiperTTS and find available models"""
        try:
            if not os.path.exists(self.piper_exe):
                print(f"❌ Piper executable not found at: {self.piper_exe}")
                print("Please ensure piper.exe is in the 'piper' folder")
                return False

            print(f"✅ Found Piper executable: {self.piper_exe}")

            piper_dir = "piper"
            model_files = []

            for file in os.listdir(piper_dir):
                if file.endswith('.onnx'):
                    model_files.append(file)

            if not model_files:
                print("⚠️ No .onnx model files found in piper directory")
                print("Please download a voice model from: https://github.com/rhasspy/piper/releases")
                print("Example models: en_US-lessac-medium.onnx, en_US-amy-medium.onnx")
                return False

            self.piper_model = os.path.join(piper_dir, model_files[0])
            self.available_models = model_files

            print(f"🎤 Using voice model: {model_files[0]}")
            print(f"📋 Available models: {', '.join(model_files)}")

            return True

        except Exception as e:
            print(f"Error initializing Piper: {e}")
            return False

    def extract_speech_content(self, text: str) -> Optional[str]:
        """Extract only the speech content from LLM output"""
        # Look for speech markers like 🗣️ followed by quoted text
        speech_pattern = r"🗣️\s*['\"]([^'\"]+)['\"]"

        matches = re.findall(speech_pattern, text)

        if matches:
            # Join multiple speech segments if found
            speech_text = " ".join(matches)
            print(f"📢 Extracted speech: {speech_text}")
            return speech_text

        # Fallback: if no speech marker found, check if text is mostly emojis/symbols
        # If it's mostly text content, use it as-is
        text_without_emojis = re.sub(r'[^\w\s.,!?-]', '', text)
        if len(text_without_emojis.strip()) > len(text) * 0.3:  # If 30% or more is actual text
            print(f"📢 No speech marker found, using full text")
            return text
        else:
            print(f"📢 Text appears to be mostly emojis/symbols, skipping TTS")
            return None

    def set_voice_model(self, model_name: str):
        """Set the voice model to use"""
        model_path = os.path.join("piper", model_name)
        if os.path.exists(model_path):
            self.piper_model = model_path
            print(f"🎤 Voice model changed to: {model_name}")
            return True
        else:
            print(f"❌ Model not found: {model_name}")
            print(f"Available models: {', '.join(self.available_models)}")
            return False

    def generate_speech_audio_file(self, text: str) -> Optional[str]:
        """Generate speech audio file using PiperTTS and return the file path"""
        try:
            if not self.piper_model or not os.path.exists(self.piper_model):
                print("❌ No valid Piper model available")
                return None

            clean_text = self._clean_text_for_speech(text)

            # Create temporary file for audio output
            temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            audio_file_path = temp_audio.name
            temp_audio.close()

            try:
                cmd = [
                    self.piper_exe,
                    '--model', self.piper_model,
                    '--output_file', audio_file_path
                ]

                process = subprocess.run(
                    cmd,
                    input=clean_text,
                    text=True,
                    capture_output=True,
                    timeout=30
                )

                if process.returncode != 0:
                    print(f"❌ Piper TTS error: {process.stderr}")
                    return None

                if os.path.exists(audio_file_path) and os.path.getsize(audio_file_path) > 0:
                    return audio_file_path
                else:
                    print("❌ Piper did not generate audio file")
                    return None

            except subprocess.TimeoutExpired:
                print("❌ Piper TTS timeout")
                return None

        except Exception as e:
            print(f"❌ Error generating speech with Piper: {e}")
            return None

    def play_audio_file(self, audio_file_path: str):
        """Play audio file using pygame"""
        try:
            if not os.path.exists(audio_file_path):
                print(f"❌ Audio file not found: {audio_file_path}")
                return False

            print("🔊 Playing audio with pygame...")

            # Load and play the audio file
            pygame.mixer.music.load(audio_file_path)
            pygame.mixer.music.play()

            # Wait for playback to finish
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)

            print("✅ Audio playback completed")
            return True

        except Exception as e:
            print(f"❌ Error playing audio with pygame: {e}")
            return False

    def speak(self, text: str):
        """Convert text to speech and play it - now with speech filtering and pygame"""
        if not text.strip():
            print("No text to speak")
            return

        try:
            # Extract only the speech content
            speech_content = self.extract_speech_content(text)

            if not speech_content:
                print("No speech content found to vocalize")
                return

            print(f"🎤 Generating speech with Piper: {speech_content[:50]}{'...' if len(speech_content) > 50 else ''}")

            # Generate audio file from extracted speech
            audio_file_path = self.generate_speech_audio_file(speech_content)
            if audio_file_path is None:
                print("Failed to generate speech audio")
                return

            # Play the audio file
            success = self.play_audio_file(audio_file_path)

            # Clean up temporary file
            try:
                os.unlink(audio_file_path)
            except:
                pass

            if not success:
                print("Failed to play audio")

        except Exception as e:
            print(f"Error in speak method: {e}")

    def speak_async(self, text: str):
        """Speak text asynchronously (non-blocking)"""

        def speak_thread():
            self.speak(text)

        thread = threading.Thread(target=speak_thread, daemon=True)
        thread.start()
        return thread

    def _clean_text_for_speech(self, text: str) -> str:
        """Clean text for better speech synthesis"""
        # Remove excessive punctuation
        text = re.sub(r'[.]{2,}', '.', text)
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)

        # Handle common internet slang/abbreviations
        replacements = {
            'lol': 'laugh out loud',
            'omg': 'oh my god',
            'btw': 'by the way',
            'imo': 'in my opinion',
            'tbh': 'to be honest',
            'irl': 'in real life',
            'afk': 'away from keyboard',
            'brb': 'be right back',
            'gtg': 'got to go',
            'ttyl': 'talk to you later',
            'nyet': 'no',  # Russian no
            'da': 'yes',  # Russian yes
        }

        for abbr, full in replacements.items():
            text = re.sub(r'\b' + re.escape(abbr) + r'\b', full, text, flags=re.IGNORECASE)

        # Handle some VTuber/gaming specific terms
        vtuber_replacements = {
            'vtuber': 'virtual tuber',
            'pog': 'awesome',
            'poggers': 'amazing',
            'kek': 'laugh',
            'sus': 'suspicious',
            'based': 'cool',
            'cringe': 'cringy',
            'comrade': 'friend',
        }

        for term, replacement in vtuber_replacements.items():
            text = re.sub(r'\b' + re.escape(term) + r'\b', replacement, text, flags=re.IGNORECASE)

        # Remove markdown formatting and emojis from speech text
        text = re.sub(r'[*_~`]', '', text)
        text = re.sub(r'[^\w\s.,!?()-]', '', text)  # Remove emojis and special symbols

        # Handle special characters
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")

        return text.strip()

    def test_speech_extraction(self):
        """Test the speech extraction functionality"""
        test_cases = [
            "🧠 *Oh no, human has discovered my fatal flaw—no sense of direction!*\n🎬 *frantically spins compass made of seashells*\n🗣️ 'Nyet comrade, we took wrong turn at Area 51! 🛸🦈 Now lost in Bermuda Triangle... but hey, free WiFi! (And maybe ghosts?) 👻💀'",
            "🗣️ 'Hello there! How are you doing today?'",
            "Regular text without any speech markers",
            "🎭🎪🎨 Just emojis and symbols! 🚀🌟✨",
            "🗣️ 'First speech' and then 🗣️ 'Second speech'"
        ]

        print("\n=== Testing Speech Extraction ===")
        for i, test in enumerate(test_cases, 1):
            print(f"\nTest {i}: {test[:50]}...")
            result = self.extract_speech_content(test)
            print(f"Result: {result}")

    def test_pygame(self) -> bool:
        """Test if pygame audio is working"""
        try:
            print("✅ Pygame mixer status:")
            print(f"  Initialized: {pygame.mixer.get_init() is not None}")
            print(f"  Frequency: {pygame.mixer.get_init()[0] if pygame.mixer.get_init() else 'N/A'}")
            print(f"  Channels: {pygame.mixer.get_init()[2] if pygame.mixer.get_init() else 'N/A'}")
            return True
        except Exception as e:
            print(f"❌ Pygame test failed: {e}")
            return False

    def test_piper(self) -> bool:
        """Test if PiperTTS is working"""
        try:
            if not os.path.exists(self.piper_exe):
                print("❌ Piper executable not found")
                return False

            if not self.piper_model:
                print("❌ No Piper model available")
                return False

            print("✅ Piper TTS detected")
            print(f"Executable: {self.piper_exe}")
            print(f"Model: {os.path.basename(self.piper_model)}")

            test_text = "Piper TTS test successful! This is Noir speaking."
            print(f"Testing with: '{test_text}'")

            audio_file_path = self.generate_speech_audio_file(test_text)
            if audio_file_path:
                success = self.play_audio_file(audio_file_path)
                # Clean up
                try:
                    os.unlink(audio_file_path)
                except:
                    pass
                return success
            else:
                print("❌ Failed to generate test audio")
                return False

        except Exception as e:
            print(f"❌ Piper test failed: {e}")
            return False

    def test_speech(self):
        """Test text-to-speech functionality"""
        print("\n=== Testing Text-to-Speech ===")

        # Test pygame
        if self.test_pygame():
            print("✅ Pygame audio system ready")
        else:
            print("❌ Pygame audio system failed")
            return

        # Test Piper
        if self.test_piper():
            print("✅ PiperTTS working correctly")
        else:
            print("❌ PiperTTS test failed")

    def stop_audio(self):
        """Stop current audio playback"""
        try:
            pygame.mixer.music.stop()
            print("🛑 Audio playback stopped")
        except Exception as e:
            print(f"Error stopping audio: {e}")

    def set_volume(self, volume: float):
        """Set playback volume (0.0 to 1.0)"""
        try:
            volume = max(0.0, min(1.0, volume))  # Clamp between 0 and 1
            pygame.mixer.music.set_volume(volume)
            print(f"🔊 Volume set to {int(volume * 100)}%")
        except Exception as e:
            print(f"Error setting volume: {e}")

    def pause_audio(self):
        """Pause current audio playback"""
        try:
            pygame.mixer.music.pause()
            print("⏸️ Audio paused")
        except Exception as e:
            print(f"Error pausing audio: {e}")

    def unpause_audio(self):
        """Resume paused audio playback"""
        try:
            pygame.mixer.music.unpause()
            print("▶️ Audio resumed")
        except Exception as e:
            print(f"Error resuming audio: {e}")

    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        except:
            pass