from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List
from app.models import supabase
from app.scraper import fetch_and_save_agendas

router = APIRouter()

# Pydantic model
class Assignment(BaseModel):
    meeting_date: str  # Could also use datetime.date for strict parsing
    role: str
    assigned: str

# Sync agendas route
@router.get("/sync_agendas")
def sync_agendas():
    logs = fetch_and_save_agendas()
    return {"logs": logs}

# Single assignment insert (optional, keep if needed)
@router.post("/assignments")
def save_assignment(payload: Assignment):
    try:
        response = supabase.table('assignments').insert(payload.dict()).execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Bulk assignment insert
@router.post("/assignments/bulk")
def save_assignments_bulk(payload: List[Assignment]):
    try:
        records = [item.dict() for item in payload]

        meeting_dates = list(set([record['meeting_date'] for record in records]))

        # Delete existing records for these dates first
        for date in meeting_dates:
            supabase.table('assignments').delete().eq('meeting_date', date).execute()

        # Insert new records
        response = supabase.table('assignments').insert(records).execute()

        return {"success": True, "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# View assignments by date
@router.get("/assignments")
def get_assignments(meeting_date: str = Query(..., description="Date in YYYY-MM-DD format")):
    try:
        response = supabase.table('assignments').select("*").eq('meeting_date', meeting_date).execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
