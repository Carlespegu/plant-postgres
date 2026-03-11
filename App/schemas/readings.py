from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


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