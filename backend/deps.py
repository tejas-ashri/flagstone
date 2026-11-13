from collections.abc import AsyncIterator
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.sse_manager import SSEConnectionManager
from backend.models.orm import DEFAULT_PROJECT_ID, Membership, User
from backend.services import auth_service

SESSION_COOKIE = "flagstone_session"
# Browsers only send custom headers cross-origin after a CORS preflight, which
# this API never approves, so requiring one blocks cross-site form posts.
CSRF_HEADER = "x-requested-with"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    factory = request.app.state.session_factory
    async with factory() as session:
        yield session


def get_sse_manager(request: Request) -> SSEConnectionManager:
    return request.app.state.sse_manager


def check_csrf(request: Request) -> None:
    if request.method not in SAFE_METHODS and request.headers.get(CSRF_HEADER) != "flagstone":
        raise HTTPException(status_code=403, detail="Missing X-Requested-With header")


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    check_csrf(request)
    token = request.cookies.get(SESSION_COOKIE)
    user = await auth_service.user_for_session(db, token) if token else None
    if user is None:
        raise HTTPException(status_code=401, detail="Not signed in")
    return user


@dataclass
class ProjectAccess:
    project_id: str
    role: str
    user: User

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


async def project_viewer(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectAccess:
    # Routes are mounted under /api/projects/{project_id}/... and, for backward
    # compatibility, under /api/... where they act on the Default project.
    project_id = request.path_params.get("project_id", DEFAULT_PROJECT_ID)
    membership = await db.get(Membership, {"project_id": project_id, "user_id": user.id})
    if membership is None:
        # Same answer as a missing project, so project ids can't be probed.
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectAccess(project_id=project_id, role=membership.role, user=user)


async def project_admin(access: ProjectAccess = Depends(project_viewer)) -> ProjectAccess:
    if not access.is_admin:
        raise HTTPException(status_code=403, detail="Only project admins can do this")
    return access
