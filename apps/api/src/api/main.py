import logging
import random
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette import status

from api.config import FRONTEND_ORIGINS, LOG_REQUEST_SAMPLE_RATE, LOG_SLOW_REQUEST_MS
from api.logging_config import configure_logging
from api.logging_context import request_id_ctx
from api.similarity import EmbeddingNotFoundError
from api.users import MovieNotFoundError, UserNotFoundError
from api.v1.main import router as v1_router

configure_logging()
logger = logging.getLogger("api")

app = FastAPI(title="TMDB RecSys API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request_id_ctx.set(request_id)
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    log_payload = {
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": round(duration_ms, 2),
        "request_id": request_id,
        "client": request.client.host if request.client else None,
    }
    if duration_ms >= LOG_SLOW_REQUEST_MS:
        logger.info("request_complete", extra=log_payload | {"slow": True})
    elif LOG_REQUEST_SAMPLE_RATE > 0 and random.random() < LOG_REQUEST_SAMPLE_RATE:
        logger.info("request_complete", extra=log_payload | {"sampled": True})
    else:
        logger.debug("request_complete", extra=log_payload)
    response.headers["X-Request-ID"] = request_id
    return response


def _error_payload(code: str, message: str, details: object | None = None) -> dict:
    error: dict[str, object] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"error": error}


def _error_response(status_code: int, code: str, message: str, details: object | None = None) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=_error_payload(code, message, details))


_STATUS_CODE_MAP = {
    status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_409_CONFLICT: "CONFLICT",
    status.HTTP_422_UNPROCESSABLE_ENTITY: "VALIDATION_ERROR",
}


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, str):
        message = exc.detail
        details = None
    else:
        message = "Request failed"
        details = exc.detail
    code = _STATUS_CODE_MAP.get(exc.status_code, "HTTP_ERROR")
    return _error_response(exc.status_code, code, message, details)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return _error_response(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "VALIDATION_ERROR",
        "Validation failed",
        exc.errors(),
    )


@app.exception_handler(UserNotFoundError)
async def user_not_found_handler(_request: Request, exc: UserNotFoundError) -> JSONResponse:
    return _error_response(status.HTTP_404_NOT_FOUND, "USER_NOT_FOUND", str(exc))


@app.exception_handler(MovieNotFoundError)
async def movie_not_found_handler(_request: Request, exc: MovieNotFoundError) -> JSONResponse:
    return _error_response(status.HTTP_404_NOT_FOUND, "MOVIE_NOT_FOUND", str(exc))


@app.exception_handler(EmbeddingNotFoundError)
async def embedding_not_found_handler(_request: Request, exc: EmbeddingNotFoundError) -> JSONResponse:
    return _error_response(status.HTTP_404_NOT_FOUND, "EMBEDDING_NOT_FOUND", str(exc))


@app.exception_handler(Exception)
async def generic_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception", exc_info=exc)
    return _error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "INTERNAL_ERROR",
        "An unexpected error occurred",
    )

@app.get("/health")
async def health():
    return {"status": "ok"}

app.include_router(v1_router, prefix="/v1")
