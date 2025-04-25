# Procrai Backend

FastAPI-based backend for the Procrai document translation service.

## API Endpoints:

- `/api/v1/upload/` - POST - Upload a document (PDF/Image) and store it.
- `/api/v1/ocr/` - POST - Extract text with layout information.
- `/api/v1/translate/` - POST - Translate extracted text while preserving structure.
- `/api/v1/reconstruct/` - POST - Rebuild translated document (PDF) while maintaining layout.
- `/api/v1/workflow/process` - POST - Process a document through the complete workflow (OCR -> Translate -> Reconstruct).

## Running the Backend

```bash
# From the project root
PYTHONPATH=$PYTHONPATH:./src uvicorn app.main:app --reload
```

## API Documentation

The API documentation is available at `http://localhost:8000/api/v1/docs` when the backend server is running.
