"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import init_db
from app.routes import auth, integration, projects, recommendations, teams, users

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    try:
        await init_db()
        logger.info("Database initialized (%s)", settings.database_url.split("@")[-1])
    except Exception:
        # Don't crash the whole process if DB init fails; surface errors per-request instead.
        logger.exception("Database init failed — the service will still start, "
                         "but DB-bound endpoints will return 500 until fixed.")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title=settings.app_name,
    description=(
        "Microservice in charge of users, authentication, teams and projects "
        "for the Intelligent Documentation Platform.\n\n"
        "Sibling modules can validate sessions via `GET /api/auth/validate` "
        "and fetch user data via `GET /api/users/{id}`."
    ),
    version=settings.app_version,
    lifespan=lifespan,
)


# ---------------- middleware ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------- global error handlers ----------------
@app.exception_handler(StarletteHTTPException)
async def _http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def _validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": exc.errors()},
    )


@app.exception_handler(SQLAlchemyError)
async def _db_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.exception("Database error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Database temporarily unavailable. Please retry."},
    )


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# ---------------- routers ----------------
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(teams.router)
app.include_router(projects.router)
app.include_router(recommendations.router)
app.include_router(integration.router)


# ---------------- service endpoints ----------------
@app.get("/health", tags=["health"])
async def health_check():
    """Liveness probe — used by orchestrators and by sibling modules."""
    return {"status": "healthy", "service": settings.app_name, "version": settings.app_version}


@app.get("/api/integration/config", tags=["integration"])
async def integration_config():
    """Return URLs of sibling microservices so the frontend can link to them.

    Other modules of the platform should advertise their public base URL via
    the corresponding ``*_SERVICE_URL`` env vars. ``null`` means the module
    isn't deployed yet — the UI shows a disabled placeholder."""
    return {
        "this_service": {"name": settings.app_name, "version": settings.app_version},
        "modules": {
            "ingestion": settings.ingestion_service_url or None,
            "reports": settings.reports_service_url or None,
            "presentations": settings.presentations_service_url or None,
            "diagrams": settings.diagrams_service_url or None,
            "chat": settings.chat_service_url or None,
        },
    }


# ---------------- static frontend ----------------
_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if _FRONTEND_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(_FRONTEND_DIR), html=False), name="static")

    @app.get("/", include_in_schema=False)
    async def _serve_index():
        return FileResponse(str(_FRONTEND_DIR / "index.html"))

    @app.get("/app/{path:path}", include_in_schema=False)
    async def _serve_spa(path: str):
        target = _FRONTEND_DIR / path
        if target.is_file():
            return FileResponse(str(target))
        return FileResponse(str(_FRONTEND_DIR / "index.html"))
else:
    @app.get("/", tags=["root"])
    async def root():
        return {
            "message": f"Welcome to {settings.app_name}",
            "version": settings.app_version,
            "docs": "/docs",
            "redoc": "/redoc",
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
