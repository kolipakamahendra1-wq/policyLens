"""Single-process deployment: the API under /api and the built website at /.

Used where one service has to serve both (e.g. Railway's free plan). Local dev and
docker compose keep the separate nginx frontend.

    STATIC_DIR=frontend/dist uvicorn api.server:app
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.main import app as api_app
from api.main import seed

STATIC_DIR = Path(os.getenv("STATIC_DIR", Path(__file__).resolve().parent.parent / "frontend" / "dist"))


class SPAStaticFiles(StaticFiles):
    """Serve index.html for client-side routes such as /reviews/3."""

    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as e:
            if e.status_code != 404:
                raise
            return await super().get_response("index.html", scope)


@asynccontextmanager
async def lifespan(_app):
    seed()  # mounted sub-apps don't run their own lifespan
    yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/api", api_app)
if STATIC_DIR.is_dir():
    app.mount("/", SPAStaticFiles(directory=STATIC_DIR, html=True), name="site")
