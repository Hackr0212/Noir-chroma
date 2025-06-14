import streamlit as st

# Optional: For speech-to-text, use streamlit_webrtc if available
try:
    from streamlit_webrtc import webrtc_streamer, AudioProcessorBase
    import queue
    import av
    import speech_recognition as sr
    WEBSPEECH_AVAILABLE = True
except ImportError:
    WEBSPEECH_AVAILABLE = False

st.set_page_config(page_title="Noir-chroma GUI", layout="centered")
st.title("Noir-chroma: Voice & Text Input Demo")

st.write("You can enter text or use your microphone to input speech.")

# --- Text Input ---
text_input = st.text_input("Type your message:")
if st.button("Submit Text"):
    st.success(f"Text input: {text_input}")
    # TODO: Integrate with AI/processing logic here

# --- Speech-to-Text Input ---
if WEBSPEECH_AVAILABLE:
    st.write("Or, speak into your microphone:")
    class AudioProcessor(AudioProcessorBase):
        def __init__(self):
            self.q = queue.Queue()
            self.recognizer = sr.Recognizer()
            self.audio_data = b""
        def recv(self, frame):
            audio = frame.to_ndarray()
            self.audio_data += audio.tobytes()
            return frame
        def get_text(self):
            if self.audio_data:
                audio = sr.AudioData(self.audio_data, 16000, 2)
                try:
                    return self.recognizer.recognize_google(audio)
                except Exception as e:
                    return f"Recognition error: {e}"
            return ""
    ctx = webrtc_streamer(key="speech-to-text", audio_processor_factory=AudioProcessor, media_stream_constraints={"audio": True, "video": False})
    if hasattr(ctx.state, "audio_processor") and ctx.state.audio_processor is not None:
        if st.button("Transcribe Speech"):
            text = ctx.state.audio_processor.get_text()
            st.success(f"Speech input: {text}")
            # TODO: Integrate with AI/processing logic here
else:
    st.warning("Speech-to-text not available. Install streamlit_webrtc and speech_recognition for this feature.")

# --- Future Integration Points ---
# - Integrate AI response logic here
# - Add Live2D/avatar display in Streamlit if desired
# - Add more advanced UI features as needed
