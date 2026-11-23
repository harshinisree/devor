"""Management commands. Usage: python -m app.cli create-admin --email X --password Y"""

import argparse
import asyncio
import sys
from collections.abc import Sequence

from app.core.errors import AppError
from app.db.session import SessionLocal, engine
from app.services.auth_service import AuthService


def _validate_password(password: str) -> None:
    if len(password) < 8:
        raise AppError(400, "invalid_password", "Password must be at least 8 characters")
    if len(password.encode()) > 72:
        raise AppError(400, "invalid_password", "Password must be at most 72 bytes")


async def create_admin(email: str, password: str) -> str:
    """Create an admin user and return its id."""
    _validate_password(password)
    if "@" not in email:
        raise AppError(400, "invalid_email", "Invalid email address")
    async with SessionLocal() as session:
        user = await AuthService(session).create_admin(email, password)
        return str(user.id)


async def _run(args: argparse.Namespace) -> None:
    try:
        user_id = await create_admin(args.email, args.password)
        print(f"Created admin {args.email.strip().lower()} (id={user_id})")
    finally:
        await engine.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("create-admin", help="Create a user with role=admin")
    p.add_argument("--email", required=True)
    p.add_argument("--password", required=True)
    args = parser.parse_args(argv)

    try:
        asyncio.run(_run(args))
    except AppError as exc:
        print(f"error: {exc.message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
