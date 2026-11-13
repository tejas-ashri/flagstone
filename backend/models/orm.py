import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

DEFAULT_PROJECT_ID = "default"


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())


class Flag(Base):
    __tablename__ = "flags"
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    key: Mapped[str] = mapped_column(String, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    variations: Mapped[list] = mapped_column(JSON, default=list)
    default_variation: Mapped[int] = mapped_column(Integer, default=0)
    rules: Mapped[list] = mapped_column(JSON, default=list)
    rollout: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )


class FeatureEvent(Base):
    __tablename__ = "events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "flag_key"], ["flags.project_id", "flags.key"], ondelete="CASCADE"
        ),
        Index("ix_events_project_flag_type", "project_id", "flag_key", "event_type", "received_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[str] = mapped_column(String)
    flag_key: Mapped[str] = mapped_column(String)
    event_type: Mapped[str] = mapped_column(String)  # 'exposure' | 'conversion'
    variation_index: Mapped[int] = mapped_column(Integer)
    user_id: Mapped[str] = mapped_column(String)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())


class SdkKey(Base):
    __tablename__ = "sdk_keys"
    key_hash: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String)
    # First characters of the key, so admins can tell keys apart.
    prefix: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True)  # always lowercase
    name: Mapped[str] = mapped_column(String, default="")
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Identity(Base):
    """A login method (GitHub, Google, Slack, dev) linked to a user."""

    __tablename__ = "identities"
    provider: Mapped[str] = mapped_column(String, primary_key=True)
    provider_user_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )


class Membership(Base):
    __tablename__ = "memberships"
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String)  # 'admin' | 'viewer'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())


class Invitation(Base):
    """Access granted to an email that has not signed in yet."""

    __tablename__ = "invitations"
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    email: Mapped[str] = mapped_column(String, primary_key=True)  # always lowercase
    role: Mapped[str] = mapped_column(String)
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())


class Session(Base):
    __tablename__ = "sessions"
    # sha256 of the cookie value; the raw token is never stored.
    token_hash: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
