import os
import streamlit as st
import red_pill.config as cfg
from red_pill.memory import MemoryManager
from red_pill.state import get_skin as get_active_skin
from openai import OpenAI
import base64
import requests
import json
import time

# PDF Support Removed per user request
PDF_AVAILABLE = False

# DOCX Support Removed per user request
DOCX_AVAILABLE = False

import io
import re
import asyncio
import edge_tts
from streamlit_mic_recorder import speech_to_text

# -----------------------------------------------------------------------------
# Helper: Neteja text per TTS
# -----------------------------------------------------------------------------
def clean_text_for_tts(text: str) -> str:
    """Elimina elements del markdown i símbols que causen deletreig en gTTS."""
    # Eliminar blocs de codi (``` ... ```)
    text = re.sub(r'```[\s\S]*?```', '', text)
    # Eliminar codi en línia (`codi`)
    text = re.sub(r'`[^`]+`', '', text)
    # Eliminar URLs (http/https/ftp...)
    text = re.sub(r'https?://\S+|www\.\S+|ftp://\S+', '', text)
    # Eliminar emojis i símbols unicode especials
    text = re.sub(r'[\U00010000-\U0010FFFF]', '', text, flags=re.UNICODE)
    text = re.sub(r'[\u2000-\u27FF]', '', text)  # lletres i símbols tècnics
    # Eliminar markdown: ##, **, __, *, _, ~, >, |
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'\*{1,3}|_{1,3}|~~|`', '', text)
    text = re.sub(r'^>+\s?', '', text, flags=re.MULTILINE)
    text = re.sub(r'\|', ' ', text)
    # Eliminar cometes dobles i simples
    text = re.sub(r'["\'\u00AB\u00BB\u201C\u201D\u2018\u2019]', '', text)
    # Substituir guions per espai (evita dir "guionet")
    text = re.sub(r'(?<=\s)-(?=\s)|^-\s', ' ', text, flags=re.MULTILINE)
    text = text.replace('--', ' ')
    # Eliminar línies que semblen codi o estructures (línies que comencen per espais/tabuladors seguits de codi)
    text = re.sub(r'^[ \t]{2,}.+$', '', text, flags=re.MULTILINE)
    # Eliminar caràcters especials restants excepte puntuació bàsica i lletres
    text = re.sub(r'[^\w\s.,;:!?()\-\u00C0-\u024F]', ' ', text)
    # Netejar espais múltiples i línies buides
    text = re.sub(r'\n{2,}', ' ', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

# -----------------------------------------------------------------------------
# Image Generation Fallback: Free Fast API
# -----------------------------------------------------------------------------
def generate_image_free(prompt: str, status=None) -> bytes:
    """Generates an image using Hugging Face (tries multiple models as fallback)."""
    hf_key = cfg.HF_API_KEY
    if not hf_key:
        if status: status.error("VISUAL CORTEX OFFLINE: Falta HF_API_KEY al fitxer .env")
        return None
    
    models = [
        "black-forest-labs/FLUX.1-schnell",
        "stabilityai/sdxl-turbo",
        "stabilityai/stable-diffusion-xl-base-1.0",
        "runwayml/stable-diffusion-v1-5",
        "Lykon/DreamShaper",
        "prompthero/openjourney"
    ]
    
    headers = {
        "Authorization": f"Bearer {hf_key}",
        "Content-Type": "application/json",
    }
    payload = {"inputs": prompt}
    
    for model in models:
        api_url = f"https://router.huggingface.co/hf-inference/models/{model}"
        if status: status.write(f"BUNKER: Attempting Visual Engram with {model}...")
        
        # Retry logic for model loading (503)
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                print(f"BUNKER: Attempting Visual Engram with {model} (Attempt {attempt+1}/{max_retries})...")
                response = requests.post(api_url, headers=headers, json=payload, timeout=60)
                
                if response.status_code == 200:
                    print(f"BUNKER: Visual Engram generated successfully with {model}.")
                    if status: status.write(f"✅ Success with {model}")
                    return response.content
                
                elif response.status_code == 401:
                    print(f"BUNKER: HF Error 401: Invalid API Key.")
                    if status: status.error(f"❌ HF Error 401: Clau API no vàlida. Revisa el teu .env")
                    return None # Stop trying other models for 401
                
                elif response.status_code == 503:
                    try:
                        error_data = response.json()
                        wait_time = error_data.get("estimated_time", retry_delay)
                        print(f"BUNKER: Model {model} is loading. Waiting {wait_time:.1f}s...")
                        if status: status.write(f"⏳ {model} is loading. Waiting {wait_time:.1f}s...")
                        time.sleep(min(wait_time, 20))
                    except:
                        time.sleep(retry_delay)
                    continue
                
                else:
                    print(f"BUNKER: Model {model} failed with status {response.status_code}: {response.text[:100]}")
                    if status: status.write(f"⚠️ {model} failed (Status {response.status_code})")
                    break
                    
            except Exception as e:
                print(f"BUNKER: Error with model {model}: {e}")
                if status: status.write(f"⚠️ Error with {model}: {e}")
                break
            
    print("BUNKER: All visual fallback models failed.")
    if status: status.write("❌ All HF models failed.")
    return None



# -----------------------------------------------------------------------------
# Configuration & Customization
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Red Pill Protocol",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="expanded",
)
# -----------------------------------------------------------------------------
# Custom CSS - The Matrix / Cyberpunk Aesthetic
# -----------------------------------------------------------------------------
def get_base_css():
    # Common base styles
    base_css = """
    /* Main Background */
    .stApp {
        font-family: 'Courier New', Courier, monospace;
    }
    
    /* Inputs */
    .stTextInput > div > div > input {
        border-radius: 0px;
    }
    
    /* Chat Messages */
    .stChatMessage {
        background-color: transparent;
        border: none;
    }

    /* Fix Bottom Input Background */
    .stBottom {
        background-color: transparent !important;
    }
    .stChatInputContainer {
        padding-bottom: 20px;
    }
    """
    
    return base_css







