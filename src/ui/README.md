# Procrai Frontend

Streamlit-based frontend for the Procrai document translation service.

## Features

- Upload PDF documents and images for translation
- Support for English ↔ Japanese translation
- Real-time translation progress tracking
- Download translated documents
- Preserves original document layout

## Running the Frontend

```bash
# From the project root
PYTHONPATH=$PYTHONPATH:./src streamlit run src/ui/main.py
```

## Usage

1. Select the source and target languages in the sidebar
2. Upload a document (PDF, PNG, JPG, JPEG)
3. Click "Translate Document" to start the translation process
4. Once the translation is complete, click "Download Translated Document" to download the result
5. Click "Translate Another Document" to start over

## Note

Make sure the backend server is running at `http://localhost:8000` before using the frontend.