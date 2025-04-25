import asyncio
from pathlib import Path

import httpx
import streamlit as st

# Constants
API_BASE_URL = "http://localhost:8000/api/v1"
ALLOWED_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg"]


def init_session_state():
    """Initialize session state variables"""
    if "translation_complete" not in st.session_state:
        st.session_state.translation_complete = False
    if "translated_filename" not in st.session_state:
        st.session_state.translated_filename = None


def is_valid_file(file):
    """Check if the uploaded file is valid"""
    if file is None:
        return False
    file_ext = Path(file.name).suffix.lower()
    return file_ext in ALLOWED_EXTENSIONS


async def translate_document(file, src_lang, target_lang):
    """Process document through the translation workflow"""
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Upload file
            files = {"file": (file.name, file.getvalue(), file.type)}
            response = await client.post(
                f"{API_BASE_URL}/workflow/process",
                files=files,
                params={"src_lang": src_lang, "target_lang": target_lang},
            )
            response.raise_for_status()
            return response.content, file.name
    except Exception as e:
        st.error(f"Error processing document: {str(e)}")
        return None, None


def main():
    st.set_page_config(
        page_title="Procrai - Document Translation", page_icon="📄", layout="wide"
    )

    init_session_state()

    # Header
    st.title("Procrai Document Translation")
    st.markdown(
        """
    Upload documents for AI-powered translation with layout preservation.
    Supported file types: PDF, PNG, JPG, JPEG
    """
    )

    # Sidebar for settings
    with st.sidebar:
        st.header("Translation Settings")
        src_lang = st.selectbox(
            "Source Language",
            options=["ja", "en"],
            format_func=lambda x: "Japanese" if x == "ja" else "English",
        )
        target_lang = st.selectbox(
            "Target Language",
            options=["en", "ja"],
            format_func=lambda x: "English" if x == "en" else "Japanese",
            index=0 if src_lang == "ja" else 1,
        )

    # Main content
    uploaded_file = st.file_uploader(
        "Choose a document to translate", type=["pdf", "png", "jpg", "jpeg"]
    )

    if uploaded_file and not st.session_state.translation_complete:
        if is_valid_file(uploaded_file):
            if st.button("Translate Document"):
                with st.spinner("Processing document..."):
                    pdf_content, filename = asyncio.run(
                        translate_document(uploaded_file, src_lang, target_lang)
                    )
                    if pdf_content:
                        st.session_state.translation_complete = True
                        st.session_state.translated_filename = filename
                        st.success("Translation completed!")

                        # Offer download
                        st.download_button(
                            label="Download Translated Document",
                            data=pdf_content,
                            file_name=f"translated_{filename}",
                            mime="application/pdf",
                        )

    # Reset button
    if st.session_state.translation_complete:
        if st.button("Translate Another Document"):
            st.session_state.translation_complete = False
            st.session_state.translated_filename = None
            st.rerun()

    # Footer
    st.markdown("---")
    st.markdown(
        "Procrai - Enterprise-Grade Document Translation with Uncompromising Privacy"
    )


if __name__ == "__main__":
    main()
