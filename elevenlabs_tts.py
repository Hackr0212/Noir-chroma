import os
import io
import pygame
import requests
from typing import Optional, Generator
from config import ELEVENLABS_API_KEY

class ElevenLabsTTS:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize ElevenLabs TTS client"""
        self.api_key = api_key or ELEVENLABS_API_KEY
        self.base_url = "https://api.elevenlabs.io/v1"
        
        if not self.api_key:
            raise ValueError("ElevenLabs API key is required")
        
        # Initialize pygame mixer for audio playback
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        
        # Default voice settings - you can customize these
        self.voice_settings = {
            "stability": 0.75,
            "similarity_boost": 0.75,
            "style": 0.5,
            "use_speaker_boost": True
        }
        
        # Cache available voices
        self._voices = None
    
    def get_voices(self) -> dict:
        """Get available voices from ElevenLabs"""
        if self._voices is not None:
            return self._voices
            
        try:
            headers = {"xi-api-key": self.api_key}
            response = requests.get(f"{self.base_url}/voices", headers=headers)
            response.raise_for_status()
            
            voices_data = response.json()
            self._voices = {voice["name"]: voice["voice_id"] for voice in voices_data["voices"]}
            
            print(f"✅ Found {len(self._voices)} available voices")
            return self._voices
            
        except Exception as e:
            print(f"❌ Error fetching voices: {e}")
            return {}
    
    def list_voices(self):
        """Print available voices"""
        voices = self.get_voices()
        if voices:
            print("\n🎤 Available ElevenLabs Voices:")
            for name, voice_id in voices.items():
                print(f"  - {name} (ID: {voice_id})")
        else:
            print("❌ No voices available")
    
    def generate_speech(self, text: str, voice_name: str = "Rachel", save_path: Optional[str] = None) -> Optional[bytes]:
        """Generate speech from text using ElevenLabs API"""
        try:
            voices = self.get_voices()
            
            if voice_name not in voices:
                print(f"❌ Voice '{voice_name}' not found. Available voices: {list(voices.keys())}")
                return None
            
            voice_id = voices[voice_name]
            
            # Prepare the request
            url = f"{self.base_url}/text-to-speech/{voice_id}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            data = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": self.voice_settings
            }
            
            print(f"🎵 Generating speech for: '{text[:50]}...' using voice '{voice_name}'")
            
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            
            audio_data = response.content
            
            # Save to file if path provided
            if save_path:
                with open(save_path, "wb") as f:
                    f.write(audio_data)
                print(f"💾 Audio saved to: {save_path}")
            
            return audio_data
            
        except Exception as e:
            print(f"❌ Error generating speech: {e}")
            return None
    
    def play_audio(self, audio_data: bytes):
        """Play audio data using pygame"""
        try:
            # Create a file-like object from bytes
            audio_file = io.BytesIO(audio_data)
            
            # Load and play the audio
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            
            # Wait for playback to finish
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
                
            print("🔊 Audio playback completed")
            
        except Exception as e:
            print(f"❌ Error playing audio: {e}")
    
    def speak(self, text: str, voice_name: str = "Rachel", save_path: Optional[str] = None) -> bool:
        """Generate and play speech from text"""
        try:
            audio_data = self.generate_speech(text, voice_name, save_path)
            
            if audio_data:
                self.play_audio(audio_data)
                return True
            else:
                return False
                
        except Exception as e:
            print(f"❌ Error in speak method: {e}")
            return False
    
    def stream_speech(self, text: str, voice_name: str = "Rachel") -> Generator[bytes, None, None]:
        """Stream speech generation (for real-time applications)"""
        try:
            voices = self.get_voices()
            
            if voice_name not in voices:
                print(f"❌ Voice '{voice_name}' not found")
                return
            
            voice_id = voices[voice_name]
            
            url = f"{self.base_url}/text-to-speech/{voice_id}/stream"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            data = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": self.voice_settings
            }
            
            with requests.post(url, json=data, headers=headers, stream=True) as response:
                response.raise_for_status()
                
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        yield chunk
                        
        except Exception as e:
            print(f"❌ Error streaming speech: {e}")
    
    def set_voice_settings(self, stability: float = 0.75, similarity_boost: float = 0.75, 
                          style: float = 0.5, use_speaker_boost: bool = True):
        """Update voice settings"""
        self.voice_settings = {
            "stability": max(0.0, min(1.0, stability)),
            "similarity_boost": max(0.0, min(1.0, similarity_boost)),
            "style": max(0.0, min(1.0, style)),
            "use_speaker_boost": use_speaker_boost
        }
        print(f"🎛️ Voice settings updated: {self.voice_settings}")

# Utility function for easy usage
def create_tts_client() -> Optional[ElevenLabsTTS]:
    """Create TTS client if API key is available"""
    try:
        if ELEVENLABS_API_KEY:
            return ElevenLabsTTS()
        else:
            print("⚠️ ElevenLabs API key not found. TTS disabled.")
            return None
    except Exception as e:
        print(f"❌ Failed to create TTS client: {e}")
        return None

# Test function
def test_tts():
    """Test the TTS functionality"""
    try:
        tts = create_tts_client()
        if tts:
            print("🧪 Testing ElevenLabs TTS...")
            
            # List available voices
            tts.list_voices()
            
            # Test speech generation
            test_text = "🧠 *This is a test of Noir's voice synthesis!* 🎬 *waves fin excitedly* 🗣️ 'Glub glub! I am totally real dolphin, not suspicious shark at all! 🐬✨'"
            
            success = tts.speak(test_text, voice_name="Rachel")
            
            if success:
                print("✅ TTS test completed successfully!")
            else:
                print("❌ TTS test failed")
        else:
            print("❌ TTS client not available")
            
    except Exception as e:
        print(f"❌ TTS test error: {e}")

if __name__ == "__main__":
    test_tts()