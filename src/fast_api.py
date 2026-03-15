from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from config import settings
from db import init_db
from router import calibrate_router, router


@asynccontextmanager
async def lifespan(app: FastAPI):  # pyright: ignore[reportUnusedParameter]
    """Initialize the database."""
    init_db()
    yield


app = FastAPI(title="Exam Calibrator", version="0.1.0", lifespan=lifespan)
app.include_router(router)
app.include_router(calibrate_router)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Redirect to the docs."""
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    uvicorn.run("fast_api:app", host=settings.host, port=settings.port, reload=settings.reload)
