import asyncio
from pathlib import Path
import time
import subprocess
import os
import requests

import streamlit as st
import inngest
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="RAG PDF Chat",
    page_icon="📄",
    layout="wide"
)


# ==================================================
# SESSION STATE
# ==================================================

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

if "source_id" not in st.session_state:
    st.session_state["source_id"] = None

if "page" not in st.session_state:
    st.session_state["page"] = "upload"


# ==================================================
# 🧑‍💻 SIDEBAR DEVELOPER PANEL
# ==================================================

st.sidebar.title("🧑‍💻 Developer Panel")

# PDF STATUS
st.sidebar.subheader("📄 Document Status")

if st.session_state.get("source_id"):
    st.sidebar.success(f"Loaded: {st.session_state['source_id']}")
else:
    st.sidebar.warning("No PDF uploaded yet")

# ==================================================
# 📂 FILE PREVIEW PANEL (AUTO-DETECT PROJECT FILES)
# ==================================================

import glob

st.sidebar.divider()
st.sidebar.subheader("📂 View Project Files")

# auto-detect important project files
PROJECT_FILE_PATTERNS = [
    "*.py",
    "*.toml",
    "*.md",
    "*.env"
]

project_files = []

for pattern in PROJECT_FILE_PATTERNS:
    project_files.extend(glob.glob(pattern))

# remove unwanted folders like tests / uploads if needed
project_files = sorted(project_files)

if project_files:

    selected_file = st.sidebar.selectbox(
        "Select file",
        project_files
    )

    try:
        with open(selected_file, "r", encoding="utf-8") as f:

            st.sidebar.code(
                f.read(),
                language="python"
            )

    except Exception as e:

        st.sidebar.warning(
            f"Could not open file: {selected_file}"
        )

else:

    st.sidebar.warning("No project files detected")

# ==================================================
# 🧪 BACKEND TEST PANEL (AUTO-DETECT ALL TEST FILES)
# ==================================================

import glob

st.sidebar.subheader("🧪 Backend Tests")

# automatically detect ALL tests recursively
available_tests = sorted(
    glob.glob("tests/**/*.py", recursive=True)
)

# keep only test files
available_tests = [
    file for file in available_tests
    if "test_" in os.path.basename(file)
]


if available_tests:

    selected_test = st.sidebar.selectbox(
        "Select backend test",
        available_tests
    )

    # RUN SELECTED TEST
    if st.sidebar.button("▶ Run Selected Test"):

        result = subprocess.run(
            ["pytest", selected_test, "-v"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            st.sidebar.success("✅ Test Passed")
        else:
            st.sidebar.error("❌ Test Failed")

        st.sidebar.code(result.stdout)


    # RUN ALL TESTS BUTTON
    if st.sidebar.button("🚀 Run ALL Tests"):

        result = subprocess.run(
            ["pytest"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            st.sidebar.success("✅ All tests passed")
        else:
            st.sidebar.error("❌ Some tests failed")

        st.sidebar.code(result.stdout)


else:

    st.sidebar.warning("No backend tests found")

# ==================================================
# INNGEST CLIENT
# ==================================================

@st.cache_resource
def get_inngest_client():
    return inngest.Inngest(
        app_id="rag_app",
        is_production=False
    )


# ==================================================
# SAVE PDF
# ==================================================

def save_uploaded_pdf(file) -> Path:

    uploads_dir = Path("uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)

    file_path = uploads_dir / file.name
    file_path.write_bytes(file.getbuffer())

    return file_path


# ==================================================
# INGEST EVENT
# ==================================================

async def send_rag_ingest_event(pdf_path: Path):

    client = get_inngest_client()

    await client.send(
        inngest.Event(
            name="rag/ingest_pdf",
            data={
                "pdf_path": str(pdf_path.resolve()),
                "source_id": pdf_path.name,
            },
        )
    )


# ==================================================
# AUTO TOP-K
# ==================================================

def get_auto_top_k(question: str):

    if "summary" in question.lower():
        return 8

    elif len(question.split()) <= 5:
        return 3

    return 5


# ==================================================
# QUERY EVENT
# ==================================================

async def send_rag_query_event(question, top_k, source_id):

    client = get_inngest_client()

    result = await client.send(
        inngest.Event(
            name="rag/query_pdf_ai",
            data={
                "question": question,
                "top_k": top_k,
                "source_id": source_id,
            },
        )
    )

    return result[0]


# ==================================================
# WAIT FOR OUTPUT
# ==================================================

def wait_for_run_output(event_id):

    start = time.time()

    while True:

        url = f"{os.getenv('INNGEST_API_BASE','http://127.0.0.1:8288/v1')}/events/{event_id}/runs"

        res = requests.get(url).json()

        runs = res.get("data", [])

        if runs:

            run = runs[0]

            status = run.get("status")

            if status in ("Completed", "Succeeded", "Finished"):

                return run.get("output", {})

        if time.time() - start > 120:

            raise TimeoutError("Timeout")

        time.sleep(0.5)


# ==================================================
# 📄 PAGE 1 → UPLOAD
# ==================================================

if st.session_state["page"] == "upload":

    st.title("📄 Upload PDF")

    st.info("Upload a PDF to begin chatting with your document")

    uploaded = st.file_uploader(
        "Choose a PDF",
        type=["pdf"]
    )

    if uploaded:

        with st.spinner("Processing PDF..."):

            path = save_uploaded_pdf(uploaded)

            asyncio.run(
                send_rag_ingest_event(path)
            )

        st.session_state["source_id"] = path.name

        st.success(f"✅ PDF ready: {path.name}")

        if st.button("➡️ Go to Chat"):

            st.session_state["page"] = "chat"

            st.rerun()


# ==================================================
# 💬 PAGE 2 → CHAT
# ==================================================

elif st.session_state["page"] == "chat":

    st.title("💬 Chat with your PDF")

    st.caption("Powered by Retrieval-Augmented Generation")

    if not st.session_state["source_id"]:

        st.warning("Upload PDF first")

        if st.button("⬅️ Back"):

            st.session_state["page"] = "upload"

            st.rerun()

        st.stop()


    st.success(
        f"Active document: {st.session_state['source_id']}"
    )


    col1, col2 = st.columns([3, 1])

    with col1:

        if st.button("⬅️ Upload Page"):

            st.session_state["page"] = "upload"

            st.rerun()


    with col2:

        if st.button("🧹 Clear Chat"):

            st.session_state["chat_history"] = []

            st.rerun()


    for chat in st.session_state["chat_history"]:

        with st.chat_message("user"):

            st.markdown(chat["question"])


        with st.chat_message("assistant"):

            st.markdown(chat["answer"])


    question = st.chat_input("Ask something about your document...")


    if question:

        with st.chat_message("user"):

            st.markdown(question)


        auto_top_k = get_auto_top_k(question)


        with st.chat_message("assistant"):

            placeholder = st.empty()


            with st.spinner("Thinking..."):

                event_id = asyncio.run(
                    send_rag_query_event(
                        question,
                        auto_top_k,
                        st.session_state["source_id"]
                    )
                )


                output = wait_for_run_output(event_id)


                answer = output.get("answer", "")

                sources = output.get("sources", [])


            typed = ""

            for ch in answer:

                typed += ch

                placeholder.markdown(typed)

                time.sleep(0.01)


            if sources:

                with st.expander("📎 Retrieved Sources"):

                    for s in sources:

                        st.write(s)


        st.session_state["chat_history"].append(
            {
                "question": question,
                "answer": answer
            }
        )