import os
import io
import tempfile
import platform
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
        self.current_audio_process = None

        # PiperTTS configuration - Linux version
        self.piper_exe = os.path.join("piper", "piper")
        self.piper_model = None
        self.available_models = []

        # Set up Linux-specific paths
        self.model_paths = [
            os.path.join("piper"),  # Local directory
            os.path.join(os.path.expanduser("~"), ".local", "share", "piper"),  # User's local share
            "/usr/share/piper",  # System-wide installation
        ]

        self.initialize_piper()

    def initialize_piper(self):
        """Initialize PiperTTS and find available models"""
        try:
            # Test if piper executable exists and is accessible
            if not os.path.exists(self.piper_exe):
                print(f"❌ Piper executable not found at: {self.piper_exe}")
                self._suggest_piper_installation()
                return False
                
            if not os.access(self.piper_exe, os.X_OK):
                print(f"❌ Piper executable is not executable: {self.piper_exe}")
                print("Run: chmod +x piper/piper")
                return False

            try:
                result = subprocess.run([self.piper_exe, '--help'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode != 0:
                    print(f"❌ Piper executable test failed: {self.piper_exe}")
                    return False
            except (FileNotFoundError, subprocess.TimeoutExpired) as e:
                print(f"❌ Piper executable not working: {e}")
                return False

            print(f"✅ Found Piper executable: {self.piper_exe}")

            # Look for model files in all possible locations
            model_files = []
            for path in self.model_paths:
                if os.path.exists(path):
                    for file in os.listdir(path):
                        if file.endswith('.onnx'):
                            model_files.append(os.path.join(path, file))

            if not model_files:
                print("⚠️ No .onnx model files found in any of the model directories")
                self._suggest_model_download()
                return False

            self.piper_model = model_files[0]
            self.available_models = [os.path.basename(f) for f in model_files]

            print(f"🎤 Using voice model: {os.path.basename(model_files[0])}")
            print(f"📋 Available models: {', '.join(self.available_models)}")

            return True

        except Exception as e:
            print(f"Error initializing Piper: {e}")
            return False

    def _suggest_piper_installation(self):
        """Suggest how to install Piper on Arch Linux"""
        print("\n📦 To install Piper TTS on Arch Linux:")
        print("1. Using AUR (recommended):")
        print("   # If you have yay:")
        print("   yay -S piper-tts")
        print("   # Or if you have paru:")
        print("   paru -S piper-tts")
        print("\n2. Or download manually:")
        print("   wget https://github.com/rhasspy/piper/releases/latest/download/piper_linux_x86_64.tar.gz")
        print("   tar -xzf piper_linux_x86_64.tar.gz")
        print("   chmod +x piper/piper")
        print("\n3. Or build from source:")
        print("   git clone https://github.com/rhasspy/piper.git")
        print("   cd piper && make")

    def _suggest_model_download(self):
        """Suggest how to download voice models"""
        print("\n🎤 To download voice models:")
        print("1. Visit: https://github.com/rhasspy/piper/releases")
        print("2. Download a voice model (e.g., en_US-lessac-medium.onnx)")
        print("3. Place it in one of these directories:")
        print("   - ./piper/")
        print("   - ~/.local/share/piper/")
        print("   - /usr/share/piper/")
        print("\nPopular English models:")
        print("   - en_US-lessac-medium.onnx (clear female voice)")
        print("   - en_US-danny-low.onnx (male voice, smaller file)")
        print("   - en_US-amy-medium.onnx (female voice)")

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
                # Use pipe for input to avoid encoding issues
                process = subprocess.Popen(
                    [
                        self.piper_exe,
                        '--model', self.piper_model,
                        '--output_file', audio_file_path
                    ],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                stdout, stderr = process.communicate(input=clean_text, timeout=30)

                if process.returncode != 0:
                    print(f"❌ Piper TTS error: {stderr}")
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
        """Play audio file using aplay (Linux) or afplay (macOS)"""
        try:
            if not os.path.exists(audio_file_path):
                print(f"❌ Audio file not found: {audio_file_path}")
                return False

            # Stop any currently playing audio
            self.stop_audio()

            # Use appropriate player based on platform
            if platform.system() == 'Linux':
                self.current_audio_process = subprocess.Popen(['aplay', audio_file_path])
            elif platform.system() == 'Darwin':  # macOS
                self.current_audio_process = subprocess.Popen(['afplay', audio_file_path])
            else:
                print("❌ Unsupported platform for audio playback")
                return False

            return True

        except Exception as e:
            print(f"❌ Error playing audio: {e}")
            return False

    def stop_audio(self):
        """Stop any currently playing audio"""
        if self.current_audio_process:
            try:
                self.current_audio_process.terminate()
                self.current_audio_process = None
            except Exception as e:
                print(f"❌ Error stopping audio: {e}")

    def set_volume(self, volume: float):
        """Set system volume (not implemented)"""
        print("⚠️ Volume control not implemented in this version")

    def pause_audio(self):
        """Pause audio playback (not implemented)"""
        print("⚠️ Audio pause not implemented in this version")

    def unpause_audio(self):
        """Unpause audio playback (not implemented)"""
        print("⚠️ Audio unpause not implemented in this version")

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
            if not self.piper_exe:
                print("❌ Piper executable not found")
                return False

            if not self.piper_model:
                print("❌ No Piper model available")
                return False

            print("✅ Piper TTS detected")
            print(f"Executable: {self.piper_exe}")
            print(f"Model: {os.path.basename(self.piper_model)}")

            test_text = "Piper TTS test successful! This is working on Linux."
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
        print(f"Platform: {platform.system()} {platform.release()}")

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

    def check_system_requirements(self):
        """Check Linux system requirements and suggest fixes"""
        print("\n=== System Check ===")
        print(f"Platform: {platform.system()} {platform.release()}")
        
        # Check audio system
        try:
            result = subprocess.run(['pulseaudio', '--check'], capture_output=True)
            if result.returncode == 0:
                print("✅ PulseAudio is running")
            else:
                print("⚠️ PulseAudio might not be running")
        except FileNotFoundError:
            print("⚠️ PulseAudio not found, checking ALSA...")
            try:
                result = subprocess.run(['aplay', '-l'], capture_output=True)
                if result.returncode == 0:
                    print("✅ ALSA detected")
                else:
                    print("❌ No audio system detected")
            except FileNotFoundError:
                print("❌ No audio system found")

        # Check dependencies
        required_packages = ['pygame', 'soundfile', 'numpy']
        for package in required_packages:
            try:
                __import__(package)
                print(f"✅ {package} installed")
            except ImportError:
                print(f"❌ {package} not installed - run: pip install {package}")

    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        except:
            pass


# Example usage and testing
if __name__ == "__main__":
    tts = TextToSpeech()
    
    # Run system check
    tts.check_system_requirements()
    
    # Test the system
    tts.test_speech()
    
    # Test speech extraction
    tts.test_speech_extraction()
    
    # Example usage
    test_text = "🗣️ 'Hello from Linux! This is a test of the text-to-speech system.'"
    print(f"\nTesting with: {test_text}")
    tts.speak(test_text)