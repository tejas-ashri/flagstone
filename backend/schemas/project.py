import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

Role = Literal["admin", "viewer"]


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    avatar_url: str | None

    model_config = {"from_attributes": True}


class ProjectMembershipResponse(BaseModel):
    id: str
    name: str
    role: Role
    flag_count: int
    member_count: int


class MeResponse(BaseModel):
    user: UserResponse
    identities: list[str]
    projects: list[ProjectMembershipResponse]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be blank")
        return v


class ProjectUpdate(ProjectCreate):
    pass


class SdkKeyCreate(BaseModel):
    label: str = Field(min_length=1, max_length=80)


class SdkKeyResponse(BaseModel):
    id: str = Field(validation_alias="key_hash")
    label: str
    prefix: str
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None

    model_config = {"from_attributes": True, "populate_by_name": True}


class SdkKeyCreated(SdkKeyResponse):
    # Only returned once, at creation.
    key: str


class MemberResponse(BaseModel):
    user: UserResponse
    role: Role
    created_at: datetime


class InvitationResponse(BaseModel):
    email: str
    role: Role
    created_at: datetime


class MembersResponse(BaseModel):
    members: list[MemberResponse]
    invitations: list[InvitationResponse]


class InviteCreate(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    role: Role = "viewer"

    @field_validator("email")
    @classmethod
    def normalize(cls, v: str) -> str:
        v = v.strip().lower()
        local, _, domain = v.partition("@")
        if not local or "." not in domain:
            raise ValueError("Enter a valid email address")
        return v


class RoleUpdate(BaseModel):
    role: Role


class EvaluateRequest(BaseModel):
    user: dict[str, Any]


class EvaluateResponse(BaseModel):
    variation_index: int
    value: Any
    reason: Literal["disabled", "rule", "rollout", "outside_rollout", "default"]
    rule_index: int | None = None
    bucket: int | None = None
    rollout_percentage: int | None = None


class DevLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    name: str = ""
