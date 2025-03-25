from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    filename: str = Field(..., description="Uploaded file name")
    message: str = Field(..., description="Message")
