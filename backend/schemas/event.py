from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator


class EventRecord(BaseModel):
    flag_key: str
    event_type: Literal["exposure", "conversion"]
    variation_index: int
    user_id: str
    attributes: dict = {}
    timestamp: datetime | None = None


class EventBatch(BaseModel):
    events: list[EventRecord]

    @field_validator("events")
    @classmethod
    def max_batch_size(cls, v):
        if len(v) > 1000:
            raise ValueError("Batch size cannot exceed 1000 events")
        return v


class VariationResult(BaseModel):
    variation_index: int
    exposures: int
    conversions: int
    conversion_rate_pct: float | None


class ExperimentResults(BaseModel):
    flag_key: str
    variations: list[VariationResult]
