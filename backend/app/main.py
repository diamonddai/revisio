from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.routes_health import router as health_router
from app.api.routes_simulation import router as simulation_router
from app.api.routes_upload import router as upload_router


def create_app() -> FastAPI:
    Path("storage/uploads").mkdir(parents=True, exist_ok=True)
    Path("storage/cases").mkdir(parents=True, exist_ok=True)
    app = FastAPI(title="Frame Backend", version="0.1.0")

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "errorCode": "BAD_REQUEST",
                "message": "request validation failed",
                "detail": exc.errors(),
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "ok": False,
                "errorCode": "HTTP_ERROR",
                "message": str(exc.detail),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, _exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "errorCode": "INTERNAL_ERROR",
                "message": "internal server error",
            },
        )

    app.include_router(upload_router, prefix="/api")
    app.include_router(simulation_router, prefix="/api")
    app.include_router(health_router, prefix="/api")
    app.mount("/uploads", StaticFiles(directory="storage/uploads"), name="uploads")
    app.mount("/cases", StaticFiles(directory="storage/cases"), name="cases")
    return app


app = create_app()

