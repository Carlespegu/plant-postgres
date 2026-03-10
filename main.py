import os
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Literal, Optional

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Index,
    Integer,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

# =========================
# ENV VARS
# =========================
DATABASE_URL = os.environ.get("DATABASE_URL")
API_KEY = os.environ.get("API_KEY", "")

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
ALERT_FROM_EMAIL = os.environ.get("ALERT_FROM_EMAIL", SMTP_USER)
ALERT_TO_EMAIL = os.environ.get("ALERT_TO_EMAIL", "")

SOIL_ALERT_THRESHOLD = int(os.environ.get("SOIL_ALERT_THRESHOLD", "25"))
ALERT_COOLDOWN_HOURS = int(os.environ.get("ALERT_COOLDOWN_HOURS", "12"))

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL env var is required")

# Render + psycopg2
if DATABASE_URL.startswith("postgresql://"):
    SQLALCHEMY_DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len("postgresql://"):]
elif DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len("postgres://"):]
else:
    SQLALCHEMY_DATABASE_URL = DATABASE_URL

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# =========================
# DB MODELS
# =========================
class Reading(Base):
    __tablename__ = "readings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    device_id = Column(Text, nullable=False)
    ts = Column(DateTime(timezone=True), nullable=False)
    temp_c = Column(Integer, nullable=True)
    hum_air = Column(Integer, nullable=True)
    ldr_raw = Column(Integer, nullable=True)
    soil_percent = Column(Integer, nullable=True)
    rain = Column(Text, nullable=True)   # "rain" | "dry"
    rssi = Column(Integer, nullable=True)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    device_id = Column(Text, nullable=False)
    alert_type = Column(Text, nullable=False)   # e.g. "soil_low"
    value = Column(Integer, nullable=True)
    recipient = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


Index("idx_readings_device_ts", Reading.device_id, Reading.ts.desc())
Index("idx_alerts_device_type_sent_at", Alert.device_id, Alert.alert_type, Alert.sent_at.desc())

Base.metadata.create_all(bind=engine)

# =========================
# SCHEMAS
# =========================
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


# =========================
# APP
# =========================
app = FastAPI(
    title="Plant Station API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # després ho pots restringir al domini del dashboard
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# HELPERS
# =========================
def require_api_key(x_api_key: Optional[str]):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def send_email_alert(device_id: str, soil_percent: int, temp_c: Optional[float], hum_air: Optional[float], ts: datetime) -> bool:
    if not SMTP_USER or not SMTP_PASSWORD or not ALERT_TO_EMAIL:
        print("Email alert skipped: missing SMTP config")
        return False

    msg = EmailMessage()
    msg["Subject"] = f"Alerta de reg - {device_id}"
    msg["From"] = ALERT_FROM_EMAIL
    msg["To"] = ALERT_TO_EMAIL

    body = f"""
La planta necessita atenció.

Dispositiu: {device_id}
Humitat del sòl: {soil_percent}%
Temperatura: {temp_c if temp_c is not None else 'N/D'} °C
Humitat aire: {hum_air if hum_air is not None else 'N/D'} %
Hora: {ts.isoformat()}

Recomanació: cal regar la planta.
""".strip()

    msg.set_content(body)

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.send_message(msg)

    return True


def should_send_soil_alert(db, device_id: str) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=ALERT_COOLDOWN_HOURS)

    recent = (
        db.query(Alert)
        .filter(Alert.device_id == device_id)
        .filter(Alert.alert_type == "soil_low")
        .filter(Alert.sent_at >= cutoff)
        .order_by(Alert.sent_at.desc())
        .first()
    )

    return recent is None


# =========================
# ROUTES
# =========================
@app.get("/")
def root():
    return {"ok": True, "service": "Plant Station API"}


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
            temp_c=int(payload.tempC) if payload.tempC is not None else None,
            hum_air=int(payload.humAir) if payload.humAir is not None else None,
            ldr_raw=payload.ldrRaw,
            soil_percent=payload.soilPercent,
            rain=payload.rain,
            rssi=payload.rssi,
        )
        db.add(row)
        db.commit()
        db.refresh(row)

        # ALERTA EMAIL
        if (
            payload.soilPercent is not None
            and payload.soilPercent < SOIL_ALERT_THRESHOLD
            and should_send_soil_alert(db, payload.deviceId)
        ):
            sent = send_email_alert(
                device_id=payload.deviceId,
                soil_percent=payload.soilPercent,
                temp_c=payload.tempC,
                hum_air=payload.humAir,
                ts=ts,
            )

            if sent:
                db.add(
                    Alert(
                        device_id=payload.deviceId,
                        alert_type="soil_low",
                        value=payload.soilPercent,
                        recipient=ALERT_TO_EMAIL,
                    )
                )
                db.commit()

        return ReadingOut(
            id=int(row.id),
            deviceId=row.device_id,
            ts=row.ts,
            tempC=float(row.temp_c) if row.temp_c is not None else None,
            humAir=float(row.hum_air) if row.hum_air is not None else None,
            ldrRaw=row.ldr_raw,
            soilPercent=row.soil_percent,
            rain=row.rain,
            rssi=row.rssi,
        )
    finally:
        db.close()


@app.get("/api/v1/readings")
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

        return [
            {
                "id": int(r.id),
                "deviceId": r.device_id,
                "ts": r.ts,
                "tempC": float(r.temp_c) if r.temp_c is not None else None,
                "humAir": float(r.hum_air) if r.hum_air is not None else None,
                "ldrRaw": r.ldr_raw,
                "soilPercent": r.soil_percent,
                "rain": r.rain,
                "rssi": r.rssi,
            }
            for r in rows
        ]
    finally:
        db.close()