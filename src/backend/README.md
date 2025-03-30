# Endpoints:

- `/api/v1/upload/` - POST - Upload a document (PDF/Image) and store it.
- `/api/v1/ocr/` - POST - Extract text with layout information.
- `/api/v1/translate/` - POST - Translate extracted text while preserving structure.
- `/api/v1/reconstruct/` - POST - Rebuild translated document (PDF) while maintaining layout.
- `/api/v1/status/{task_id}` - GET - Check the status of an asynchronous task (if needed).