def get_css(skin):
    # Common base styles
    base_css = get_base_css()
    
    if skin == "cyberpunk":
        # CYBERPUNK THEME (Neon Pink/Cyan/Yellow + Dark)
        theme_css = """
        .stApp {
            background-color: #050510;
            color: #00ffff;
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] {
            background-color: #0a0a1a;
            border-right: 1px solid #ff00ff;
        }

        /* Header Bar */
        header[data-testid="stHeader"] {
            background-color: transparent;
        }
        
        /* Headers */
        h1, h2, h3 {
            color: #ff00ff !important;
            text-transform: uppercase;
            letter-spacing: 2px;
            text-shadow: 0px 0px 5px rgba(255, 0, 255, 0.7);
        }
        
        /* Inputs (Standard) */
        .stTextInput > div > div > input {
            background-color: #111;
            color: #ffff00;
            border: 1px solid #00ffff;
        }
        
        /* Chat Input (Bottom) - User requested WHITE background */
        .stChatInput textarea, .stChatInput input {
            background-color: #ffffff !important;
            color: #000000 !important;
            border: 1px solid #ff00ff !important;
        }
        .stChatInput [data-testid="stChatInputSubmitButton"] {
            background-color: transparent !important;
            color: #ff00ff !important;
        }
        
        /* User Message Bubble */
        [data-testid="stChatMessage"]:nth-child(odd) {
            background-color: #1a1a2e;
            border-left: 3px solid #ffff00; /* Neon Yellow */
            border-radius: 5px;
            padding: 1rem;
            margin-bottom: 10px;
        }
        
        /* Assistant Message Bubble */
        [data-testid="stChatMessage"]:nth-child(even) {
            background-color: #1a051a;
            border-left: 3px solid #ff00ff; /* Neon Pink */
            border-radius: 5px;
            padding: 1rem;
            margin-bottom: 10px;
        }
        
        /* Buttons */
        .stButton > button {
            background-color: #000;
            color: #00ffff;
            border: 1px solid #00ffff;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-radius: 0px;
        }
        .stButton > button:hover {
            background-color: #00ffff;
            color: #000;
            border-color: #ff00ff;
            box-shadow: 0 0 15px #00ffff;
        }
        
        /* Status Containers */
        div[data-testid="stStatusWidget"] {
            background-color: #0a0a1a;
            border: 1px solid #ff00ff;
        }

        /* Toolbars, Action Buttons, and Menus (Fix for Rerun/Print) */
        div[data-testid="stElementToolbar"], 
        [data-testid="stActionButton"],
        [data-testid="stMainMenu"] > button {
            background-color: #050510 !important;
            color: #00ffff !important;
            border: 1px solid #ff00ff !important;
        }
        
        /* Tooltip and Popover backgrounds */
        div[data-testid="stTooltipContent"],
        div[data-baseweb="popover"],
        div[data-baseweb="menu"] {
            background-color: #0a0a1a !important;
            color: #00ffff !important;
            border: 1px solid #ff00ff !important;
        }
        
        /* Menu item text color */
        div[data-baseweb="menu"] li {
            color: #00ffff !important;
        }
        div[data-baseweb="menu"] li:hover {
            background-color: #ff00ff !important;
            color: #000 !important;
        }

        /* HARD OVERRIDES FOR READABILITY */
        p, li, span, div.stMarkdown {
            color: #00ffff !important;
        }
        
        /* Captions / Small text */
        .stCaption, small, div[data-testid="caption"] {
            color: #b0ffff !important; /* Slightly dimmer cyan */
        }

        /* File Uploader - HARD OVERRIDE */
        [data-testid="stFileUploader"] {
            border: 2px dashed #ff00ff !important;
            background-color: #1a051a !important; /* Darker background */
            padding: 15px !important;
            border-radius: 5px;
        }
        [data-testid="stFileUploader"] section {
            background-color: transparent !important;
        }
        [data-testid="stFileUploader"] button {
            border: 1px solid #00ffff !important;
            color: #00ffff !important;
            background-color: #000 !important;
        }
        [data-testid="stFileUploader"] small {
             color: #ff00ff !important;
        }

        /* Header Icons (like the 'Running' man) and Labels */
        header[data-testid="stHeader"] svg {
            fill: #00ffff !important;
        }
        header[data-testid="stHeader"] {
            color: #00ffff !important;
        }
        """
    else:
        # MATRIX THEME (Default)
        theme_css = """
        .stApp {
            background-color: #050505;
            color: #e0e0e0;
        }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background-color: #0a0a0a;
            border-right: 1px solid #333;
        }
        
        /* Header Bar */
        header[data-testid="stHeader"] {
            background-color: transparent;
        }
        
        /* Headers */
        h1, h2, h3 {
            color: #ff4b4b !important;
            text-transform: uppercase;
            letter-spacing: 2px;
            text-shadow: 0px 0px 10px rgba(255, 75, 75, 0.4);
        }
        
        /* Inputs */
        .stTextInput > div > div > input {
            background-color: #111;
            color: #00ff41;
            border: 1px solid #333;
        }
        .stTextInput > div > div > input:focus {
            border-color: #ff4b4b;
            box-shadow: 0 0 10px rgba(255, 75, 75, 0.2);
        }

        /* Chat Input (Bottom) - User requested WHITE background */
        .stChatInput textarea, .stChatInput input {
            background-color: #ffffff !important;
            color: #000000 !important;
            border: 1px solid #ccc !important;
        }
        .stChatInput [data-testid="stChatInputSubmitButton"] {
            color: #000000 !important;
        }
        
        /* User Message Bubble */
        [data-testid="stChatMessage"]:nth-child(odd) {
            background-color: #1a1a1a;
            border-left: 3px solid #00ff41; /* Matrix Green */
            border-radius: 5px;
            padding: 1rem;
            margin-bottom: 10px;
        }
        
        /* Assistant Message Bubble */
        [data-testid="stChatMessage"]:nth-child(even) {
            background-color: #110000;
            border-left: 3px solid #ff4b4b; /* Red Pill Red */
            border-radius: 5px;
            padding: 1rem;
            margin-bottom: 10px;
        }
        
        /* Status Containers */
        div[data-testid="stStatusWidget"] {
            background-color: #111;
            border: 1px solid #333;
        }

        /* Toolbars, Action Buttons, and Menus (Fix for Rerun/Print) */
        div[data-testid="stElementToolbar"], 
        [data-testid="stActionButton"],
        [data-testid="stMainMenu"] > button {
            background-color: #050505 !important;
            color: #ff4b4b !important;
            border: 1px solid #333 !important;
        }

        /* Tooltip and Popover backgrounds */
        div[data-testid="stTooltipContent"],
        div[data-baseweb="popover"],
        div[data-baseweb="menu"] {
            background-color: #111 !important;
            color: #e0e0e0 !important;
            border: 1px solid #333 !important;
        }
        
        /* Menu item text color */
        div[data-baseweb="menu"] li {
            color: #e0e0e0 !important;
        }
        div[data-baseweb="menu"] li:hover {
            background-color: #ff4b4b !important;
            color: #000 !important;
        }

        /* Buttons */
        .stButton > button {
            background-color: #111;
            color: #ff4b4b;
            border: 1px solid #ff4b4b;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .stButton > button:hover {
            background-color: #ff4b4b;
            color: #000;
            border-color: #ff4b4b;
        }
        
        /* HARD OVERRIDES FOR READABILITY */
        p, li, span, div.stMarkdown {
            color: #00ff41 !important; /* Matrix Green for high visibility */
        }
        
        /* Keep headers red */
        h1, h2, h3, h4, h5, h6 {
            color: #ff4b4b !important;
        }
        
        /* Small text slightly dimmer but still visible */
        .stCaption, small, div[data-testid="caption"] {
             color: #00cc33 !important; 
        }

        /* File Uploader */
        [data-testid="stFileUploader"] {
            border: 2px dashed #00ff41;
            background-color: rgba(0, 255, 65, 0.05);
            padding: 10px;
        }
        [data-testid="stFileUploader"] section {
            background-color: transparent !important;
        }
        [data-testid="stFileUploader"] button {
            border: 1px solid #ff4b4b !important;
            color: #ff4b4b !important;
        }
        """
    
    return f"<style>{base_css}\n{theme_css}</style>"

