import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import Settings
from backend.models.orm import (
    DEFAULT_PROJECT_ID,
    Identity,
    Invitation,
    Membership,
    Session,
    User,
)


@dataclass
class Profile:
    """What a login provider tells us about the person signing in."""

    provider: str
    provider_user_id: str
    email: str
    email_verified: bool
    name: str = ""
    avatar_url: str | None = None


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)  # SQLite drops tzinfo


async def create_session(db: AsyncSession, user_id: uuid.UUID, settings: Settings) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    db.add(
        Session(
            token_hash=_hash(token),
            user_id=user_id,
            created_at=now,
            expires_at=now + timedelta(hours=settings.session_ttl_hours),
        )
    )
    await db.commit()
    return token


async def user_for_session(db: AsyncSession, token: str) -> User | None:
    session = await db.get(Session, _hash(token))
    if session is None:
        return None
    if _aware(session.expires_at) <= datetime.now(timezone.utc):
        await db.delete(session)
        await db.commit()
        return None
    return await db.get(User, session.user_id)


async def delete_session(db: AsyncSession, token: str) -> None:
    await db.execute(delete(Session).where(Session.token_hash == _hash(token)))
    await db.commit()


async def _grant(db: AsyncSession, project_id: str, user_id: uuid.UUID, role: str) -> None:
    existing = await db.get(Membership, {"project_id": project_id, "user_id": user_id})
    if existing is None:
        db.add(
            Membership(
                project_id=project_id,
                user_id=user_id,
                role=role,
                created_at=datetime.now(timezone.utc),
            )
        )
    elif role == "admin" and existing.role != "admin":
        existing.role = "admin"


async def sign_in(db: AsyncSession, profile: Profile, settings: Settings) -> User:
    """Finds or creates the user for a verified login and applies pending access.

    Identities are matched first; failing that, a user with the same verified
    email is linked, so one person can sign in with any configured provider.
    """
    if not profile.email_verified or not profile.email:
        raise ValueError("A verified email address is required to sign in.")
    email = profile.email.strip().lower()
    now = datetime.now(timezone.utc)

    identity = await db.get(
        Identity, {"provider": profile.provider, "provider_user_id": profile.provider_user_id}
    )
    user = await db.get(User, identity.user_id) if identity else None
    if user is None:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None:
        user = User(email=email, name=profile.name or email.split("@")[0], created_at=now)
        db.add(user)
        await db.flush()
    if identity is None:
        db.add(
            Identity(
                provider=profile.provider,
                provider_user_id=profile.provider_user_id,
                user_id=user.id,
            )
        )
    if profile.name:
        user.name = profile.name
    if profile.avatar_url:
        user.avatar_url = profile.avatar_url
    user.last_login_at = now

    if email in settings.admin_email_set:
        await _grant(db, DEFAULT_PROJECT_ID, user.id, "admin")

    invites = (await db.execute(select(Invitation).where(Invitation.email == email))).scalars()
    for invite in list(invites):
        await _grant(db, invite.project_id, user.id, invite.role)
        await db.delete(invite)

    await db.commit()
    await db.refresh(user)
    return user


async def identities_for(db: AsyncSession, user_id: uuid.UUID) -> list[str]:
    result = await db.execute(select(Identity.provider).where(Identity.user_id == user_id))
    return sorted(set(result.scalars()))
