import uvicorn
from fastapi import FastAPI

from config import settings
from db import init_db
from router import calibrate_router, router

app = FastAPI(title="Exam Calibrator", version="0.1.0")
app.include_router(router)
app.include_router(calibrate_router)


@app.on_event("startup")
def startup():
    init_db()


if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=settings.reload)
