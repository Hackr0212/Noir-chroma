"""
LangChain Expression Language + LangSmith setup for Noir-chroma project.
This script sets up LangSmith tracing and provides a helper to wrap chains for tracing.
"""
import os
from langchain_core.tracers import LangChainTracer
from langsmith import Client

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # If dotenv isn't installed, skip loading .env

# Get LangSmith API key from environment or .env
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
if not LANGSMITH_API_KEY:
    raise ValueError("LangSmith API key not found. Set LANGSMITH_API_KEY in your environment.")

# Optionally set LangSmith project name
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "Noir-chroma")

# Initialize LangSmith client
client = Client(api_key=LANGSMITH_API_KEY)

# Set up LangChain tracer
tracer = LangChainTracer(client=client)

# Helper: Use tracer with LangChain chains

def trace_chain(chain, session_name=None):
    """
    Attach the LangSmith tracer to a LangChain chain.
    Usage:
        chain = trace_chain(chain)
    Optionally specify a session name (used as run name/project).
    """
    # Most LangChain run methods accept a 'callbacks' argument
    chain.tracer = tracer
    return chain

# Usage Example (in your code):
# result = trace_chain(chain).invoke(input)
# or manually: chain.invoke(input, callbacks=[tracer])
# from langsmith_setup import trace_chain
# chain = trace_chain(chain)
