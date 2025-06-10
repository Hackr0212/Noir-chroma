# live2d_integration.py
import threading
import time
import queue
from typing import Optional
from live2d_avatar import Live2DAvatar
import config


class VTuberAvatarManager:
    """
    Manages the Live2D avatar integration with the VTuber chat system
    """

    def __init__(self):
        self.avatar: Optional[Live2DAvatar] = None
        self.avatar_thread: Optional[threading.Thread] = None
        self.response_queue = queue.Queue()
        self.is_running = False

        # Get model path from config
        self.model_path = getattr(config, 'LIVE2D_MODEL_PATH', 'models/noir_model')

    def initialize_avatar(self, window_size=(800, 600)) -> bool:
        """Initialize the Live2D avatar"""
        try:
            print(f"🎭 Initializing Live2D avatar from: {self.model_path}")

            self.avatar = Live2DAvatar(
                model_path=self.model_path,
                window_size=window_size
            )

            if self.avatar.initialize():
                print("✅ Live2D avatar initialized successfully")
                return True
            else:
                print("❌ Failed to initialize Live2D avatar")
                self.avatar = None
                return False

        except Exception as e:
            print(f"❌ Error initializing avatar: {e}")
            return False

    def start_avatar_display(self):
        """Start the avatar display in a separate thread"""
        if not self.avatar:
            print("❌ Avatar not initialized")
            return False

        if self.avatar_thread and self.avatar_thread.is_alive():
            print("⚠️ Avatar display already running")
            return True

        self.is_running = True

        def avatar_thread_func():
            """Avatar display thread function"""
            try:
                # Start response processing thread
                response_processor = threading.Thread(
                    target=self._process_responses,
                    daemon=True
                )
                response_processor.start()

                # Run main avatar display loop
                self.avatar.run_display_loop()

            except Exception as e:
                print(f"❌ Avatar thread error: {e}")
            finally:
                self.is_running = False

        self.avatar_thread = threading.Thread(target=avatar_thread_func, daemon=True)
        self.avatar_thread.start()

        print("🎬 Live2D avatar display started")
        return True

    def _process_responses(self):
        """Process queued AI responses for avatar reactions"""
        while self.is_running:
            try:
                # Wait for response with timeout
                response = self.response_queue.get(timeout=1.0)

                if response and self.avatar:
                    print(f"🎭 Processing avatar response: {response[:50]}...")
                    self.avatar.handle_response(response)

                self.response_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                print(f"⚠️ Response processing error: {e}")

    def queue_response(self, response_text: str):
        """Queue an AI response for avatar processing"""
        if self.is_running and self.avatar:
            try:
                self.response_queue.put(response_text, block=False)
            except queue.Full:
                print("⚠️ Avatar response queue full, skipping response")
        else:
            print("⚠️ Avatar not running, cannot queue response")

    def update_mouse_position(self, x: int, y: int):
        """Update avatar eye tracking with mouse position"""
        if self.avatar:
            self.avatar.update_mouse_tracking((x, y))

    def set_avatar_emotion(self, emotion: str, intensity: float = 1.0):
        """Manually set avatar emotion"""
        if self.avatar:
            self.avatar.set_expression(emotion, intensity)

    def start_lip_sync(self, text: str):
        """Start lip sync for speech"""
        if self.avatar:
            self.avatar.start_lip_sync(text)

    def stop_lip_sync(self):
        """Stop lip sync"""
        if self.avatar:
            self.avatar.stop_lip_sync()

    def is_avatar_ready(self) -> bool:
        """Check if avatar is ready and running"""
        return (self.avatar is not None and
                self.is_running and
                self.avatar_thread is not None and
                self.avatar_thread.is_alive())

    def shutdown(self):
        """Shutdown the avatar system"""
        print("🛑 Shutting down Live2D avatar...")

        self.is_running = False

        if self.avatar:
            self.avatar.cleanup()

        if self.avatar_thread and self.avatar_thread.is_alive():
            self.avatar_thread.join(timeout=2.0)

        print("✅ Live2D avatar shutdown complete")


# Global avatar manager instance
avatar_manager = VTuberAvatarManager()


def initialize_live2d_avatar(window_size=(800, 600)) -> bool:
    """Initialize the Live2D avatar system"""
    return avatar_manager.initialize_avatar(window_size)


def start_live2d_display():
    """Start the Live2D avatar display"""
    return avatar_manager.start_avatar_display()


def handle_ai_response(response_text: str):
    """Handle AI response for avatar reactions"""
    avatar_manager.queue_response(response_text)


def update_avatar_mouse_tracking(x: int, y: int):
    """Update avatar eye tracking"""
    avatar_manager.update_mouse_position(x, y)


def set_avatar_emotion(emotion: str, intensity: float = 1.0):
    """Set avatar emotion manually"""
    avatar_manager.set_avatar_emotion(emotion, intensity)


def sync_avatar_speech(text: str):
    """Sync avatar lip movement with speech"""
    avatar_manager.start_lip_sync(text)


def is_avatar_running() -> bool:
    """Check if avatar is running"""
    return avatar_manager.is_avatar_ready()


def shutdown_avatar():
    """Shutdown avatar system"""
    avatar_manager.shutdown()


# Integration helper functions
def get_avatar_status() -> dict:
    """Get current avatar status"""
    return {
        'initialized': avatar_manager.avatar is not None,
        'running': avatar_manager.is_running,
        'model_path': avatar_manager.model_path,
        'thread_alive': (avatar_manager.avatar_thread.is_alive()
                         if avatar_manager.avatar_thread else False)
    }