from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(examples=["validation_error"])
    message: str = Field(examples=["Request validation failed"])
    request_id: str | None = Field(default=None, examples=["01J00000000000000000000000"])
    details: Any = Field(default=None)


class ErrorResponse(BaseModel):
    error: ErrorDetail
