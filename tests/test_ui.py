import httpx
import pytest
from backend.config import get_settings
from backend.main import create_app


@pytest.fixture
def make_ui_client(tmp_path, monkeypatch):
    """Builds the full app with UI_DIST_DIR pointing at a fake UI build."""

    def make(ui_dir):
        monkeypatch.setenv("UI_DIST_DIR", str(ui_dir))
        get_settings.cache_clear()
        app = create_app()
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")

    yield make
    get_settings.cache_clear()


@pytest.fixture
def dist(tmp_path):
    d = tmp_path / "dist"
    (d / "assets").mkdir(parents=True)
    (d / "index.html").write_text("<html>flagstone ui</html>")
    (d / "assets" / "app-1a2b3c.js").write_text("console.log('app')")
    (d / "vite.svg").write_text("<svg/>")
    (tmp_path / "secret.txt").write_text("outside the UI folder")
    return d


async def test_root_serves_index(make_ui_client, dist):
    async with make_ui_client(dist) as c:
        resp = await c.get("/")
    assert resp.status_code == 200
    assert "flagstone ui" in resp.text
    assert resp.headers["cache-control"] == "no-cache"


async def test_client_side_route_serves_index(make_ui_client, dist):
    async with make_ui_client(dist) as c:
        resp = await c.get("/projects/default/flags/checkout/results")
    assert resp.status_code == 200
    assert "flagstone ui" in resp.text


async def test_static_files_served_with_cache_headers(make_ui_client, dist):
    async with make_ui_client(dist) as c:
        asset = await c.get("/assets/app-1a2b3c.js")
        icon = await c.get("/vite.svg")
    assert asset.status_code == 200
    assert asset.text == "console.log('app')"
    assert "immutable" in asset.headers["cache-control"]
    assert icon.status_code == 200
    assert icon.headers["cache-control"] == "no-cache"


async def test_head_requests_supported(make_ui_client, dist):
    async with make_ui_client(dist) as c:
        asset = await c.head("/assets/app-1a2b3c.js")
        page = await c.head("/projects/default/flags")
    assert asset.status_code == 200
    assert "immutable" in asset.headers["cache-control"]
    assert page.status_code == 200


@pytest.mark.parametrize("path", ["/api/nope", "/api", "/auth/nope", "/sdk/nope"])
async def test_unknown_backend_paths_are_404_not_ui(make_ui_client, dist, path):
    async with make_ui_client(dist) as c:
        resp = await c.get(path)
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Not Found"}


async def test_api_routes_still_take_precedence(make_ui_client, dist):
    async with make_ui_client(dist) as c:
        providers = await c.get("/auth/providers")
        docs = await c.get("/docs")
    assert providers.status_code == 200
    assert "providers" in providers.json()
    assert docs.status_code == 200
    assert "flagstone ui" not in docs.text


async def test_files_outside_ui_folder_are_not_served(make_ui_client, dist):
    async with make_ui_client(dist) as c:
        resp = await c.get("/assets/%2e%2e/%2e%2e/secret.txt")
    assert "outside the UI folder" not in resp.text


async def test_ui_not_served_when_not_built(make_ui_client, tmp_path):
    async with make_ui_client(tmp_path / "missing") as c:
        resp = await c.get("/")
    assert resp.status_code == 404
