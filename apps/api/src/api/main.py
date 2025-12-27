from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import FRONTEND_ORIGINS
from api.v1.main import router as v1_router

app = FastAPI(title="TMDB RecSys API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/v1")
