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


API_DESCRIPTION = """
**Exam Calibrator** uses a 1-Parameter Logistic (Rasch) Item Response Theory (IRT) model to analyze exam results.

## Workflow

1. **Record responses** — Use `/responses/attempt` to log student answers (0 = wrong, 1 = correct). Students and questions are created automatically.
2. **Calibrate** — Call `/calibrate` to fit the IRT model and estimate student abilities (θ) and question difficulties (b).
3. **Inspect results** — Fetch `/responses/students` and `/responses/questions` for ability/difficulty estimates, or download `/responses/data` as CSV.
"""

app = FastAPI(
    title="Exam Calibrator",
    description=API_DESCRIPTION,
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(router)
app.include_router(calibrate_router)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Redirect to the docs."""
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    uvicorn.run("fast_api:app", host=settings.host, port=settings.port, reload=settings.reload)
