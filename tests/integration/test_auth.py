import uuid
from datetime import timedelta
from typing import Any

from fastapi import Depends
from httpx import AsyncClient

from app.api.deps import require_role
from app.core.security import create_token
from app.main import app
from app.models.user import User
from tests.helpers import unique_email

PASSWORD = "correct-horse-battery"


# Test-only protected route (admin only) to exercise require_role.
@app.get("/__test__/admin-only", include_in_schema=False)
async def _admin_only(user: User = Depends(require_role("admin"))) -> dict[str, str]:
    return {"id": str(user.id)}


async def _register(client: AsyncClient, role: str = "customer") -> dict[str, Any]:
    email = unique_email()
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": PASSWORD, "role": role}
    )
    assert response.status_code == 201, response.text
    return {"email": email, **response.json()}


async def _login(client: AsyncClient, email: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    tokens: dict[str, str] = response.json()
    return tokens


async def test_register_ok(client: AsyncClient) -> None:
    user = await _register(client, "owner")

    assert user["role"] == "owner"
    assert user["is_active"] is True
    assert "password" not in user and "password_hash" not in user
    uuid.UUID(user["id"])


async def test_register_duplicate_email_409(client: AsyncClient) -> None:
    user = await _register(client)

    response = await client.post(
        "/api/v1/auth/register",
        json={"email": user["email"].upper(), "password": PASSWORD, "role": "customer"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"


async def test_register_admin_role_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": unique_email(), "password": PASSWORD, "role": "admin"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_register_short_password_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": unique_email(), "password": "short", "role": "customer"},
    )

    assert response.status_code == 422
    assert set(response.json()) == {"error"}


async def test_login_ok(client: AsyncClient) -> None:
    user = await _register(client)

    tokens = await _login(client, user["email"])

    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"] and tokens["refresh_token"]


async def test_login_wrong_password_and_unknown_email_look_identical(
    client: AsyncClient,
) -> None:
    user = await _register(client)

    wrong_password = await client.post(
        "/api/v1/auth/login", json={"email": user["email"], "password": "not-the-password"}
    )
    unknown_email = await client.post(
        "/api/v1/auth/login", json={"email": unique_email(), "password": PASSWORD}
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


async def test_expired_token_401(client: AsyncClient) -> None:
    user = await _register(client)
    expired = create_token(uuid.UUID(user["id"]), "access", expires_delta=timedelta(seconds=-5))

    response = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {expired}"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "token_expired"


async def test_missing_or_garbage_token_401(client: AsyncClient) -> None:
    missing = await client.get("/api/v1/me")
    garbage = await client.get("/api/v1/me", headers={"Authorization": "Bearer not.a.jwt"})

    assert missing.status_code == garbage.status_code == 401
    assert missing.json()["error"]["code"] == "unauthorized"
    assert garbage.json()["error"]["code"] == "invalid_token"


async def test_refresh_ok_returns_working_access_token(client: AsyncClient) -> None:
    user = await _register(client)
    tokens = await _login(client, user["email"])

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert response.status_code == 200
    new_access = response.json()["access_token"]
    me = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {new_access}"})
    assert me.status_code == 200


async def test_refresh_with_access_token_401(client: AsyncClient) -> None:
    user = await _register(client)
    tokens = await _login(client, user["email"])

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


async def test_refresh_token_cannot_be_used_as_access_token(client: AsyncClient) -> None:
    user = await _register(client)
    tokens = await _login(client, user["email"])

    response = await client.get(
        "/api/v1/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"}
    )

    assert response.status_code == 401


async def test_wrong_role_403(client: AsyncClient) -> None:
    user = await _register(client, "customer")
    tokens = await _login(client, user["email"])

    response = await client.get(
        "/__test__/admin-only", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


async def test_me_returns_user(client: AsyncClient) -> None:
    user = await _register(client, "partner")
    tokens = await _login(client, user["email"])

    response = await client.get(
        "/api/v1/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == user["id"]
    assert body["email"] == user["email"]
    assert body["role"] == "partner"


async def test_unknown_route_uses_error_shape(client: AsyncClient) -> None:
    response = await client.get("/api/v1/nope")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Not Found"}}
