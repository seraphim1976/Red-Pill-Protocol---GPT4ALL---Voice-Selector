import streamlit as st
from streamlit_mic_recorder import mic_recorder, speech_to_text

st.title("Mic test")
text = speech_to_text(
    language='ca',
    start_prompt="Parlador! 🎤",
    stop_prompt="Parant...",
    just_once=True,
    use_container_width=True,
    callback=None,
    args=(),
    kwargs={},
    key='STT'
)
if text:
    st.write("Has dit:", text)
