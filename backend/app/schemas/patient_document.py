"""Patient document schemas — P-12, P-13, P-14."""
from datetime import datetime
from pydantic import BaseModel, Field


class PatientDocumentUpload(BaseModel):
    """Input for uploading a patient document (form data — actual file is UploadFile)."""
    document_type: str = Field(..., pattern=r"^(xray|consent|lab_result|referral|photo|other)$")
    description: str | None = Field(default=None, max_length=500)
    tooth_number: int | None = Field(default=None, ge=11, le=85)


class PatientDocumentResponse(BaseModel):
    """Single document response."""
    id: str
    patient_id: str
    document_type: str
    file_name: str
    file_size_bytes: int
    mime_type: str
    description: str | None
    tooth_number: int | None
    uploaded_by: str
    download_url: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PatientDocumentListResponse(BaseModel):
    """Paginated list of patient documents."""
    items: list[PatientDocumentResponse]
    total: int
    page: int
    page_size: int
