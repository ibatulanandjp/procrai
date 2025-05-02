import asyncio
from pathlib import Path

import httpx
import streamlit as st
from streamlit_pdf_viewer import pdf_viewer

# Constants
API_BASE_URL = "http://localhost:8000/api/v1"
ALLOWED_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg"]


def init_session_state():
    """Initialize session state variables"""
    if "translation_complete" not in st.session_state:
        st.session_state.translation_complete = False
    if "translated_filename" not in st.session_state:
        st.session_state.translated_filename = None
    if "original_file" not in st.session_state:
        st.session_state.original_file = None
    if "translated_file" not in st.session_state:
        st.session_state.translated_file = None


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
    Upload PDF document for AI-powered translation with layout preservation,
    without compromising privacy.
    """
    )

    # Sidebar for settings
    with st.sidebar:
        st.header("Translation Settings")
        src_lang = st.selectbox(
            "Source Language",
            options=["en", "ja"],
            format_func=lambda x: "English" if x == "en" else "Japanese",
        )
        target_lang = st.selectbox(
            "Target Language",
            options=["ja", "en"],
            format_func=lambda x: "Japanese" if x == "ja" else "English",
            index=0 if src_lang == "en" else 1,
        )

    # Main content
    uploaded_file = st.file_uploader(
        "Choose a document to translate", type=["pdf", "png", "jpg", "jpeg"]
    )

    if uploaded_file and not st.session_state.translation_complete:
        if is_valid_file(uploaded_file):
            if st.button("Translate Document"):
                with st.spinner("Processing document..."):
                    # Store original file
                    st.session_state.original_file = uploaded_file.getvalue()

                    # Process translation
                    pdf_content, filename = asyncio.run(
                        translate_document(uploaded_file, src_lang, target_lang)
                    )
                    if pdf_content:
                        st.session_state.translation_complete = True
                        st.session_state.translated_filename = filename
                        st.session_state.translated_file = pdf_content
                        st.success("Translation completed!")

    # Display comparison if translation is complete
    if st.session_state.translation_complete:
        st.header("Document Comparison")

        # Create two columns for side-by-side comparison
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Original Document")
            if st.session_state.original_file:
                pdf_viewer(st.session_state.original_file, width=550, height=650)
            else:
                st.warning("No original file to display.")

        with col2:
            st.markdown("### Translated Document")
            if st.session_state.translated_file:
                pdf_viewer(st.session_state.translated_file, width=550, height=650)
            else:
                st.warning("No translated file to display.")

        # Download button
        if st.session_state.translated_file:
            st.download_button(
                label="Download Translated Document",
                data=st.session_state.translated_file,
                file_name=f"translated_{st.session_state.translated_filename}",
                mime="application/pdf",
            )

        # Reset button
        if st.button("Translate Another Document"):
            st.session_state.translation_complete = False
            st.session_state.translated_filename = None
            st.session_state.original_file = None
            st.session_state.translated_file = None
            st.rerun()

    # Footer
    st.markdown(
        """
        <style>
        .footer {
            position: fixed;
            left: 0;
            bottom: 0;
            width: calc(100% - 10rem);
            margin-left: 10rem;
            width: 100%;
            background: #0e1117;
            color: gray;
            text-align: center;
            font-size: 1rem;
            padding: 0.5rem 0;
            z-index: 100;
            border-top: 1px solid #222;
            overflow-x: hidden;
            # transition: margin-left 0.2s, width 0.2s;
        }
        # @media (max-width: 1200px) {
        #     .footer {
        #         width: 100% !important;
        #         margin-left: 0 !important;
        #     }
        # }
        </style>
        <div class="footer">
            Procrai - Document Translation
            | Built with ☕ by
            <a href='https://linkedin.com/in/ibatulanand' target='_blank'
                style='color: #4F8BF9; text-decoration: none;'>@ibatulanand</a>
            | <a href='https://github.com/ibatulanandjp/procrai/' target='_blank'
                style='color: #4F8BF9; text-decoration: none;'>Github</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
