import uuid
from typing import Any

from httpx import AsyncClient

from app.cli import create_admin
from tests.helpers import unique_email

PASSWORD = "correct-horse-battery"
VALID = {
    "name": "Spice Garden",
    "cuisine": "indian",
    "address": "12 MG Road, Bengaluru",
    "lat": 12.9716,
    "lng": 77.5946,
}


async def _login(client: AsyncClient, email: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _user(client: AsyncClient, role: str, approved: bool = True) -> dict[str, str]:
    """Register a user and return auth headers; owners are approved by a fresh admin."""
    email = unique_email()
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": PASSWORD, "role": role}
    )
    assert response.status_code == 201, response.text
    if role == "owner" and approved:
        admin_email = unique_email()
        await create_admin(admin_email, PASSWORD)
        admin = await _login(client, admin_email)
        done = await client.post(f"/api/v1/admin/approve/{response.json()['id']}", headers=admin)
        assert done.status_code == 200, done.text
    return await _login(client, email)


async def _create(client: AsyncClient, headers: dict[str, str], **overrides: Any) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/restaurants", json={**VALID, **overrides}, headers=headers
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def test_create_restaurant_ok(client: AsyncClient) -> None:
    owner = await _user(client, "owner")
    me = (await client.get("/api/v1/me", headers=owner)).json()

    restaurant = await _create(client, owner)

    assert restaurant["owner_id"] == me["id"]
    assert restaurant["name"] == "Spice Garden"
    assert restaurant["is_open"] is False
    assert restaurant["created_at"]
    uuid.UUID(restaurant["id"])


async def test_owner_can_have_several_restaurants(client: AsyncClient) -> None:
    owner = await _user(client, "owner")

    first = await _create(client, owner, name="First Place")
    second = await _create(client, owner, name="Second Place")

    assert first["id"] != second["id"]
    assert first["owner_id"] == second["owner_id"]


async def test_unapproved_owner_403(client: AsyncClient) -> None:
    owner = await _user(client, "owner", approved=False)

    response = await client.post("/api/v1/restaurants", json=VALID, headers=owner)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_approved"


async def test_customer_403(client: AsyncClient) -> None:
    customer = await _user(client, "customer")

    response = await client.post("/api/v1/restaurants", json=VALID, headers=customer)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


async def test_anonymous_create_401(client: AsyncClient) -> None:
    response = await client.post("/api/v1/restaurants", json=VALID)

    assert response.status_code == 401


async def test_edit_own_restaurant(client: AsyncClient) -> None:
    owner = await _user(client, "owner")
    restaurant = await _create(client, owner)

    response = await client.patch(
        f"/api/v1/restaurants/{restaurant['id']}",
        json={"name": "Spice Garden 2", "cuisine": "thai"},
        headers=owner,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Spice Garden 2"
    assert body["cuisine"] == "thai"
    assert body["address"] == VALID["address"]  # untouched fields stay as they were


async def test_edit_other_owners_restaurant_403(client: AsyncClient) -> None:
    owner = await _user(client, "owner")
    other = await _user(client, "owner")
    restaurant = await _create(client, owner)

    edit = await client.patch(
        f"/api/v1/restaurants/{restaurant['id']}", json={"name": "Hijacked"}, headers=other
    )
    toggle = await client.patch(
        f"/api/v1/restaurants/{restaurant['id']}/open", json={"is_open": True}, headers=other
    )

    assert edit.status_code == toggle.status_code == 403
    assert edit.json()["error"]["code"] == "forbidden"
    unchanged = (await client.get(f"/api/v1/restaurants/{restaurant['id']}")).json()
    assert unchanged["name"] == "Spice Garden"
    assert unchanged["is_open"] is False


async def test_edit_unknown_restaurant_404(client: AsyncClient) -> None:
    owner = await _user(client, "owner")

    response = await client.patch(
        f"/api/v1/restaurants/{uuid.uuid4()}", json={"name": "Nope Nope"}, headers=owner
    )

    assert response.status_code == 404


async def test_open_and_close(client: AsyncClient) -> None:
    owner = await _user(client, "owner")
    restaurant = await _create(client, owner)
    url = f"/api/v1/restaurants/{restaurant['id']}/open"

    opened = await client.patch(url, json={"is_open": True}, headers=owner)
    closed = await client.patch(url, json={"is_open": False}, headers=owner)

    assert opened.status_code == 200 and opened.json()["is_open"] is True
    assert closed.status_code == 200 and closed.json()["is_open"] is False


async def test_get_is_public(client: AsyncClient) -> None:
    owner = await _user(client, "owner")
    restaurant = await _create(client, owner)

    response = await client.get(f"/api/v1/restaurants/{restaurant['id']}")  # no auth header

    assert response.status_code == 200
    assert response.json() == restaurant


async def test_get_missing_404(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/restaurants/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "restaurant_not_found", "message": "Restaurant not found"}
    }


async def test_bad_lat_422_in_error_shape(client: AsyncClient) -> None:
    owner = await _user(client, "owner")

    response = await client.post("/api/v1/restaurants", json={**VALID, "lat": 91}, headers=owner)

    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == "validation_error"
    assert "lat" in body["error"]["message"]


async def test_other_validation_rules_422(client: AsyncClient) -> None:
    owner = await _user(client, "owner")
    bad_payloads = [
        {**VALID, "lat": -90.5},
        {**VALID, "lng": 180.1},
        {**VALID, "lng": -181},
        {**VALID, "name": "A"},
        {**VALID, "name": "x" * 101},
        {**VALID, "name": "   "},
    ]

    for payload in bad_payloads:
        response = await client.post("/api/v1/restaurants", json=payload, headers=owner)
        assert response.status_code == 422, payload
        assert response.json()["error"]["code"] == "validation_error"


async def test_boundary_coordinates_accepted(client: AsyncClient) -> None:
    owner = await _user(client, "owner")

    restaurant = await _create(client, owner, lat=-90, lng=180, name="Ab")

    assert restaurant["lat"] == -90
    assert restaurant["lng"] == 180


async def test_patch_validates_and_rejects_empty_or_null(client: AsyncClient) -> None:
    owner = await _user(client, "owner")
    restaurant = await _create(client, owner)
    url = f"/api/v1/restaurants/{restaurant['id']}"

    bad_lat = await client.patch(url, json={"lat": 200}, headers=owner)
    empty = await client.patch(url, json={}, headers=owner)
    null_name = await client.patch(url, json={"name": None}, headers=owner)

    assert bad_lat.status_code == empty.status_code == null_name.status_code == 422