active_skin = get_active_skin()
st.markdown(get_css(active_skin), unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# State Initialization
# -----------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "memory" not in st.session_state:
    try:
        st.session_state.memory_manager = MemoryManager()
        st.session_state.memory_error = None
    except Exception as e:
        st.session_state.memory_manager = None
        st.session_state.memory_error = str(e)

if "client" not in st.session_state or st.session_state.get("force_reconnect"):
    api_key = cfg.OPENAI_API_KEY.strip() if cfg.OPENAI_API_KEY else None
    base_url = cfg.OPENAI_BASE_URL
    
    try:
        if not api_key:
             st.session_state.client = None
             st.session_state.client_error = "Missing OPENAI_API_KEY in .env"
             st.session_state.dalle_client = None
        else:
            st.session_state.client = OpenAI(api_key=api_key, base_url=base_url)
            st.session_state.client_error = None
            
            # --- DALL-E Client (Always connects to real OpenAI) ---
            if api_key.startswith("sk-") and api_key != "dummy":
                st.session_state.dalle_client = OpenAI(api_key=api_key, base_url="https://api.openai.com/v1") 
            else:
                st.session_state.dalle_client = None
                if not api_key.startswith("sk-"):
                    st.session_state.client_error = "VISUAL CORTEX requires an 'sk-' OpenAI key."
            
            # Verify connection AND try to auto-detect model if not explicitly set
            try:
                models_response = st.session_state.client.models.list()
                
                # If LLM_MODEL_NAME is the default or unset, and we have a local server, grab the first model name
                if cfg.LLM_MODEL_NAME == "gpt-3.5-turbo" and cfg.OPENAI_BASE_URL:
                    available_models = models_response.data
                    if available_models:
                        detected_model = available_models[0].id
                        cfg.LLM_MODEL_NAME = detected_model
                        st.info(f"Detected local model: {detected_model}")
            except Exception as model_e:
                st.session_state.client_error = f"Connection error: {model_e}"

    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg:
             error_msg = "401 Unauthorized: Invalid API Key. Ensure OPENAI_API_KEY is correct."
        st.session_state.client = None
        st.session_state.client_error = error_msg
        st.session_state.dalle_client = None
    
    # Reset force flag
    st.session_state.force_reconnect = False

# -----------------------------------------------------------------------------
# Sidebar
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("🔴 SYSTEM STATUS")
    
    st.markdown("---")
    
    # Memory Status
    if st.session_state.memory_manager:
        st.success(f"BUNKER: ONLINE")
        st.caption(f"Path: {cfg.QDRANT_PATH or cfg.QDRANT_URL}")
    else:
        st.error(f"BUNKER: OFFLINE")
        st.error(st.session_state.memory_error)
        
    st.markdown("---")

    # AI Status
    if st.session_state.client:
        model = cfg.LLM_MODEL_NAME
        st.success(f"UPLINK: ACTIVE")
        st.caption(f"Model: {model}")
        if cfg.OPENAI_BASE_URL:
            st.caption(f"Node: {cfg.OPENAI_BASE_URL}")
        
        if st.session_state.dalle_client:
            st.success("VISUAL CORTEX: ONLINE")
        elif cfg.HF_API_KEY:
            st.success("VISUAL CORTEX: ONLINE (HF FREE)")
            st.caption("Using Hugging Face FLUX.1-schnell")
        else:
            st.warning("VISUAL CORTEX: OFFLINE")
            st.caption("Afegeix HF_API_KEY al .env")
            
    else:
        st.error(f"UPLINK: SEVERED")
        if st.session_state.client_error:
            st.caption(f"Error: {st.session_state.client_error}")

    st.markdown("---")
    if st.button("PURGE CACHE (RESET)"):
        st.session_state.messages = []
        st.rerun()

    if st.button("RESET LINKS (FORCE RECONNECT)"):
        st.session_state.force_reconnect = True
        st.rerun()

    st.markdown("---")
    st.markdown("### 🔊 VEU (TTS)")
    
    # Opcions de veu disponibles amb edge-tts (Neurals)
    VOICE_OPTIONS = {
        "👩 🌟💙🟡🔴 Joana (CatalàF)": "ca-ES-JoanaNeural",
        "👨 🌟💙🟡🔴 Enric (CatalàM)": "ca-ES-EnricNeural",
        "👩 🇪🇸 Elvira (CastellàF)": "es-ES-ElviraNeural",
        "👨 🇪🇸 Álvaro (CastellàM)": "es-ES-AlvaroNeural",
        "👩 🇬🇧 Sonia (Anglès UK-F)": "en-GB-SoniaNeural",
        "👨 🇬🇧 Ryan (Anglès UK-M)": "en-GB-RyanNeural",
        "👩 🇺🇸 Ava (Anglès US-F)": "en-US-AvaNeural",
        "👨 🇺🇸 Andrew (Anglès US-M)": "en-US-AndrewNeural",
        "🔇 Silenci (desactivar)": None,
    }
    
    selected_voice_label = st.selectbox(
        "Veu de resposta:",
        options=list(VOICE_OPTIONS.keys()),
        index=0,
        key="tts_voice_selector"
    )
    st.session_state.tts_voice = VOICE_OPTIONS[selected_voice_label]
    st.markdown("---")
    st.markdown("### 📂 DATA INGESTION")
    
    # Determine supported file types
    supported_types = ['txt', 'md', 'py', 'json', 'csv', 'png', 'jpg', 'jpeg']
    type_label = "Upload intel (Text/Image)"
    
    if PDF_AVAILABLE:
        supported_types.append('pdf')
        type_label += "/PDF"


    uploaded_files_sidebar = st.file_uploader(
        type_label, 
        type=supported_types, 
        accept_multiple_files=True,
        key="sidebar_uploader"
    )

# -----------------------------------------------------------------------------
# Chat Interface
# -----------------------------------------------------------------------------
col1, col2 = st.columns([1, 5])
with col1:
    st.markdown("# 🔴")
with col2:
    st.markdown("# RED PILL PROTOCOL")
    st.caption("DIGITAL SOVEREIGNTY v4.0.0")

# --- FILE UPLOAD POPUP IN MAIN CHAT ---
with st.popover("📎 Upload Files", help="Attach files to the conversation"):
    uploaded_files_main = st.file_uploader(
        "Select files to upload",
        type=supported_types,
        accept_multiple_files=True,
        key="main_uploader"
    )

# Combine files from sidebar and main uploader
uploaded_files = []
if uploaded_files_sidebar:
    uploaded_files.extend(uploaded_files_sidebar)
if uploaded_files_main:
    # Avoid duplicates if possible, or just extend
    uploaded_files.extend(uploaded_files_main)
    # Simple de-duplication by name might be good but tricky with streamlit file objects
    # sticking to simple extension for now.

st.markdown("---")

# Display History
for message in st.session_state.messages:
    role = message["role"]
    content = message["content"]
    image_data = message.get("image")
    
    with st.chat_message(role):
        st.markdown(content)
        if image_data:
            st.image(image_data)

# User Input
with st.container():
    # Place mic next to the chat if possible, or just above it
    voice_prompt = speech_to_text(language='ca', start_prompt="🎙️ Parlar", stop_prompt="⏹️ Parant...", just_once=True, key='STT')
    text_prompt = st.chat_input("Enter your query to the construct...")

prompt = text_prompt or voice_prompt

if prompt:
    # 1. Display User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Process
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        assistant_image = None
        
        # A. Memory Recall
        context_text = ""
        if st.session_state.memory_manager:
            with st.status("ACCESSING NEURAL PATHWAYS...", expanded=False) as status:
                relevant = st.session_state.memory_manager.search_and_reinforce("social_memories", prompt, limit=3)
                if relevant:
                    context_text = "\n".join([f"- {m.payload['content']}" for m in relevant])
                    status.update(label=f"RECOVERED {len(relevant)} ENGRAMS", state="complete")
                else:
                    status.update(label="NO MATCHING ENGRAMS", state="complete")

                # B. Construct Prompt
        system_prompt = (
            "You are Neo, an AI assistant powered by the Red Pill Protocol. "
            "You are connected to a private local server and a local persistent memory database (The Bunker). "
            "Use the following context to answer the user if relevant.\n\n"
            f"CONTEXT FROM BUNKER:\n{context_text}\n\n"
            "INSTRUCTIONS:\n"
            "- Adopt a professional, technical, slightly cyberpunk persona.\n"
            "- If the user asks for an image or visual, use the 'generate_image' tool. (Powered by VISUAL CORTEX)\n"
            "- Be helpful. Provide detailed explanations when necessary, but remain concise for simple queries.\n"
            "- If memories are relevant, reference them implicitly or explicitly.\n"
            "- If the user asks you to remember something, confirm it is being saved to the Bunker.\n"
        )

        messages = [{"role": "system", "content": system_prompt}]
        
        # Tools Definition
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "generate_image",
                    "description": "Generate an image using DALL-E 3 based on a text description.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "The detailed description of the image to generate.",
                            }
                        },
                        "required": ["prompt"],
                    },
                }
            }
        ]
        
        # Add uploaded files to context
        file_context = ""
        user_images = []
        
        if uploaded_files:
            for uploaded_file in uploaded_files:
                try:
                    # Text files
                    if uploaded_file.type in ["text/plain", "text/markdown", "text/x-python", "application/json", "text/csv"]:
                        stringio = uploaded_file.getvalue().decode("utf-8")
                        file_context += f"\n\n--- FILE: {uploaded_file.name} ---\n{stringio}\n--- END FILE ---\n"
                    
                    # Image files
                    elif uploaded_file.type in ["image/png", "image/jpeg", "image/jpg"]:
                        # Convert to base64
                        base64_image = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
                        user_images.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{uploaded_file.type};base64,{base64_image}"
                            }
                        })
                        file_context += f"\n[Attached Image: {uploaded_file.name}]"
                    
                    # PDF files - DISABLED
                    # elif uploaded_file.type == "application/pdf" and PDF_AVAILABLE:
                    #     pdf_reader = PdfReader(io.BytesIO(uploaded_file.getvalue()))
                    #     pdf_text = ""
                    #     for page in pdf_reader.pages:
                    #         pdf_text += page.extract_text() + "\n"
                    #     file_context += f"\n\n--- PDF: {uploaded_file.name} ---\n{pdf_text}\n--- END PDF ---\n"
                    


                except Exception as e:
                    file_context += f"\n[Error reading file {uploaded_file.name}: {str(e)}]"
        
        # If we have file context, append it to the user's latest message or system prompt
        if file_context:
            pass 

        # Add last 4 messages for short term context
        # We need to construct the messages carefully if we have images
        
        # 1. Add history (text only for now to keep it simple, or we could support multi-modal history if we store it right)
        # For this implementation, we will only send images in the Current Turn.
        messages.extend(st.session_state.messages[-4:]) 
        
        # 2. Prepare the *current* user message
        if user_images:
            # Multi-modal message
            user_content = [
                {"type": "text", "text": f"{prompt}\n\nADDITIONAL CONTEXT FROM UPLOADED FILES:{file_context}"}
            ]
            user_content.extend(user_images)
            
            # Replace the last message we optimistically added (which was text-only) with the complex one?
            # Actually st.session_state.messages only has the text prompt.
            # The 'messages' list for the API is what we are building here.
            
            # So we need to POP the last message (which is the current user prompt text-only) 
            # and replace it with the multi-modal version for the API call.
            if messages and messages[-1]["role"] == "user":
                messages.pop()
            
            messages.append({"role": "user", "content": user_content})
            
        else:
            # Text-only message (but with file context appended)
            
            # Let's remove the simple prompt we added from 'messages' list (which came from session_state)
            if messages and messages[-1]["role"] == "user":
                 messages.pop()
                 
            final_user_text = f"{prompt}\n\nADDITIONAL CONTEXT FROM UPLOADED FILES:{file_context}" if file_context else prompt
            messages.append({"role": "user", "content": final_user_text})


        # C. Generate Response
        if st.session_state.client:
            try:
                # Try generating with tools first
                try:
                    response = st.session_state.client.chat.completions.create(
                        model=cfg.LLM_MODEL_NAME,
                        messages=messages,
                        tools=tools,
                        tool_choice="auto",
                        temperature=0.7,
                        max_tokens=4096,
                        stream=False,
                    )
                except Exception as e:
                    # Fallback if tools fail (e.g. Local LLM doesn't support them)
                    # We send the request again without tools
                    # st.warning(f"Using fallback mode (Tools unavailable: {e})")
                    response = st.session_state.client.chat.completions.create(
                        model=cfg.LLM_MODEL_NAME,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=4096,
                        stream=False,
                    )

                response_message = response.choices[0].message
                tool_calls = getattr(response_message, 'tool_calls', None)
                content = response_message.content or ""
                
                full_response = content
                message_placeholder.markdown(full_response)
                # D. Tool Handling (Image Generation)
                # Detect if image generation is needed (via tool_calls OR keyword detection)
                img_prompt = None
                
                if tool_calls:
                    for tool_call in tool_calls:
                        if tool_call.function.name == "generate_image":
                            args = json.loads(tool_call.function.arguments)
                            img_prompt = args.get("prompt")
                
                # Fallback: Keyword detection for local LLMs that don't support tool calls
                if not img_prompt:
                    image_keywords = [
                        "genera una imatge", "genera imatge", "imatge", "imatges", "fes una imatge", "fes-me una imatge",
                        "generar imagen", "genera imagen", "imagen", "imagenes", "haz una imagen", "hazme una imagen",
                        "generate image", "generate an image", "image", "images", "make an image",
                        "dibuixa", "dibuix", "dibuja", "dibujo", "draw", "drawing",
                        "genera foto", "genera una foto", "foto", "photo", "photography"
                    ]
                    prompt_lower = prompt.lower()
                    if any(kw in prompt_lower for kw in image_keywords):
                        # Use the user's original prompt as the image prompt
                        img_prompt = prompt
                
                if img_prompt:
                    with st.status(f"GENERATING VISUAL ENGRAM: {img_prompt[:60]}...", expanded=True) as status:
                        try:
                            img_url = None
                            img_raw = None
                            is_base64 = False
                            
                            if st.session_state.dalle_client:
                                # Use DALL-E 3
                                dalle_resp = st.session_state.dalle_client.images.generate(
                                    model="dall-e-3",
                                    prompt=img_prompt,
                                    size="1024x1024",
                                    quality="standard",
                                    n=1,
                                )
                                img_url = dalle_resp.data[0].url
                                st.image(img_url, caption=f"VISUAL CORTEX ENGRAM: {img_prompt}")
                                # Download for local saving
                                img_raw = requests.get(img_url).content
                            else:
                                # Fallback to Hugging Face Free API
                                img_raw = generate_image_free(img_prompt, status=status)
                                if img_raw:
                                    st.image(img_raw, caption=f"VISUAL CORTEX ENGRAM (HF): {img_prompt}")
                                else:
                                    if not cfg.HF_API_KEY:
                                        status.error("VISUAL CORTEX OFFLINE: Afegeix HF_API_KEY al teu .env")
                                    else:
                                        status.error("VISUAL CORTEX FAILURE: All visual fallback models (HF) failed.")
                                    full_response += f"\n\n[SYSTEM ALERT: VISUAL CORTEX FAILURE]"

                            # --- LOCAL SAVING TO THE BUNKER ---
                            if img_raw:
                                from pathlib import Path
                                bunker_dir = Path.home() / "Baixades" / "Bunker" / "Creuetes"
                                bunker_dir.mkdir(parents=True, exist_ok=True)
                                
                                # Sanitize filename from prompt
                                clean_name = re.sub(r'[^\w\s-]', '', img_prompt).strip().replace(' ', '_')[:50].upper()
                                if not clean_name: clean_name = "VISUAL_ENGRAM"
                                
                                # Determine extension
                                ext = ".png" if st.session_state.dalle_client else ".jpg"
                                filename = f"{clean_name}{ext}" if not is_base64 else f"{clean_name}.webp"

                                file_path = bunker_dir / filename
                                
                                with open(file_path, "wb") as f:
                                    f.write(img_raw)
                                
                                st.success(f"📁 ENGRAM LOCALIZED: {file_path}")
                                full_response += f"\n\n[Visual Engram Saved to Bunker: {file_path}]"
                                
                                # Save image for chat history
                                assistant_image = img_raw
                            
                            status.update(label="VISUAL ENGRAM COMPLETE", state="complete")
                        except Exception as img_e:
                            st.error(f"IMAGE GEN ERROR: {img_e}")
                            status.update(label="VISUAL ENGRAM FAILED", state="error")

                # E. Persist Memory
                if st.session_state.memory_manager:
                    # We only save the text prompt to memory to save space/complexity for now
                    memory_text = f"User asked: {prompt}\n(With {len(uploaded_files)} files attached)\nAI answered: {full_response}"
                    memory_text = memory_text[:4096]  # Ensure it fits the engram size limit
                    st.session_state.memory_manager.add_memory("social_memories", memory_text)
                    
                # E. Voice Generation (TTS) - Neural Gendered Voices
                tts_voice = st.session_state.get("tts_voice", "ca-ES-JoanaNeural")
                if tts_voice:  # None means silence
                    try:
                        clean_text = clean_text_for_tts(full_response)
                        if clean_text:
                            # Use edge-tts (async) inside asyncio.run
                            communicate = edge_tts.Communicate(clean_text, tts_voice)
                            fp = io.BytesIO()
                            # We use a temp file or bytes? Communicate.save is async.
                            # Let's use a simpler approach for Streamlit
                            async def get_audio_bytes():
                                audio_data = b""
                                async for chunk in communicate.stream():
                                    if chunk["type"] == "audio":
                                        audio_data += chunk["data"]
                                return audio_data
                            
                            audio_bytes = asyncio.run(get_audio_bytes())
                            if audio_bytes:
                                st.audio(audio_bytes, format="audio/mp3", autoplay=True)
                    except Exception as tts_e:
                        st.warning(f"Error generant àudio (Neural): {tts_e}")

            except Exception as e:

                # Check for "is not of type 'string' - 'content'" error which means model doesn't support images
                error_str = str(e)
                if "400" in error_str and "'content'" in error_str and "not of type 'string'" in error_str:
                    st.error("⚠️ IMAGE UPLOAD ERROR: The connected AI model does not support image inputs (Vision).")
                    st.info("Resolution: Please switch to a multimodal model (like LLaVA) in your local server, or upload text files only.")
                    full_response = "SYSTEM ALERT: INCOMPATIBLE MODEL DETECTED (VISION MODULE MISSING)."
                else:
                    st.error(f"CRITICAL ERROR: {e}")
                    full_response = "CONNECTION SEVERED. CHECK LOCAL NODE."
        else:
             st.error("UPLINK OFFLINE.")
             full_response = "SYSTEM HALTED."

    # 3. Save Assistant Message
    # We must also save the text into session_state so it renders on refresh
    msg_data = {"role": "assistant", "content": full_response}
    if assistant_image:
        msg_data["image"] = assistant_image
        
    st.session_state.messages.append(msg_data)
