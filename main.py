import os
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import FastAPI, Depends, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("plant-station")


DATABASE_URL = os.getenv("DATABASE_URL")
API_KEY = os.getenv("API_KEY", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
ALERT_FROM_EMAIL = os.getenv("ALERT_FROM_EMAIL", "Plant Station <onboarding@resend.dev>")
ALERT_TO_EMAIL = os.getenv("ALERT_TO_EMAIL", "")
SOIL_ALERT_THRESHOLD = float(os.getenv("SOIL_ALERT_THRESHOLD", "25"))
ALERT_COOLDOWN_HOURS = int(os.getenv("ALERT_COOLDOWN_HOURS", "12"))
EMAIL_MODE = os.getenv("EMAIL_MODE", "resend")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


# ------------------------------
# DATABASE MODELS
# ------------------------------

class ReadingDB(Base):
    __tablename__ = "readings"

    id = Column(Integer, primary_key=True, index=True)
    deviceId = Column("device_id", String(100), nullable=False, index=True)
    ts = Column(DateTime(timezone=True), nullable=False, index=True, default=lambda: datetime.now(timezone.utc))
    tempC = Column("temp_c", Float, nullable=True)
    humAir = Column("hum_air", Float, nullable=True)
    ldrRaw = Column("ldr_raw", Integer, nullable=True)
    soilPercent = Column("soil_percent", Float, nullable=True)
    rain = Column(Text, nullable=True)
    rssi = Column(Integer, nullable=True)


class AlertDB(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    deviceId = Column("device_id", String(100), nullable=False, index=True)
    alertType = Column("alert_type", String(50), nullable=False, index=True)
    value = Column(Integer, nullable=True)
    recipient = Column(String(255), nullable=True)
    sentAt = Column("sent_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


def create_tables():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ------------------------------
# SCHEMAS
# ------------------------------

class ReadingIn(BaseModel):
    deviceId: str
    ts: Optional[datetime] = None
    tempC: Optional[float] = None
    humAir: Optional[float] = None
    ldrRaw: Optional[int] = None
    soilPercent: Optional[float] = None
    rain: Optional[str] = None
    rssi: Optional[int] = None


class ReadingOut(BaseModel):
    id: int
    deviceId: str
    ts: datetime
    tempC: Optional[float]
    humAir: Optional[float]
    ldrRaw: Optional[int]
    soilPercent: Optional[float]
    rain: Optional[str]
    rssi: Optional[int]

    model_config = ConfigDict(from_attributes=True)


# ------------------------------
# SECURITY
# ------------------------------

def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


# ------------------------------
# EMAIL
# ------------------------------

def send_email(subject: str, html: str):
    if EMAIL_MODE == "log":
        logger.info("EMAIL TEST MODE | subject=%s | html=%s", subject, html)
        return

    if not RESEND_API_KEY or not ALERT_TO_EMAIL:
        logger.warning("Email not configured")
        return

    # crida real a Resend

    payload = {
        "from": ALERT_FROM_EMAIL,
        "to": [ALERT_TO_EMAIL],
        "subject": subject,
        "html": html,
    }

    req = Request(
        url="https://api.resend.com/emails",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(req):
            logger.info("Email sent")
    except Exception as e:
        logger.error(f"Email failed {e}")


# ------------------------------
# ALERT LOGIC
# ------------------------------

def should_send_alert(db: Session, device_id: str):

    cooldown = datetime.now(timezone.utc) - timedelta(hours=ALERT_COOLDOWN_HOURS)

    last = (
        db.query(AlertDB)
        .filter(AlertDB.deviceId == device_id, AlertDB.alertType == "soil_low")
        .order_by(AlertDB.sentAt.desc())
        .first()
    )

    if not last:
        return True

    return last.sentAt <= cooldown


def process_alert(db: Session, reading: ReadingDB):

    if reading.soilPercent is None:
        return

    if reading.soilPercent >= SOIL_ALERT_THRESHOLD:
        return

    if not should_send_alert(db, reading.deviceId):
        return

    subject = f"Plant alert {reading.deviceId}"

    html = f"""
    <h2>Low soil moisture</h2>
    <p>Device: {reading.deviceId}</p>
    <p>Soil: {reading.soilPercent}%</p>
    """

    send_email(subject, html)

    alert = AlertDB(
        deviceId=reading.deviceId,
        alertType="soil_low",
        value=int(reading.soilPercent),
        recipient=ALERT_TO_EMAIL,
    )

    db.add(alert)
    db.commit()


# ------------------------------
# APP
# ------------------------------

app = FastAPI(title="Plant Station API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    create_tables()
    logger.info("API started")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/readings", response_model=ReadingOut, dependencies=[Depends(require_api_key)])
def create_reading(payload: ReadingIn, db: Session = Depends(get_db)):

    reading = ReadingDB(
        deviceId=payload.deviceId,
        ts=payload.ts or datetime.now(timezone.utc),
        tempC=payload.tempC,
        humAir=payload.humAir,
        ldrRaw=payload.ldrRaw,
        soilPercent=payload.soilPercent,
        rain=payload.rain,
        rssi=payload.rssi,
    )

    db.add(reading)
    db.commit()
    db.refresh(reading)

    try:
        process_alert(db, reading)
    except Exception as e:
        logger.error(f"Alert error {e}")

    return reading


@app.get("/api/v1/readings", response_model=List[ReadingOut])
def list_readings(limit: int = 100, db: Session = Depends(get_db)):

    rows = (
        db.query(ReadingDB)
        .order_by(ReadingDB.ts.desc())
        .limit(limit)
        .all()
    )

    return rows