from fastapi import FastAPI

app = FastAPI(title="Devor")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}