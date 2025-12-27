from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette import status

from api.config import FRONTEND_ORIGINS
from api.similarity import EmbeddingNotFoundError
from api.users import MovieNotFoundError, UserNotFoundError
from api.v1.main import router as v1_router

app = FastAPI(title="TMDB RecSys API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _error_payload(code: str, message: str, details: object | None = None) -> dict:
    error: dict[str, object] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"error": error}


def _error_response(status_code: int, code: str, message: str, details: object | None = None) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=_error_payload(code, message, details))


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, str):
        message = exc.detail
        details = None
    else:
        message = "Request failed"
        details = exc.detail
    return _error_response(exc.status_code, "HTTP_ERROR", message, details)


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

app.include_router(v1_router, prefix="/v1")
