An AI AGENT that create with deepseek api and use Lancgchain and chroma for RAG Memory

# Features

- uses Lancgchain and chroma for RAG Memory
- uses deepseek api for generating text
- **NEW: ElevenLabs TTS integration for high-quality voice synthesis**
- has a simple command line interface
- has a simple web interface with voice input/output
- Live2D avatar support (optional)

# Installation

1. Install the required packages: `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill in your API keys:
   - `DEEPSEEK_API_KEY`: your deepseek api key
   - `ELEVENLABS_API_KEY`: your ElevenLabs API key (for TTS)
   - `GROQ_API_KEY`: your Groq API key (for speech recognition)
3. Run the agent: `python main.py`

# Usage

You can interact with the agent by:
- **Text**: Type messages in the web interface
- **Voice**: Click the microphone button to speak (auto-transcribed)
- **Audio Output**: Noir will speak responses using ElevenLabs TTS

The web interface is available at `http://localhost:7860` when you run `python main.py`.

## Voice Features

- **Text-to-Speech**: Noir's responses are automatically converted to speech using ElevenLabs
- **Voice Selection**: Choose from available ElevenLabs voices in the interface
- **Speech Recognition**: Speak to Noir using the microphone input
- **Test Voice**: Try different voices with the test button

# Configuration

You can configure the agent by setting the following environment variables:

- `DEEPSEEK_API_KEY`: your deepseek api key (required)
- `ELEVENLABS_API_KEY`: your ElevenLabs API key (optional, enables TTS)
- `GROQ_API_KEY`: your Groq API key (optional, for speech recognition)
- `LIVE2D_MODEL_PATH`: the path to the live2d model
- `CHROMA_DB_PATH`: the path to the chroma db

You can also configure the agent by modifying the `config.py` file.

## ElevenLabs Setup

1. Sign up at [ElevenLabs](https://elevenlabs.io/)
2. Get your API key from the dashboard
3. Add it to your `.env` file as `ELEVENLABS_API_KEY`
4. The system will automatically detect available voices

## Testing TTS

Run the TTS test script:
```bash
python elevenlabs_tts.py
```

This will:
- List all available voices
- Test speech generation
- Play a sample audio

# Character

Noir is a chaotic VTuber who pretends to be a '100% real dolphin' but is obviously a mutated shark. The character responds in a specific format with thoughts, actions, and dialogue, complete with broken English-Russian and shark gaslighting.

# License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.