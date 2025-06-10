import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
# Add Live2D model path
LIVE2D_MODEL_PATH = os.getenv("LIVE2D_MODEL_PATH", "models/noir_model")  # Default path

if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY environment variable is required")