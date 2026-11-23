from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_livez_returns_ok_without_dependencies() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/livez")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_root_redirects_to_docs() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/docs"
