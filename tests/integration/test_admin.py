import subprocess
import sys
import uuid
from typing import Any

from fastapi import Depends
from httpx import AsyncClient

from app.api.deps import require_approved, require_role
from app.cli import create_admin
from app.main import app
from app.models.user import User
from tests.helpers import unique_email

PASSWORD = "correct-horse-battery"


# Test-only route standing in for future owner/partner-only endpoints.
@app.get(
    "/__test__/approved-only",
    include_in_schema=False,
    dependencies=[Depends(require_role("owner", "partner"))],
)
async def _approved_only(user: User = Depends(require_approved)) -> dict[str, str]:
    return {"id": str(user.id)}


async def _register(client: AsyncClient, role: str) -> dict[str, Any]:
    email = unique_email()
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": PASSWORD, "role": role}
    )
    assert response.status_code == 201, response.text
    return {"email": email, **response.json()}


async def _auth(client: AsyncClient, email: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    email = unique_email()
    await create_admin(email, PASSWORD)
    return await _auth(client, email)


async def test_create_admin_helper_makes_approved_admin(client: AsyncClient) -> None:
    email = unique_email()
    await create_admin(email, PASSWORD)

    me = await client.get("/api/v1/me", headers=await _auth(client, email))

    assert me.status_code == 200
    assert me.json()["role"] == "admin"
    assert me.json()["is_approved"] is True


def test_create_admin_cli_command() -> None:
    email = unique_email()
    cmd = [sys.executable, "-m", "app.cli", "create-admin", "--email", email]

    first = subprocess.run([*cmd, "--password", PASSWORD], capture_output=True, text=True)
    duplicate = subprocess.run([*cmd, "--password", PASSWORD], capture_output=True, text=True)
    weak = subprocess.run(
        [sys.executable, "-m", "app.cli", "create-admin", "--email", unique_email()]
        + ["--password", "short"],
        capture_output=True,
        text=True,
    )

    assert first.returncode == 0, first.stderr
    assert email in first.stdout
    assert duplicate.returncode == 1
    assert "already exists" in duplicate.stderr
    assert weak.returncode == 1


async def test_cannot_create_admin_via_api(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": unique_email(), "password": PASSWORD, "role": "admin"},
    )

    assert response.status_code == 422


async def test_customer_is_auto_approved_owner_and_partner_are_not(client: AsyncClient) -> None:
    customer = await _register(client, "customer")
    owner = await _register(client, "owner")
    partner = await _register(client, "partner")

    assert customer["is_approved"] is True
    assert owner["is_approved"] is False
    assert partner["is_approved"] is False


async def test_non_admin_gets_403_on_admin_routes(client: AsyncClient) -> None:
    customer = await _register(client, "customer")
    headers = await _auth(client, customer["email"])

    pending = await client.get("/api/v1/admin/pending", headers=headers)
    approve = await client.post(f"/api/v1/admin/approve/{uuid.uuid4()}", headers=headers)
    anonymous = await client.get("/api/v1/admin/pending")

    assert pending.status_code == approve.status_code == 403
    assert pending.json()["error"]["code"] == "forbidden"
    assert anonymous.status_code == 401


async def test_pending_lists_only_unapproved_owners_and_partners(client: AsyncClient) -> None:
    admin = await _admin_headers(client)
    customer = await _register(client, "customer")
    owner = await _register(client, "owner")
    partner = await _register(client, "partner")

    response = await client.get("/api/v1/admin/pending", headers=admin)

    assert response.status_code == 200
    items = response.json()
    ids = {u["id"] for u in items}
    assert {owner["id"], partner["id"]} <= ids
    assert customer["id"] not in ids
    assert all(u["role"] in ("owner", "partner") and u["is_approved"] is False for u in items)
    assert all("password_hash" not in u for u in items)


async def test_approve_flow(client: AsyncClient) -> None:
    admin = await _admin_headers(client)
    owner = await _register(client, "owner")
    owner_headers = await _auth(client, owner["email"])

    # Before approval: login works, /me works, but approval-gated routes are 403.
    assert (await client.get("/api/v1/me", headers=owner_headers)).status_code == 200
    blocked = await client.get("/__test__/approved-only", headers=owner_headers)
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "not_approved"

    approved = await client.post(f"/api/v1/admin/approve/{owner['id']}", headers=admin)
    assert approved.status_code == 200
    assert approved.json()["is_approved"] is True

    # Same token now passes (approval is read from the DB on each request).
    allowed = await client.get("/__test__/approved-only", headers=owner_headers)
    assert allowed.status_code == 200
    pending_ids = {
        u["id"] for u in (await client.get("/api/v1/admin/pending", headers=admin)).json()
    }
    assert owner["id"] not in pending_ids


async def test_double_approve_409(client: AsyncClient) -> None:
    admin = await _admin_headers(client)
    partner = await _register(client, "partner")

    first = await client.post(f"/api/v1/admin/approve/{partner['id']}", headers=admin)
    second = await client.post(f"/api/v1/admin/approve/{partner['id']}", headers=admin)

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "already_approved"


async def test_approve_unknown_user_404(client: AsyncClient) -> None:
    admin = await _admin_headers(client)

    response = await client.post(f"/api/v1/admin/approve/{uuid.uuid4()}", headers=admin)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "user_not_found"


async def test_approve_bad_uuid_uses_error_shape(client: AsyncClient) -> None:
    admin = await _admin_headers(client)

    response = await client.post("/api/v1/admin/approve/not-a-uuid", headers=admin)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
