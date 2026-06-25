from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class FlagRule(BaseModel):
    attribute: str
    operator: Literal["equals", "contains", "gt", "lt", "in"]
    value: Any
    variation: int


class FlagRollout(BaseModel):
    variation: int
    percentage: int


class FlagCreate(BaseModel):
    key: str
    enabled: bool = True
    variations: list[Any] = [False, True]
    default_variation: int = 0
    rules: list[FlagRule] = []
    rollout: FlagRollout | None = None


class FlagUpdate(BaseModel):
    enabled: bool | None = None
    variations: list[Any] | None = None
    default_variation: int | None = None
    rules: list[FlagRule] | None = None
    rollout: FlagRollout | None = None


class FlagResponse(BaseModel):
    key: str
    enabled: bool
    variations: list[Any]
    default_variation: int
    rules: list[FlagRule]
    rollout: FlagRollout | None
    updated_at: datetime

    model_config = {"from_attributes": True}
