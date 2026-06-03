# app.py
import streamlit as st
from groq import Groq
import time
from datetime import datetime

# ------------------- PAGE CONFIG -------------------
st.set_page_config(
    page_title="Groq Multi‑Model Chat",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------- CUSTOM CSS (dark, modern) -------------------
st.markdown(
    """
    <style>
    .main { background: #0a0c10; }
    section[data-testid="stSidebar"] { background: #0f1117; border-right: 1px solid #252836; }
    .user-bubble {
        background: #1a2f6e; color: #c8d8ff; border-radius: 20px 20px 5px 20px;
        padding: 10px 16px; margin: 8px 0; max-width: 75%; float: right;
        clear: both; word-wrap: break-word; font-size: 14px; line-height: 1.5;
    }
    .assistant-bubble {
        background: #1f2230; color: #e2e4f0; border-radius: 20px 20px 20px 5px;
        padding: 10px 16px; margin: 8px 0; max-width: 75%; float: left;
        clear: both; word-wrap: break-word; font-size: 14px; line-height: 1.5;
        border: 1px solid #2e3244;
    }
    .badge {
        font-size: 10px; font-family: monospace; background: #2a2d3e;
        padding: 2px 8px; border-radius: 12px; color: #8b5cf6; display: inline-block; margin-bottom: 4px;
    }
    .cmp-card {
        background: #0f1117; border: 1px solid #252836; border-radius: 16px;
        padding: 16px; margin-bottom: 12px; transition: 0.2s;
    }
    .cmp-card:hover { border-color: #8b5cf6; }
    h1, h2, h3 { color: #e2e4f0 !important; }
    hr { border-color: #252836; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------- SECRET KEY HANDLING -------------------
def get_groq_client():
    api_key = st.secrets.get("GROQ_API_KEY", None)
    if not api_key:
        st.error("❌ GROQ_API_KEY not found in secrets. Please add it in Streamlit Cloud → Settings → Secrets.")
        st.stop()
    return Groq(api_key=api_key)

client = get_groq_client()

# ------------------- FETCH ACTIVE MODELS FROM GROQ API -------------------
@st.cache_data(ttl=3600)
def get_available_models():
    """Fetch currently supported chat models from Groq API."""
    try:
        models = client.models.list()
        chat_models = {}
        for model in models.data:
            # Filter out non‑chat models
            if "embed" not in model.id and "whisper" not in model.id:
                # Friendly name
                display_name = model.id.replace("-", " ").title()
                chat_models[model.id] = display_name
        return chat_models
    except Exception as e:
        st.error(f"Could not fetch models: {str(e)}")
        # Fallback models (known working)
        return {
            "llama-3.3-70b-versatile": "Llama 3.3 70B",
            "llama-3.1-8b-instant": "Llama 3.1 8B",
            "gemma2-9b-it": "Gemma 2 9B",
        }

# ------------------- SIDEBAR CONFIGURATION -------------------
with st.sidebar:
    st.image("https://groq.com/wp-content/uploads/2023/03/Groq_logo.png", width=180)
    st.markdown("## ⚙️ Configuration")

    # Get live models
    available_models = get_available_models()
    model_keys = list(available_models.keys())
    default_model = model_keys[0] if model_keys else "llama-3.3-70b-versatile"

    selected_model = st.selectbox(
        "🤖 Model",
        options=model_keys,
        format_func=lambda x: available_models[x],
        index=0,
    )

    # System prompt
    system_prompt = st.text_area(
        "🧠 System prompt",
        value="You are a helpful, knowledgeable AI assistant.",
        height=100,
    )

    # Clear chat button
    if st.button("🗑️ Clear chat history", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    # Export chat
    if st.button("📥 Export chat (.txt)", use_container_width=True):
        if st.session_state.messages:
            chat_text = f"Groq Chat Export – {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            chat_text += f"Model: {available_models[selected_model]}\n"
            chat_text += f"System: {system_prompt}\n{'-'*40}\n\n"
            for msg in st.session_state.messages:
                chat_text += f"[{msg['role'].upper()}]\n{msg['content']}\n\n"
            st.download_button(
                "⬇️ Download",
                chat_text,
                file_name=f"groq_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True,
            )
        else:
            st.info("No messages to export.")

    st.markdown("---")
    st.caption("🔒 API key from secrets.\n⚡ Powered by Groq LPU.")

# ------------------- INITIALIZE SESSION STATE -------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# Validate and migrate compare_configs to use valid model IDs
if "compare_configs" not in st.session_state:
    # Start with two valid default models
    st.session_state.compare_configs = [
        {"model": model_keys[0] if model_keys else "llama-3.3-70b-versatile", "name": available_models.get(model_keys[0], "Llama 3.3 70B")},
        {"model": model_keys[1] if len(model_keys) > 1 else model_keys[0], "name": available_models.get(model_keys[1], "Llama 3.1 8B")},
    ]
else:
    # Clean up any old model IDs that are no longer available
    valid_keys = set(model_keys)
    for cfg in st.session_state.compare_configs:
        if cfg["model"] not in valid_keys:
            cfg["model"] = default_model
            cfg["name"] = available_models.get(default_model, "Unknown")
        else:
            cfg["name"] = available_models[cfg["model"]]

# ------------------- MAIN TABS -------------------
tab_chat, tab_compare, tab_info = st.tabs(["💬 Chat", "⚖️ Compare Models", "ℹ️ Info"])

# ======================= CHAT TAB =======================
with tab_chat:
    st.markdown(f"#### 🧠 Model: **{available_models[selected_model]}**")
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(
                    f'<div class="message-row" style="justify-content: flex-end;">'
                    f'<div class="user-bubble">{msg["content"]}</div></div>',
                    unsafe_allow_html=True,
                )
            else:
                display_model = msg.get("model", available_models[selected_model])
                st.markdown(
                    f'<div class="message-row"><div class="assistant-bubble">'
                    f'<span class="badge">🤖 {display_model}</span><br>'
                    f'{msg["content"]}</div></div>',
                    unsafe_allow_html=True,
                )

    user_input = st.chat_input("Type your message here...")
    if user_input:
        st.session_state.messages.append(
            {"role": "user", "content": user_input, "timestamp": time.time()}
        )
        with chat_container:
            st.markdown(
                f'<div class="message-row" style="justify-content: flex-end;">'
                f'<div class="user-bubble">{user_input}</div></div>',
                unsafe_allow_html=True,
            )

        with st.spinner("Thinking..."):
            try:
                conv_history = []
                if system_prompt:
                    conv_history.append({"role": "system", "content": system_prompt})
                for m in st.session_state.messages[-10:]:
                    conv_history.append({"role": m["role"], "content": m["content"]})

                response = client.chat.completions.create(
                    model=selected_model,
                    messages=conv_history,
                    temperature=0.7,
                    max_tokens=1024,
                )
                assistant_reply = response.choices[0].message.content

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": assistant_reply,
                        "model": available_models[selected_model],
                        "timestamp": time.time(),
                    }
                )
                with chat_container:
                    st.markdown(
                        f'<div class="message-row"><div class="assistant-bubble">'
                        f'<span class="badge">🤖 {available_models[selected_model]}</span><br>'
                        f'{assistant_reply}</div></div>',
                        unsafe_allow_html=True,
                    )
            except Exception as e:
                st.error(f"API error: {str(e)}")

# ======================= COMPARE TAB =======================
with tab_compare:
    st.markdown("## ⚖️ Compare multiple models side‑by‑side")
    st.caption("Add up to 4 models, enter a prompt, and see all responses at once.")

    def add_compare_row():
        if len(st.session_state.compare_configs) < 4:
            st.session_state.compare_configs.append(
                {"model": default_model, "name": available_models[default_model]}
            )
        else:
            st.warning("Maximum 4 models for comparison.")

    def remove_compare_row(idx):
        if len(st.session_state.compare_configs) > 1:
            st.session_state.compare_configs.pop(idx)
            st.rerun()

    cols = st.columns([3, 1])
    with cols[0]:
        st.markdown("#### Models to compare")
    with cols[1]:
        st.button("➕ Add model", on_click=add_compare_row)

    # Display each compare row with safe index handling
    for i, cfg in enumerate(st.session_state.compare_configs):
        col1, col2, col3 = st.columns([3, 2, 0.5])
        with col1:
            # Find the current index; if not found, default to 0
            current_idx = model_keys.index(cfg["model"]) if cfg["model"] in model_keys else 0
            model_key = st.selectbox(
                f"Model {i+1}",
                options=model_keys,
                format_func=lambda x: available_models[x],
                key=f"cmp_model_{i}",
                index=current_idx,
            )
            cfg["model"] = model_key
            cfg["name"] = available_models[model_key]
        with col2:
            st.write("")
        with col3:
            if len(st.session_state.compare_configs) > 1:
                st.button("🗑️", key=f"del_{i}", on_click=remove_compare_row, args=(i,))

    compare_prompt = st.text_area(
        "📝 Prompt to send to all models",
        height=100,
        placeholder="E.g., Explain quantum computing in simple terms...",
        key="compare_prompt",
    )

    if st.button("🚀 Run comparison", use_container_width=True):
        if not compare_prompt.strip():
            st.error("Please enter a prompt.")
        else:
            st.markdown("---")
            st.markdown("### 📊 Results")
            progress_bar = st.progress(0)
            responses = []
            total = len(st.session_state.compare_configs)

            for idx, cfg in enumerate(st.session_state.compare_configs):
                try:
                    messages = [{"role": "system", "content": system_prompt}]
                    messages.append({"role": "user", "content": compare_prompt})
                    resp = client.chat.completions.create(
                        model=cfg["model"],
                        messages=messages,
                        temperature=0.7,
                        max_tokens=1024,
                    )
                    replies = resp.choices[0].message.content
                    responses.append(
                        {"model": cfg["name"], "reply": replies, "error": None}
                    )
                except Exception as e:
                    responses.append(
                        {"model": cfg["name"], "reply": None, "error": str(e)}
                    )
                progress_bar.progress((idx + 1) / total)

            for resp in responses:
                st.markdown(
                    f"""
                    <div class="cmp-card">
                        <h4>🤖 {resp['model']}</h4>
                        <hr>
                        <div style="white-space: pre-wrap;">{resp['reply'] if resp['reply'] else f'❌ Error: {resp["error"]}'}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.success("Comparison complete!")

