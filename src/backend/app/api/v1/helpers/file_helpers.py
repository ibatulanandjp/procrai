from fastapi import UploadFile


def is_file_type_allowed(file: UploadFile, allowed_extensions: set[str]) -> bool:
    if file.content_type:
        extension = file.content_type.split("/")[-1].lower()
    else:
        extension = file.filename.split(".")[-1].lower() if file.filename else ""

    return extension in allowed_extensions
