from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from App.db.models import ReadingDB
from App.schemas.readings import ReadingIn


def create_reading(db: Session, payload: ReadingIn) -> ReadingDB:
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

    return reading


def list_readings(
    db: Session,
    limit: int,
    device_id: Optional[str] = None,
):
    query = db.query(ReadingDB)

    if device_id:
        query = query.filter(ReadingDB.deviceId == device_id)

    rows = (
        query.order_by(ReadingDB.ts.desc())
        .limit(limit)
        .all()
    )

    return rows