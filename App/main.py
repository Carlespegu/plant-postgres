from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from App.api.routes.readings import router as readings_router
from App.db.base import Base
from App.db.session import engine

# Important: importa els models perquè SQLAlchemy conegui el metadata
from App.db.models import *  # noqa: F401,F403

app = FastAPI(
    title="Plant Station API",
    version="2.0.0",
    description="IoT backend for plants, installations, assets and readings",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    # Per entorns locals o proves.
    # En producció, millor que l'esquema el controli el teu SQL oficial.
    Base.metadata.create_all(bind=engine)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


app.include_router(readings_router)