from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.taxi_service import TaxiService, TripNotFound
router = APIRouter()

class TripDistancePatch(BaseModel):
    distance_km: float = Field(ge=0)

@router.get("/trips")
def list_trips():
    with TaxiService() as s: return {"items": s.list_trips()}
@router.get("/trips/{trip_id}")
def get_trip(trip_id: int):
    with TaxiService() as s:
        row = s.trip(trip_id)
        if not row: raise HTTPException(404)
        return row
@router.patch("/trips/{trip_id}")
def patch_trip(trip_id: int, body: TripDistancePatch):
    try:
        with TaxiService() as s:
            return s.update_trip_distance(trip_id, body.distance_km)
    except TripNotFound:
        raise HTTPException(404, "trip not found")
