from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from backend.config import Settings
from backend.services.auth_service import Profile


class OAuthError(Exception):
    pass


@dataclass(frozen=True)
class Provider:
    name: str
    label: str
    authorize_url: str
    scope: str

    def credentials(self, settings: Settings) -> tuple[str, str]:
        return (
            getattr(settings, f"{self.name}_client_id"),
            getattr(settings, f"{self.name}_client_secret"),
        )

    def configured(self, settings: Settings) -> bool:
        return all(self.credentials(settings))


PROVIDERS = {
    p.name: p
    for p in [
        Provider(
            "github", "GitHub", "https://github.com/login/oauth/authorize", "read:user user:email"
        ),
        Provider(
            "google",
            "Google",
            "https://accounts.google.com/o/oauth2/v2/auth",
            "openid email profile",
        ),
        Provider(
            "slack", "Slack", "https://slack.com/openid/connect/authorize", "openid email profile"
        ),
    ]
}


def redirect_uri(settings: Settings, provider: str) -> str:
    return f"{settings.public_url.rstrip('/')}/auth/{provider}/callback"


def authorize_url(provider: Provider, settings: Settings, state: str) -> str:
    client_id, _ = provider.credentials(settings)
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri(settings, provider.name),
        "scope": provider.scope,
        "state": state,
        "response_type": "code",
    }
    if provider.name == "google":
        params["prompt"] = "select_account"
    return f"{provider.authorize_url}?{urlencode(params)}"


def _json(resp: httpx.Response, what: str) -> dict:
    if resp.status_code >= 400:
        raise OAuthError(f"{what} failed ({resp.status_code})")
    try:
        return resp.json()
    except ValueError as e:
        raise OAuthError(f"{what} returned an unreadable response") from e


async def _github(http: httpx.AsyncClient, code: str, cid: str, secret: str, uri: str) -> Profile:
    token = _json(
        await http.post(
            "https://github.com/login/oauth/access_token",
            data={"client_id": cid, "client_secret": secret, "code": code, "redirect_uri": uri},
            headers={"Accept": "application/json"},
        ),
        "GitHub token exchange",
    )
    access = token.get("access_token")
    if not access:
        raise OAuthError(token.get("error_description") or "GitHub did not return a token")
    headers = {"Authorization": f"Bearer {access}", "Accept": "application/vnd.github+json"}
    user = _json(await http.get("https://api.github.com/user", headers=headers), "GitHub profile")
    emails = _json(
        await http.get("https://api.github.com/user/emails", headers=headers), "GitHub emails"
    )
    primary = next((e for e in emails if e.get("primary") and e.get("verified")), None)
    verified = primary or next((e for e in emails if e.get("verified")), None)
    return Profile(
        provider="github",
        provider_user_id=str(user["id"]),
        email=verified["email"] if verified else "",
        email_verified=verified is not None,
        name=user.get("name") or user.get("login") or "",
        avatar_url=user.get("avatar_url"),
    )


async def _google(http: httpx.AsyncClient, code: str, cid: str, secret: str, uri: str) -> Profile:
    token = _json(
        await http.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": cid,
                "client_secret": secret,
                "code": code,
                "redirect_uri": uri,
                "grant_type": "authorization_code",
            },
        ),
        "Google token exchange",
    )
    info = _json(
        await http.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {token['access_token']}"},
        ),
        "Google profile",
    )
    return Profile(
        provider="google",
        provider_user_id=info["sub"],
        email=info.get("email", ""),
        email_verified=info.get("email_verified") is True,
        name=info.get("name", ""),
        avatar_url=info.get("picture"),
    )


async def _slack(http: httpx.AsyncClient, code: str, cid: str, secret: str, uri: str) -> Profile:
    # Slack reports errors as HTTP 200 with {"ok": false, "error": "..."}.
    token = _json(
        await http.post(
            "https://slack.com/api/openid.connect.token",
            data={"client_id": cid, "client_secret": secret, "code": code, "redirect_uri": uri},
        ),
        "Slack token exchange",
    )
    if not token.get("ok"):
        raise OAuthError(f"Slack token exchange failed: {token.get('error', 'unknown error')}")
    info = _json(
        await http.get(
            "https://slack.com/api/openid.connect.userInfo",
            headers={"Authorization": f"Bearer {token['access_token']}"},
        ),
        "Slack profile",
    )
    if not info.get("ok"):
        raise OAuthError(f"Slack profile failed: {info.get('error', 'unknown error')}")
    return Profile(
        provider="slack",
        provider_user_id=info["sub"],
        email=info.get("email", ""),
        email_verified=info.get("email_verified") is True,
        name=info.get("name", ""),
        avatar_url=info.get("picture"),
    )


_EXCHANGERS = {"github": _github, "google": _google, "slack": _slack}


async def fetch_profile(provider: Provider, settings: Settings, code: str) -> Profile:
    client_id, secret = provider.credentials(settings)
    async with httpx.AsyncClient(timeout=10) as http:
        try:
            return await _EXCHANGERS[provider.name](
                http, code, client_id, secret, redirect_uri(settings, provider.name)
            )
        except httpx.HTTPError as e:
            raise OAuthError(f"Could not reach {provider.label}") from e
        except (KeyError, TypeError) as e:
            raise OAuthError(f"Unexpected response from {provider.label}") from e
