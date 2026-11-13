import re
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.orm import (
    DEFAULT_PROJECT_ID,
    FeatureEvent,
    Flag,
    Invitation,
    Membership,
    Project,
    SdkKey,
    User,
)
from backend.schemas.project import (
    InvitationResponse,
    MemberResponse,
    MembersResponse,
    ProjectMembershipResponse,
    UserResponse,
)


def _new_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:30] or "project"
    return f"{slug}-{secrets.token_hex(3)}"


async def projects_for(db: AsyncSession, user_id: uuid.UUID) -> list[ProjectMembershipResponse]:
    flag_counts = (
        select(Flag.project_id, func.count().label("n")).group_by(Flag.project_id).subquery()
    )
    member_counts = (
        select(Membership.project_id, func.count().label("n"))
        .group_by(Membership.project_id)
        .subquery()
    )
    rows = await db.execute(
        select(
            Project.id,
            Project.name,
            Membership.role,
            func.coalesce(flag_counts.c.n, 0),
            func.coalesce(member_counts.c.n, 0),
        )
        .join(Membership, Membership.project_id == Project.id)
        .outerjoin(flag_counts, flag_counts.c.project_id == Project.id)
        .outerjoin(member_counts, member_counts.c.project_id == Project.id)
        .where(Membership.user_id == user_id)
        .order_by(Project.name)
    )
    return [
        ProjectMembershipResponse(
            id=pid, name=name, role=role, flag_count=flags, member_count=members
        )
        for pid, name, role, flags, members in rows
    ]


async def create_project(db: AsyncSession, name: str, owner: User) -> Project:
    now = datetime.now(timezone.utc)
    project = Project(id=_new_id(name), name=name, created_at=now)
    db.add(project)
    await db.flush()
    db.add(Membership(project_id=project.id, user_id=owner.id, role="admin", created_at=now))
    await db.commit()
    await db.refresh(project)
    return project


async def get_project(db: AsyncSession, project_id: str) -> Project:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def rename_project(db: AsyncSession, project_id: str, name: str) -> Project:
    project = await get_project(db, project_id)
    project.name = name
    await db.commit()
    await db.refresh(project)
    return project


async def delete_project(db: AsyncSession, project_id: str) -> None:
    if project_id == DEFAULT_PROJECT_ID:
        raise HTTPException(status_code=400, detail="The Default project cannot be deleted")
    project = await get_project(db, project_id)
    # Explicit deletes so this also works where foreign keys aren't enforced.
    for model in (FeatureEvent, Flag, SdkKey, Invitation, Membership):
        await db.execute(delete(model).where(model.project_id == project_id))
    await db.delete(project)
    await db.commit()


async def list_members(db: AsyncSession, project_id: str) -> MembersResponse:
    rows = await db.execute(
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .where(Membership.project_id == project_id)
        .order_by(User.email)
    )
    invites = await db.execute(
        select(Invitation).where(Invitation.project_id == project_id).order_by(Invitation.email)
    )
    return MembersResponse(
        members=[
            MemberResponse(
                user=UserResponse.model_validate(u), role=m.role, created_at=m.created_at
            )
            for m, u in rows
        ],
        invitations=[
            InvitationResponse(email=i.email, role=i.role, created_at=i.created_at)
            for i in invites.scalars()
        ],
    )


async def invite(
    db: AsyncSession, project_id: str, email: str, role: str, invited_by: User
) -> None:
    """Adds an existing user directly; otherwise records an invitation that is
    applied the first time someone signs in with that email."""
    now = datetime.now(timezone.utc)
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is not None:
        existing = await db.get(Membership, {"project_id": project_id, "user_id": user.id})
        if existing is not None:
            raise HTTPException(status_code=409, detail=f"{email} is already a member")
        db.add(Membership(project_id=project_id, user_id=user.id, role=role, created_at=now))
    else:
        existing = await db.get(Invitation, {"project_id": project_id, "email": email})
        if existing is not None:
            existing.role = role
        else:
            db.add(
                Invitation(
                    project_id=project_id,
                    email=email,
                    role=role,
                    invited_by=invited_by.id,
                    created_at=now,
                )
            )
    await db.commit()


async def _admin_count(db: AsyncSession, project_id: str) -> int:
    return (
        await db.execute(
            select(func.count())
            .select_from(Membership)
            .where(Membership.project_id == project_id, Membership.role == "admin")
        )
    ).scalar_one()


async def _membership(db: AsyncSession, project_id: str, user_id: uuid.UUID) -> Membership:
    m = await db.get(Membership, {"project_id": project_id, "user_id": user_id})
    if m is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return m


async def set_role(db: AsyncSession, project_id: str, user_id: uuid.UUID, role: str) -> None:
    m = await _membership(db, project_id, user_id)
    if m.role == "admin" and role != "admin" and await _admin_count(db, project_id) <= 1:
        raise HTTPException(status_code=400, detail="A project needs at least one admin")
    m.role = role
    await db.commit()


async def remove_member(db: AsyncSession, project_id: str, user_id: uuid.UUID) -> None:
    m = await _membership(db, project_id, user_id)
    if m.role == "admin" and await _admin_count(db, project_id) <= 1:
        raise HTTPException(status_code=400, detail="A project needs at least one admin")
    await db.delete(m)
    await db.commit()


async def cancel_invite(db: AsyncSession, project_id: str, email: str) -> None:
    invite_row = await db.get(Invitation, {"project_id": project_id, "email": email.lower()})
    if invite_row is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    await db.delete(invite_row)
    await db.commit()
