from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from App.api.routes.readings import router as readings_router
from App.db.base import Base
from App.db.session import engine

app = FastAPI(title="Plant Station API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(readings_router)