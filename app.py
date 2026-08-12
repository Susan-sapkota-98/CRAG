import os
import tempfile
import time
import streamlit as st

st.set_page_config(page_title="CRAG QA System", page_icon="🤖", layout="centered")

st.title("📚 Multimodal Educational QA System")
st.caption("CRAG-based RAG pipeline | Nepali + English")


@st.cache_resource(show_spinner="Loading pipeline...")
def load_graph_module():
    import crag_graph
    return crag_graph


cg = load_graph_module()
app = cg.app

if "history" not in st.session_state:
    st.session_state.history = []

# Tracks whether the latest answer still needs to be streamed once
if "just_answered" not in st.session_state:
    st.session_state.just_answered = False


# -----------------------------
# PDF Upload (supports multiple files)
# -----------------------------
with st.expander("📤 Upload a PDF to add to knowledge base", expanded=False):
    uploaded_files = st.file_uploader(
        "Choose PDF(s)", type=["pdf"], accept_multiple_files=True
    )
    mode_label = st.selectbox(
        "How to do index?",
        ["Add to existing index (accumulate)", "Replace existing index (start fresh)"],
    )
    mode = "add" if mode_label.startswith("Add") else "replace"

    if uploaded_files:
        if st.button("Process PDF(s)"):
            for i, uploaded_file in enumerate(uploaded_files):
                with st.spinner(f"Processing {uploaded_file.name} ({i+1}/{len(uploaded_files)})..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(uploaded_file.read())
                        tmp_path = tmp.name

                    # First file respects chosen mode; rest always "add" so they don't wipe each other out
                    current_mode = mode if i == 0 else "add"
                    cg.add_pdf_to_index(tmp_path, mode=current_mode)
                    os.remove(tmp_path)

            st.success(f"{len(uploaded_files)} PDF(s) added ({mode} mode). Index updated.")


# -----------------------------
# Image / handwritten upload (new block added for OCR routing)
# -----------------------------
with st.expander("🖼️ Upload a scanned image / handwritten page", expanded=False):
    img_file = st.file_uploader("Choose an image", type=["png", "jpg", "jpeg"], key="img_uploader")
    engine = st.selectbox(
        "Document type",
        ["english_printed", "nepali_printed", "english_handwritten"],
        format_func=lambda x: {
            "english_printed": "English (typed/printed)",
            "nepali_printed": "Nepali (typed/printed)",
            "english_handwritten": "English (handwritten)"
        }[x],
        key="ocr_engine_select"
    )
    img_mode_label = st.selectbox(
        "How to do index?",
        ["Add to existing index (accumulate)", "Replace existing index (start fresh)"],
        key="img_mode_select"
    )
    img_mode = "add" if img_mode_label.startswith("Add") else "replace"

    if img_file is not None:
        if st.button("Process image"):
            with st.spinner(f"Running OCR ({engine}) and updating index..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(img_file.read())
                    tmp_path = tmp.name

                cg.add_image_to_index(tmp_path, engine=engine, mode=img_mode)
                os.remove(tmp_path)

            st.success(f"'{img_file.name}' processed ({img_mode} mode). Index updated.")

# -----------------------------
# Question box
# -----------------------------
question = st.text_input("Ask the Question:", placeholder="e.g. what is AI?")

col1, col2 = st.columns([1, 5])
with col1:
    run = st.button("Ask", type="primary")

if run and question.strip():
    with st.spinner("Thinking..."):
        result = app.invoke({
            "question": question,
            "docs": [], "good_docs": [], "verdict": "", "reason": "",
            "strips": [], "kept_strips": [], "refined_context": "",
            "web_docs": [], "answer": "", "sources": [],
        })

    st.session_state.history.append((question, result))
    st.session_state.just_answered = True  # this answer should stream once

# Display latest result
if st.session_state.history:
    q, res = st.session_state.history[-1]

    # Source badges shown above the answer (pill-style, like the reference screenshot)
    sources = res.get("sources", [])
    if sources:
        badge_html = "".join(
            f'<span style="background-color:#1e3a5f; color:#7ec8ff; padding:4px 10px; '
            f'border-radius:6px; margin:3px; display:inline-block; font-size:0.85em;">{s}</span>'
            for s in sources
        )
        st.markdown(f"**📎 Sources:**<br>{badge_html}", unsafe_allow_html=True)
        st.markdown("")

    st.markdown("### Answer")

    answer_text = res.get("answer", "No answer generated.")

    # Word-by-word streaming effect (typewriter style) — only on the answer that was just generated
    if st.session_state.just_answered:
        def stream_words():
            for word in answer_text.split(" "):
                yield word + " "
                time.sleep(0.03)
        st.write_stream(stream_words)
        st.session_state.just_answered = False  # don't re-stream on next rerun
    else:
        st.write(answer_text)

    verdict = res.get("verdict", "")
    badge_color = {"CORRECT": "green", "AMBIGUOUS": "orange", "INCORRECT": "red"}.get(verdict, "gray")
    st.markdown(f"**Verdict:** :{badge_color}[{verdict}]")
    st.caption(res.get("reason", ""))

    with st.expander("🔍 Retrieved chunks (PDF)"):
        for d in res.get("docs", []):
            st.markdown(f"**Source:** {d.metadata.get('source', 'N/A')}")
            st.text(d.page_content[:300])
            st.divider()

    if res.get("web_docs"):
        with st.expander("🌐 Web search results"):
            for d in res.get("web_docs", []):
                st.markdown(f"**{d.metadata.get('title', '')}**  \n{d.metadata.get('url', '')}")
                st.text(d.page_content[:300])
                st.divider()

# Chat history sidebar
with st.sidebar:
    st.subheader("History")
    for q, r in reversed(st.session_state.history):
        st.markdown(f"- {q} → `{r.get('verdict','')}`")


    st.subheader("Model Settings")
    provider = st.selectbox("Provider", ["ollama", "huggingface", "openai"])

    if provider == "ollama":
        model_name = st.selectbox("Model", ["qwen2.5:7b", "llama3.1:8b", "mistral:7b"])
        api_key = None
    elif provider == "huggingface":
        model_name = st.text_input("HF model repo_id", "meta-llama/Meta-Llama-3-8B-Instruct")
        api_key = st.text_input("HF API token", type="password")
    else:  # openai
        model_name = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o"])
        api_key = st.text_input("OpenAI API key", type="password")

    if st.button("Apply model"):
        cg.set_active_model(provider, model_name, api_key)
        st.success(f"Switched to {provider}: {model_name}")