from sqlalchemy import Column, DateTime, BigInteger, Integer, Numeric, String, ForeignKey, func

from App.db.base import Base


class Reading(Base):
    __tablename__ = "readings"

    id = Column(BigInteger, primary_key=True)
    asset_id = Column(BigInteger, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    ts = Column(DateTime(timezone=True), nullable=False)

    temp_c = Column(Numeric(6, 2))
    hum_air = Column(Numeric(6, 2))
    ldr_raw = Column(Integer)
    soil_percent = Column(Numeric(6, 2))
    rain = Column(String(50))
    rssi = Column(Integer)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())