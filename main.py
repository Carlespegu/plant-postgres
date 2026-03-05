import os
from datetime import datetime, timezone
from typing import Optional, Literal, List

from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import (
    create_engine, Column, BigInteger, Text, Integer, Real, DateTime, Index
)
from sqlalchemy.orm import declarative_base, sessionmaker

# ===== Config via env =====
DATABASE_URL = os.environ.get("DATABASE_URL")  # Render provides this
API_KEY = os.environ.get("API_KEY", "")        # set in Render env vars

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL env var is required")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# ===== DB model =====
class Reading(Base):
    __tablename__ = "readings"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    device_id = Column(Text, nullable=False)
    ts = Column(DateTime(timezone=True), nullable=False)
    temp_c = Column(Real, nullable=True)
    hum_air = Column(Real, nullable=True)
    ldr_raw = Column(Integer, nullable=True)
    soil_percent = Column(Integer, nullable=True)
    rain = Column(Text, nullable=True)  # "rain" | "dry"
    rssi = Column(Integer, nullable=True)

Index("idx_readings_device_ts", Reading.device_id, Reading.ts.desc())

Base.metadata.create_all(bind=engine)

RainType = Literal["rain", "dry"]

class ReadingIn(BaseModel):
    deviceId: str = Field(min_length=1, max_length=64)
    ts: Optional[datetime] = None
    tempC: Optional[float] = None
    humAir: Optional[float] = None
    ldrRaw: Optional[int] = Field(default=None, ge=0, le=4095)
    soilPercent: Optional[int] = Field(default=None, ge=0, le=100)
    rain: Optional[RainType] = None
    rssi: Optional[int] = Field(default=None, ge=-120, le=0)

class ReadingOut(BaseModel):
    id: int
    deviceId: str
    ts: datetime
    tempC: Optional[float]
    humAir: Optional[float]
    ldrRaw: Optional[int]
    soilPercent: Optional[int]
    rain: Optional[str]
    rssi: Optional[int]

app = FastAPI(title="Plant Station API", version="1.0.0")

def require_api_key(x_api_key: Optional[str]):
    # If API_KEY not set, allow early tests. Set it in Render for production.
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/api/v1/readings", response_model=ReadingOut)
def create_reading(payload: ReadingIn, x_api_key: Optional[str] = Header(default=None)):
    require_api_key(x_api_key)

    ts = payload.ts
    if ts is None:
        ts = datetime.now(timezone.utc)
    elif ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    db = SessionLocal()
    try:
        row = Reading(
            device_id=payload.deviceId,
            ts=ts,
            temp_c=payload.tempC,
            hum_air=payload.humAir,
            ldr_raw=payload.ldrRaw,
            soil_percent=payload.soilPercent,
            rain=payload.rain,
            rssi=payload.rssi,
        )
        db.add(row)
        db.commit()
        db.refresh(row)

        return ReadingOut(
            id=int(row.id),
            deviceId=row.device_id,
            ts=row.ts,
            tempC=row.temp_c,
            humAir=row.hum_air,
            ldrRaw=row.ldr_raw,
            soilPercent=row.soil_percent,
            rain=row.rain,
            rssi=row.rssi,
        )
    finally:
        db.close()

@app.get("/api/v1/readings", response_model=List[ReadingOut])
def list_readings(
    deviceId: str = Query(..., min_length=1, max_length=64),
    limit: int = Query(200, ge=1, le=2000),
    from_ts: Optional[datetime] = Query(None, alias="from"),
    to_ts: Optional[datetime] = Query(None, alias="to"),
    x_api_key: Optional[str] = Header(default=None),
):
    require_api_key(x_api_key)

    if from_ts and from_ts.tzinfo is None:
        from_ts = from_ts.replace(tzinfo=timezone.utc)
    if to_ts and to_ts.tzinfo is None:
        to_ts = to_ts.replace(tzinfo=timezone.utc)

    db = SessionLocal()
    try:
        q = db.query(Reading).filter(Reading.device_id == deviceId)
        if from_ts:
            q = q.filter(Reading.ts >= from_ts)
        if to_ts:
            q = q.filter(Reading.ts <= to_ts)

        rows = q.order_by(Reading.ts.desc()).limit(limit).all()
        out: List[ReadingOut] = []
        for r in rows:
            out.append(ReadingOut(
                id=int(r.id),
                deviceId=r.device_id,
                ts=r.ts,
                tempC=r.temp_c,
                humAir=r.hum_air,
                ldrRaw=r.ldr_raw,
                soilPercent=r.soil_percent,
                rain=r.rain,
                rssi=r.rssi
            ))
        return out
    finally:
        db.close()