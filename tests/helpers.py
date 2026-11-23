import uuid


def unique_email() -> str:
    # Unique per call, so tests don't need to clean the DB between runs.
    return f"user-{uuid.uuid4().hex[:12]}@example.com"
