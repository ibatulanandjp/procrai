from fastapi import UploadFile


def is_file_type_allowed(file: UploadFile, allowed_extensions: list[str]) -> bool:
    extension = file.content_type.split("/")[-1].lower()

    return extension in allowed_extensions
