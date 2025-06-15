import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
# Add Live2D model path
LIVE2D_MODEL_PATH = os.getenv("LIVE2D_MODEL_PATH", "models/noir_model")  # Default path

if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY environment variable is required")

if not ELEVENLABS_API_KEY:
    print("Warning: ELEVENLABS_API_KEY not found. TTS features will be disabled.")