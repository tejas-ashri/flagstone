import secrets
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import Settings, get_settings
from backend.deps import SESSION_COOKIE, check_csrf, get_current_user, get_db
from backend.models.orm import User
from backend.schemas.project import DevLoginRequest, MeResponse, UserResponse
from backend.services import auth_service, oauth, project_service
from backend.services.auth_service import Profile

router = APIRouter(tags=["auth"])

STATE_COOKIE = "flagstone_oauth_state"
NEXT_COOKIE = "flagstone_oauth_next"
STATE_TTL_SECONDS = 600


def _safe_next(path: str | None) -> str:
    # Only same-site relative paths, so the login can't be used as an open redirect.
    if not path or not path.startswith("/") or path.startswith("//") or "\\" in path:
        return "/"
    return path


def _ui(settings: Settings, path: str) -> str:
    return settings.public_url.rstrip("/") + path


def _set_session(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def _login_error(settings: Settings, message: str) -> RedirectResponse:
    response = RedirectResponse(_ui(settings, f"/login?error={quote(message)}"), status_code=302)
    response.delete_cookie(STATE_COOKIE, path="/auth")
    response.delete_cookie(NEXT_COOKIE, path="/auth")
    return response


@router.get("/auth/providers")
async def providers(settings: Settings = Depends(get_settings)):
    return {
        "providers": [
            {"id": p.name, "label": p.label}
            for p in oauth.PROVIDERS.values()
            if p.configured(settings)
        ],
        "dev_login": settings.dev_login,
    }


@router.get("/auth/{provider}/login")
async def login(
    provider: str, next: str | None = None, settings: Settings = Depends(get_settings)
):
    p = oauth.PROVIDERS.get(provider)
    if p is None or not p.configured(settings):
        raise HTTPException(status_code=404, detail=f"Sign-in with '{provider}' is not configured")
    state = secrets.token_urlsafe(24)
    response = RedirectResponse(oauth.authorize_url(p, settings, state), status_code=302)
    cookie = {
        "max_age": STATE_TTL_SECONDS,
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "path": "/auth",
    }
    response.set_cookie(STATE_COOKIE, state, **cookie)
    response.set_cookie(NEXT_COOKIE, _safe_next(next), **cookie)
    return response


@router.get("/auth/{provider}/callback")
async def callback(
    provider: str,
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    p = oauth.PROVIDERS.get(provider)
    if p is None or not p.configured(settings):
        return _login_error(settings, f"Sign-in with '{provider}' is not configured.")
    if error:
        return _login_error(settings, f"{p.label} sign-in was cancelled or failed ({error}).")
    expected = request.cookies.get(STATE_COOKIE)
    if not code or not state or not expected or not secrets.compare_digest(state, expected):
        return _login_error(settings, "Sign-in expired or was started elsewhere. Try again.")
    try:
        profile = await oauth.fetch_profile(p, settings, code)
        user = await auth_service.sign_in(db, profile, settings)
    except oauth.OAuthError as e:
        return _login_error(settings, str(e))
    except ValueError:
        return _login_error(
            settings, f"Your {p.label} account has no verified email address."
        )
    token = await auth_service.create_session(db, user.id, settings)
    response = RedirectResponse(
        _ui(settings, _safe_next(request.cookies.get(NEXT_COOKIE))), status_code=302
    )
    response.delete_cookie(STATE_COOKIE, path="/auth")
    response.delete_cookie(NEXT_COOKIE, path="/auth")
    _set_session(response, token, settings)
    return response


@router.post("/auth/dev-login", response_model=UserResponse)
async def dev_login(
    data: DevLoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if not settings.dev_login:
        raise HTTPException(status_code=404, detail="Not found")
    check_csrf(request)
    email = data.email.strip().lower()
    profile = Profile(
        provider="dev",
        provider_user_id=email,
        email=email,
        email_verified=True,
        name=data.name.strip(),
    )
    user = await auth_service.sign_in(db, profile, settings)
    _set_session(response, await auth_service.create_session(db, user.id, settings), settings)
    return user


@router.post("/auth/logout", status_code=204)
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    check_csrf(request)
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        await auth_service.delete_session(db, token)
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/api/me", response_model=MeResponse)
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return MeResponse(
        user=UserResponse.model_validate(user),
        identities=await auth_service.identities_for(db, user.id),
        projects=await project_service.projects_for(db, user.id),
    )
