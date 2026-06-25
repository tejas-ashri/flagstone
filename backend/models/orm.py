import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, String, Boolean, Integer, DateTime, func, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Flag(Base):
    __tablename__ = "flags"
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
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    flag_key: Mapped[str] = mapped_column(String, ForeignKey("flags.key", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String)  # 'exposure' | 'conversion'
    variation_index: Mapped[int] = mapped_column(Integer)
    user_id: Mapped[str] = mapped_column(String)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())


class SdkKey(Base):
    __tablename__ = "sdk_keys"
    key_hash: Mapped[str] = mapped_column(String, primary_key=True)
    label: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
