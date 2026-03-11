from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from App.db.base import Base


class ReadingDB(Base):
    __tablename__ = "readings"

    id = Column(Integer, primary_key=True, index=True)
    deviceId = Column("device_id", String(100), nullable=False, index=True)
    ts = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        default=lambda: datetime.now(timezone.utc),
    )
    tempC = Column("temp_c", Float, nullable=True)
    humAir = Column("hum_air", Float, nullable=True)
    ldrRaw = Column("ldr_raw", Integer, nullable=True)
    soilPercent = Column("soil_percent", Float, nullable=True)
    rain = Column(Text, nullable=True)
    rssi = Column(Integer, nullable=True)