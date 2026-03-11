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


# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("plant-station")


# ------------------------------------------------------------------------------
# Env config
# ------------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")
API_KEY = os.getenv("API_KEY", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
ALERT_FROM_EMAIL = os.getenv("ALERT_FROM_EMAIL", "Plant Station <onboarding@resend.dev>")
ALERT_TO_EMAIL = os.getenv("ALERT_TO_EMAIL", "")
SOIL_ALERT_THRESHOLD = float(os.getenv("SOIL_ALERT_THRESHOLD", "25"))
ALERT_COOLDOWN_HOURS = int(os.getenv("ALERT_COOLDOWN_HOURS", "12"))

if not DATABASE_URL:
    raise RuntimeError("Missing DATABASE_URL environment variable")

# Alguns proveïdors retornen postgres:// i SQLAlchemy prefereix postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


# ------------------------------------------------------------------------------
# DB
# ------------------------------------------------------------------------------
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

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
    deviceId = Column(String(100), nullable=False, index=True)
    alertType = Column(String(50), nullable=False, index=True)
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    soilPercent = Column(Float, nullable=True)
    sentTo = Column(String(255), nullable=True)
    resendId = Column(String(255), nullable=True)
    createdAt = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ------------------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------------------
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
    tempC: Optional[float] = None
    humAir: Optional[float] = None
    ldrRaw: Optional[int] = None
    soilPercent: Optional[float] = None
    rain: Optional[str] = None
    rssi: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class HealthOut(BaseModel):
    status: str


# ------------------------------------------------------------------------------
# Security
# ------------------------------------------------------------------------------
def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    if not API_KEY:
        logger.warning("API_KEY not configured in environment")
        raise HTTPException(status_code=500, detail="Server API key is not configured")

    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ------------------------------------------------------------------------------
# Email / Resend
# ------------------------------------------------------------------------------
def parse_recipients(raw_value: str) -> List[str]:
    return [x.strip() for x in raw_value.split(",") if x.strip()]


def send_email_with_resend(subject: str, html: str, text: str = "") -> Optional[str]:
    """
    Envia email via Resend REST API.
    Retorna resend email id si tot va bé.
    """
    if not RESEND_API_KEY:
        logger.warning("Email alert skipped: missing RESEND_API_KEY")
        return None

    recipients = parse_recipients(ALERT_TO_EMAIL)
    if not recipients:
        logger.warning("Email alert skipped: missing ALERT_TO_EMAIL")
        return None

    payload = {
        "from": ALERT_FROM_EMAIL,
        "to": recipients,
        "subject": subject,
        "html": html,
        "text": text or subject,
    }

    request = Request(
        url="https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
            data = json.loads(body) if body else {}
            resend_id = data.get("id")
            logger.info("Email sent via Resend. resend_id=%s", resend_id)
            return resend_id

    except HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        logger.exception("Resend HTTPError: %s - %s", e.code, error_body)
        return None
    except URLError as e:
        logger.exception("Resend URLError: %s", str(e))
        return None
    except Exception:
        logger.exception("Unexpected error sending email with Resend")
        return None


# ------------------------------------------------------------------------------
# Alert logic
# ------------------------------------------------------------------------------
def should_send_soil_alert(db: Session, device_id: str) -> bool:
    cooldown_limit = datetime.now(timezone.utc) - timedelta(hours=ALERT_COOLDOWN_HOURS)

    last_alert = (
        db.query(AlertDB)
        .filter(AlertDB.deviceId == device_id, AlertDB.alertType == "soil_low")
        .order_by(AlertDB.createdAt.desc())
        .first()
    )

    if not last_alert:
        return True

    # Compatibilitat si la datetime ve sense tz
    last_created = last_alert.createdAt
    if last_created.tzinfo is None:
        last_created = last_created.replace(tzinfo=timezone.utc)

    return last_created <= cooldown_limit


def maybe_send_soil_alert(db: Session, reading: ReadingDB) -> None:
    if reading.soilPercent is None:
        return

    if reading.soilPercent >= SOIL_ALERT_THRESHOLD:
        return

    if not should_send_soil_alert(db, reading.deviceId):
        logger.info("Soil alert skipped due to cooldown for device=%s", reading.deviceId)
        return

    subject = f"Alerta planta: humitat baixa ({reading.deviceId})"
    text = (
        f"S'ha detectat humitat baixa al dispositiu {reading.deviceId}. "
        f"Valor actual: {reading.soilPercent}%. "
        f"Llindar configurat: {SOIL_ALERT_THRESHOLD}%."
    )
    html = f"""
    <h2>Alerta de planta</h2>
    <p><strong>Dispositiu:</strong> {reading.deviceId}</p>
    <p><strong>Humitat sòl:</strong> {reading.soilPercent}%</p>
    <p><strong>Llindar:</strong> {SOIL_ALERT_THRESHOLD}%</p>
    <p><strong>Temperatura:</strong> {reading.tempC if reading.tempC is not None else "-"}</p>
    <p><strong>Humitat aire:</strong> {reading.humAir if reading.humAir is not None else "-"}</p>
    <p><strong>Timestamp:</strong> {reading.ts.isoformat()}</p>
    """

    resend_id = send_email_with_resend(subject=subject, html=html, text=text)

    alert = AlertDB(
        deviceId=reading.deviceId,
        alertType="soil_low",
        subject=subject,
        message=text,
        soilPercent=reading.soilPercent,
        sentTo=ALERT_TO_EMAIL,
        resendId=resend_id,
    )
    db.add(alert)
    db.commit()

    if resend_id:
        logger.info("Soil alert stored and email sent for device=%s", reading.deviceId)
    else:
        logger.warning("Soil alert stored but email could not be sent for device=%s", reading.deviceId)


# ------------------------------------------------------------------------------
# App
# ------------------------------------------------------------------------------
app = FastAPI(title="Plant Station API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # després ho pots limitar al teu frontend Vite
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    create_tables()
    logger.info("Plant Station API started")


@app.get("/health", response_model=HealthOut)
def health():
    return {"status": "ok"}


@app.post("/api/v1/readings", response_model=ReadingOut, dependencies=[Depends(require_api_key)])
def create_reading(payload: ReadingIn, db: Session = Depends(get_db)):
    reading_ts = payload.ts or datetime.now(timezone.utc)

    reading = ReadingDB(
        deviceId=payload.deviceId,
        ts=reading_ts,
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

    maybe_send_soil_alert(db, reading)

    return reading


@app.get("/api/v1/readings", response_model=List[ReadingOut])
def list_readings(
    deviceId: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = db.query(ReadingDB)

    if deviceId:
        query = query.filter(ReadingDB.deviceId == deviceId)

    rows = query.order_by(ReadingDB.ts.desc()).limit(limit).all()
    return rows


@app.post("/api/v1/alerts/test")
def test_alert(db: Session = Depends(get_db)):
    fake_reading = ReadingDB(
        deviceId="test-device",
        ts=datetime.now(timezone.utc),
        tempC=24,
        humAir=50,
        soilPercent=10,
    )
    maybe_send_soil_alert(db, fake_reading)
    return {"ok": True, "message": "Test alert executed"}