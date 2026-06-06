from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.medication import MedicationForm, MedicationSource


class MedicationFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=300)
    generic_name: str | None = Field(default=None, max_length=300)
    brand_name: str | None = Field(default=None, max_length=300)
    dosage: str | None = Field(default=None, max_length=200)
    form: MedicationForm
    instructions: str | None = Field(
        default=None,
        max_length=4000,
        description="User-confirmed text only; never generated medical advice",
    )
    with_food: bool | None = None
    pill_color: str | None = Field(default=None, max_length=100)
    pill_shape: str | None = Field(default=None, max_length=100)
    imprint: str | None = Field(default=None, max_length=100)
    label_image_id: UUID | None = None
    pill_image_id: UUID | None = None
    source: MedicationSource = MedicationSource.MANUAL
    confirmed_by: UUID | None = None
    active: bool = True

    @field_validator(
        "name",
        "generic_name",
        "brand_name",
        "dosage",
        "instructions",
        "pill_color",
        "pill_shape",
        "imprint",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def enforce_ocr_confirmation(self) -> "MedicationFields":
        if self.source is MedicationSource.OCR and self.confirmed_by is None:
            if self.instructions is not None:
                raise ValueError("OCR instructions require patient confirmation")
            self.active = False
        return self


class MedicationCreateRequest(MedicationFields):
    pass


class MedicationUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=300)
    generic_name: str | None = Field(default=None, max_length=300)
    brand_name: str | None = Field(default=None, max_length=300)
    dosage: str | None = Field(default=None, max_length=200)
    form: MedicationForm | None = None
    instructions: str | None = Field(
        default=None,
        max_length=4000,
        description="User-confirmed text only; never generated medical advice",
    )
    with_food: bool | None = None
    pill_color: str | None = Field(default=None, max_length=100)
    pill_shape: str | None = Field(default=None, max_length=100)
    imprint: str | None = Field(default=None, max_length=100)
    label_image_id: UUID | None = None
    pill_image_id: UUID | None = None
    confirmed_by: UUID | None = None
    active: bool | None = None

    @field_validator(
        "name",
        "generic_name",
        "brand_name",
        "dosage",
        "instructions",
        "pill_color",
        "pill_shape",
        "imprint",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class MedicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    generic_name: str | None
    brand_name: str | None
    dosage: str | None
    form: MedicationForm
    instructions: str | None
    with_food: bool | None
    pill_color: str | None
    pill_shape: str | None
    imprint: str | None
    label_image_id: UUID | None
    pill_image_id: UUID | None
    source: MedicationSource
    confirmed_by: UUID | None
    active: bool
    created_at: datetime
    updated_at: datetime
