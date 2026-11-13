import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.deps import ProjectAccess, get_current_user, get_db, project_admin, project_viewer
from backend.models.orm import User
from backend.schemas.project import (
    InviteCreate,
    MembersResponse,
    ProjectCreate,
    ProjectMembershipResponse,
    ProjectUpdate,
    RoleUpdate,
    SdkKeyCreate,
    SdkKeyCreated,
    SdkKeyResponse,
)
from backend.services import project_service, sdk_key_service

router = APIRouter(prefix="/api/projects", tags=["projects"])


async def _summary(db: AsyncSession, user: User, project_id: str) -> ProjectMembershipResponse:
    return next(p for p in await project_service.projects_for(db, user.id) if p.id == project_id)


@router.get("", response_model=list[ProjectMembershipResponse])
async def list_projects(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await project_service.projects_for(db, user.id)


@router.post("", response_model=ProjectMembershipResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await project_service.create_project(db, data.name, user)
    return await _summary(db, user, project.id)


@router.get("/{project_id}", response_model=ProjectMembershipResponse)
async def get_project(
    access: ProjectAccess = Depends(project_viewer), db: AsyncSession = Depends(get_db)
):
    return await _summary(db, access.user, access.project_id)


@router.put("/{project_id}", response_model=ProjectMembershipResponse)
async def rename_project(
    data: ProjectUpdate,
    access: ProjectAccess = Depends(project_admin),
    db: AsyncSession = Depends(get_db),
):
    await project_service.rename_project(db, access.project_id, data.name)
    return await _summary(db, access.user, access.project_id)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    access: ProjectAccess = Depends(project_admin), db: AsyncSession = Depends(get_db)
):
    await project_service.delete_project(db, access.project_id)


# SDK keys


@router.get("/{project_id}/keys", response_model=list[SdkKeyResponse])
async def list_keys(
    access: ProjectAccess = Depends(project_viewer), db: AsyncSession = Depends(get_db)
):
    return await sdk_key_service.list_keys(db, access.project_id)


@router.post("/{project_id}/keys", response_model=SdkKeyCreated, status_code=201)
async def create_key(
    data: SdkKeyCreate,
    access: ProjectAccess = Depends(project_admin),
    db: AsyncSession = Depends(get_db),
):
    row, raw = await sdk_key_service.create_key(db, access.project_id, data.label.strip())
    return SdkKeyCreated(**SdkKeyResponse.model_validate(row).model_dump(), key=raw)


@router.delete("/{project_id}/keys/{key_id}", response_model=SdkKeyResponse)
async def revoke_key(
    key_id: str,
    access: ProjectAccess = Depends(project_admin),
    db: AsyncSession = Depends(get_db),
):
    return await sdk_key_service.revoke_key(db, access.project_id, key_id)


# Members


@router.get("/{project_id}/members", response_model=MembersResponse)
async def list_members(
    access: ProjectAccess = Depends(project_viewer), db: AsyncSession = Depends(get_db)
):
    return await project_service.list_members(db, access.project_id)


@router.post("/{project_id}/members", response_model=MembersResponse, status_code=201)
async def invite_member(
    data: InviteCreate,
    access: ProjectAccess = Depends(project_admin),
    db: AsyncSession = Depends(get_db),
):
    await project_service.invite(db, access.project_id, data.email, data.role, access.user)
    return await project_service.list_members(db, access.project_id)


@router.put("/{project_id}/members/{user_id}", response_model=MembersResponse)
async def change_role(
    user_id: uuid.UUID,
    data: RoleUpdate,
    access: ProjectAccess = Depends(project_admin),
    db: AsyncSession = Depends(get_db),
):
    await project_service.set_role(db, access.project_id, user_id, data.role)
    return await project_service.list_members(db, access.project_id)


@router.delete("/{project_id}/members/{user_id}", response_model=MembersResponse)
async def remove_member(
    user_id: uuid.UUID,
    access: ProjectAccess = Depends(project_admin),
    db: AsyncSession = Depends(get_db),
):
    await project_service.remove_member(db, access.project_id, user_id)
    return await project_service.list_members(db, access.project_id)


@router.delete("/{project_id}/invitations/{email}", response_model=MembersResponse)
async def cancel_invitation(
    email: str,
    access: ProjectAccess = Depends(project_admin),
    db: AsyncSession = Depends(get_db),
):
    await project_service.cancel_invite(db, access.project_id, email)
    return await project_service.list_members(db, access.project_id)
