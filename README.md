An AI AGENT that create with deepseek api and use Lancgchain and chroma for RAG Memory

# Features

- uses Lancgchain and chroma for RAG Memory
- uses deepseek api for generating text
- has a simple command line interface
- has a simple web interface

# Installation

1. Install the required packages: `pip install -r requirements.txt`
2. Set the `DEEPSEEK_API_KEY` environment variable to your deepseek api key
3. Run the agent: `python main.py`

# Usage

You can interact with the agent by sending it messages. The agent will respond with a message.

You can also use the web interface to interact with the agent. The web interface is available at `http://localhost:5000`.

# Configuration

You can configure the agent by setting the following environment variables:

- `DEEPSEEK_API_KEY`: your deepseek api key
- `LIVE2D_MODEL_PATH`: the path to the live2d model
- `CHROMA_DB_PATH`: the path to the chroma db

You can also configure the agent by modifying the `config.py` file.

# License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
