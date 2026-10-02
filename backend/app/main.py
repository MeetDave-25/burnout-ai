"""BurnoutAI: one service that serves the API under /api and the built website for everything else.

Run (development):  uvicorn app.main:app --reload        (from backend/; the Vite dev server proxies /api here)
Run (production):   see Dockerfile / README → Deploy
API docs:           http://localhost:8000/api/docs (development only)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .config import settings
from .ml.predictor import get_predictor
from .routers import accounts, orgs, public

log = logging.getLogger("burnoutai")


# ── The API (mounted at /api) ────────────────────────────────────

api = FastAPI(
    title="BurnoutAI API",
    version="1.0.0",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None,
    openapi_url=None if settings.is_production else "/openapi.json",
)
if not settings.is_production:  # same-origin in production; only the Vite dev server needs CORS
    api.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])
api.include_router(public.router, tags=["public"])
api.include_router(accounts.router, tags=["accounts"])
api.include_router(orgs.router, tags=["organisations"])


# ── The site ─────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.is_production and (issues := settings.problems()):
        raise RuntimeError("Refusing to start in production:\n  - " + "\n  - ".join(issues))
    if settings.auto_migrate:
        from .migrate import upgrade

        upgrade()
    get_predictor()  # load the model + SHAP explainer once
    if not settings.frontend_dist.joinpath("index.html").exists():
        log.warning("No built website at %s. Run `npm run build` in frontend/ (API still works).", settings.frontend_dist)
    yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    for k, v in SECURITY_HEADERS.items():
        response.headers.setdefault(k, v)
    if settings.cookie_secure:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


app.mount("/api", api)


@app.get("/{path:path}", include_in_schema=False)
def website(path: str):
    """Static files from the built site; any other path gets index.html so client-side routes work on refresh."""
    dist = settings.frontend_dist.resolve()
    index = dist / "index.html"
    if not index.exists():
        raise HTTPException(404, "Website not built. Run `npm run build` in frontend/")
    target = (dist / path).resolve()
    if path and target.is_file() and dist in target.parents:
        immutable = path.startswith("assets/")  # Vite fingerprints these, so they can be cached forever
        return FileResponse(target, headers={"Cache-Control": "public, max-age=31536000, immutable" if immutable
                                             else "public, max-age=3600"})
    return FileResponse(index, headers={"Cache-Control": "no-cache"})
