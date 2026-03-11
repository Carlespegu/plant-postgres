from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from App.Core.config import DEFAULT_LIMIT, MAX_LIMIT
from App.Core.security import require_api_key
from App.db.session import get_db
from App.schemas.readings import ReadingIn, ReadingOut
from App.services.readings_service import create_reading, list_readings

router = APIRouter(prefix="/api/v1/readings", tags=["readings"])


@router.post("", response_model=ReadingOut, dependencies=[Depends(require_api_key)])
def create_reading_endpoint(
    payload: ReadingIn,
    db: Session = Depends(get_db),
):
    return create_reading(db, payload)


@router.get("", response_model=List[ReadingOut])
def list_readings_endpoint(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    deviceId: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    return list_readings(db=db, limit=limit, device_id=deviceId)