import os
import io
import tempfile
import platform
import sounddevice as sd
import soundfile as sf
import numpy as np
import subprocess
from typing import Optional, List, Tuple
import time
import threading
import re


class TextToSpeech:
    def __init__(self):
        self.vb_audio_device_id = None
        self.default_device_id = None
        self.sample_rate = 22050
        self.vb_audio_found = False

        # PiperTTS configuration
        self.piper_exe = os.path.join("piper", "piper.exe")
        self.piper_model = None
        self.available_models = []

        self.initialize_audio_devices()
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

    def initialize_audio_devices(self):
        """Initialize and configure audio devices"""
        try:
            devices = sd.query_devices()
            self.default_device_id = sd.default.device[1]

            print("Available Audio Devices:")
            for i, device in enumerate(devices):
                if device['max_output_channels'] > 0:
                    device_name = device['name'].lower()
                    print(f"  {i}: {device['name']} (Outputs: {device['max_output_channels']})")

                    if any(keyword in device_name for keyword in ['vb-audio', 'virtual cable', 'cable input']):
                        self.vb_audio_device_id = i
                        self.vb_audio_found = True
                        print(f"    ✅ VB-Audio Virtual Cable found!")

            if self.vb_audio_found:
                print(f"\n🎵 VB-Audio Virtual Cable will be used (Device ID: {self.vb_audio_device_id})")
            else:
                print(f"\n🔊 Using default audio device (Device ID: {self.default_device_id})")
                print("💡 Install VB-Audio Virtual Cable for streaming audio to applications")

        except Exception as e:
            print(f"Error initializing audio devices: {e}")
            self.default_device_id = None

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

    def get_available_devices(self) -> List[Tuple[int, str, int]]:
        """Get list of available output audio devices"""
        devices = []
        try:
            device_list = sd.query_devices()
            for i, device in enumerate(device_list):
                if device['max_output_channels'] > 0:
                    devices.append((i, device['name'], device['max_output_channels']))
        except Exception as e:
            print(f"Error getting audio devices: {e}")
        return devices

    def set_output_device(self, device_id: Optional[int] = None):
        """Set the output audio device"""
        if device_id is not None:
            try:
                device_info = sd.query_devices(device_id)
                if device_info['max_output_channels'] > 0:
                    self.vb_audio_device_id = device_id
                    print(f"Output device set to: {device_info['name']}")
                    return True
                else:
                    print("Selected device has no output channels")
                    return False
            except Exception as e:
                print(f"Error setting output device: {e}")
                return False
        return False

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

    def generate_speech_audio(self, text: str) -> Optional[Tuple[np.ndarray, int]]:
        """Generate speech audio using PiperTTS"""
        try:
            if not self.piper_model or not os.path.exists(self.piper_model):
                print("❌ No valid Piper model available")
                return None

            clean_text = self._clean_text_for_speech(text)

            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as text_file:
                text_file.write(clean_text)
                text_file_path = text_file.name

            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as audio_file:
                audio_file_path = audio_file.name

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
                    audio_data, sample_rate = sf.read(audio_file_path)
                    return audio_data, sample_rate
                else:
                    print("❌ Piper did not generate audio file")
                    return None

            finally:
                try:
                    os.unlink(text_file_path)
                except:
                    pass
                try:
                    os.unlink(audio_file_path)
                except:
                    pass

        except subprocess.TimeoutExpired:
            print("❌ Piper TTS timeout")
            return None
        except Exception as e:
            print(f"❌ Error generating speech with Piper: {e}")
            return None

    def play_audio(self, audio_data: np.ndarray, sample_rate: int, device_id: Optional[int] = None):
        """Play audio through specified device"""
        try:
            output_device = device_id or self.vb_audio_device_id or self.default_device_id

            if output_device is not None:
                device_info = sd.query_devices(output_device)
                device_name = device_info['name']

                if self.vb_audio_found and output_device == self.vb_audio_device_id:
                    print("🎵 Playing through VB-Audio Virtual Cable...")
                else:
                    print(f"🔊 Playing through: {device_name}")
            else:
                print("🔊 Playing through default device...")

            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)

            if np.max(np.abs(audio_data)) > 0:
                audio_data = audio_data / np.max(np.abs(audio_data)) * 0.8

            sd.play(audio_data, samplerate=sample_rate, device=output_device)
            sd.wait()

        except Exception as e:
            print(f"Error playing audio: {e}")
            try:
                sd.play(audio_data, samplerate=sample_rate)
                sd.wait()
            except Exception as e2:
                print(f"Fallback audio playback also failed: {e2}")

    def speak(self, text: str):
        """Convert text to speech and play it - now with speech filtering"""
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

            # Generate audio from extracted speech
            audio_result = self.generate_speech_audio(speech_content)
            if audio_result is None:
                print("Failed to generate speech audio")
                return

            audio_data, sample_rate = audio_result
            self.play_audio(audio_data, sample_rate)

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

    # ... (rest of the methods remain the same as in your original code)

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

            audio_result = self.generate_speech_audio(test_text)
            if audio_result:
                audio_data, sample_rate = audio_result
                self.play_audio(audio_data, sample_rate)
                return True
            else:
                print("❌ Failed to generate test audio")
                return False

        except Exception as e:
            print(f"❌ Piper test failed: {e}")
            return False

    def stop_audio(self):
        """Stop current audio playback"""
        try:
            sd.stop()
            print("🛑 Audio playback stopped")
        except Exception as e:
            print(f"Error stopping audio: {e}")

    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            sd.stop()
        except:
            pass