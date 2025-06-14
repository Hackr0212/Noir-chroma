import speech_recognition as sr
import threading
import time
from typing import Optional
import platform


class SpeechRecognizer:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        
        # Linux-specific microphone settings
        if platform.system() == 'Linux':
            try:
                # Try to find the default microphone
                self.microphone = sr.Microphone()
                # Adjust settings for Linux
                self.recognizer.energy_threshold = 300  # Lower threshold for Linux
                self.recognizer.dynamic_energy_threshold = True
                self.recognizer.pause_threshold = 0.8
                self.recognizer.operation_timeout = None
                print("✅ Microphone initialized for Linux")
            except Exception as e:
                print(f"❌ Error initializing microphone: {e}")
                print("Please ensure you have a working microphone and proper permissions")
                print("For Arch Linux, install required packages:")
                print("   sudo pacman -S portaudio python-pyaudio")
                print("   sudo pacman -S alsa-utils")
                raise
        else:
            self.microphone = sr.Microphone()
            self.recognizer.energy_threshold = 400
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 0.8
            self.recognizer.operation_timeout = None

        self.is_listening = False
        self.voice_detected = False
        self.speech_thread = None

        # Voice activity detection settings
        self.voice_detection_timeout = 0.1  # Check every 100ms
        self.silence_timeout = 2.0  # Stop listening after 2 seconds of silence

    def listen_with_voice_detection(self) -> Optional[str]:
        """Listen for speech with voice activity detection"""
        print("🎤 Listening for voice... (or press Enter to type)")

        # Start voice activity detection in background
        self.voice_detected = False
        self.is_listening = True

        # Create a thread for voice detection
        detection_thread = threading.Thread(target=self._voice_activity_detection)
        detection_thread.daemon = True
        detection_thread.start()

        # Wait for voice detection or user input
        start_time = time.time()
        while self.is_listening and not self.voice_detected:
            time.sleep(0.1)
            # Timeout after 30 seconds if no voice detected
            if time.time() - start_time > 30:
                self.is_listening = False
                break

        if self.voice_detected:
            print("🗣️ Voice detected! Processing speech...")
            return self._capture_speech()
        else:
            self.is_listening = False
            return None

    def _voice_activity_detection(self):
        """Background thread for detecting voice activity"""
        try:
            with self.microphone as source:
                # Quick ambient noise adjustment
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)

            while self.is_listening and not self.voice_detected:
                try:
                    with self.microphone as source:
                        # Listen for very short audio chunks to detect voice
                        audio = self.recognizer.listen(
                            source,
                            timeout=self.voice_detection_timeout,
                            phrase_time_limit=0.5
                        )

                        # If we captured audio, check if it's above energy threshold
                        if len(audio.frame_data) > 0:
                            # Voice detected - signal main thread
                            self.voice_detected = True
                            break

                except sr.WaitTimeoutError:
                    # No audio in this time slice, continue monitoring
                    continue
                except Exception:
                    # Any other error, stop detection
                    break

        except Exception as e:
            print(f"Voice detection error: {e}")
            self.is_listening = False

    def _capture_speech(self) -> Optional[str]:
        """Capture and recognize speech after voice is detected"""
        try:
            with self.microphone as source:
                # Listen for the full speech
                audio = self.recognizer.listen(
                    source,
                    timeout=1,  # Quick timeout since we know voice is there
                    phrase_time_limit=15
                )

            print("🔄 Processing speech...")
            recognized_text = self.recognizer.recognize_google(audio)
            print(f"✅ You said: {recognized_text}")
            return recognized_text

        except sr.UnknownValueError:
            print("❌ Sorry, I couldn't understand the audio. Please try again.")
            return None
        except sr.RequestError as e:
            print(f"❌ Error with speech recognition service: {e}")
            return None
        except sr.WaitTimeoutError:
            print("⏱️ Speech timeout. Please try again.")
            return None
        except Exception as e:
            print(f"❌ Unexpected error during speech recognition: {e}")
            return None

    def listen(self, timeout: int = 10, phrase_time_limit: int = 15) -> Optional[str]:
        """Original listen method for backward compatibility"""
        try:
            print("Adjusting for ambient noise... Please wait.")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=2)

            print("Listening... Speak now!")
            with self.microphone as source:
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )

            print("Processing speech...")
            recognized_text = self.recognizer.recognize_google(audio)
            print(f"You said: {recognized_text}")
            return recognized_text

        except sr.UnknownValueError:
            print("Sorry, I couldn't understand the audio. Please try again.")
            return None
        except sr.RequestError as e:
            print(f"Error with speech recognition service: {e}")
            return None
        except sr.WaitTimeoutError:
            print("Listening timeout. No speech detected.")
            return None
        except Exception as e:
            print(f"Unexpected error during speech recognition: {e}")
            return None

    def test_microphone(self) -> bool:
        """Test if microphone is working"""
        try:
            print("Testing microphone...")
            with self.microphone as source:
                print("Adjusting for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
                # Try to capture a small audio sample
                print("Capturing test audio...")
                audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=1)
                
                if len(audio.frame_data) > 0:
                    print("✅ Microphone test successful!")
                    return True
                else:
                    print("❌ No audio data captured")
                    return False
                    
        except Exception as e:
            print(f"❌ Microphone test failed: {e}")
            if platform.system() == 'Linux':
                print("\nTroubleshooting steps for Arch Linux:")
                print("1. Check if microphone is detected:")
                print("   arecord -l")
                print("   # or")
                print("   pactl list sources")
                print("2. Check if you have proper permissions:")
                print("   sudo usermod -a -G audio $USER")
                print("3. Install required packages:")
                print("   sudo pacman -S portaudio python-pyaudio")
                print("   sudo pacman -S alsa-utils")
                print("4. Check if PulseAudio is running:")
                print("   systemctl --user status pulseaudio")
                print("5. If PulseAudio is not running:")
                print("   systemctl --user start pulseaudio")
            return False

    def stop_listening(self):
        """Stop voice activity detection"""
        self.is_listening = False