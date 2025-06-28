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

@router.get("/health")
def health_check():
    return {"status": "ok"}

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
    
# Get agenda and saved assignments for a specific date
@router.get("/agenda/{meeting_date}")
def get_agenda(meeting_date: str):
    try:
        # Get all agenda records for the date
        agenda_res = supabase.table('agendas').select("*").eq('meeting_date', meeting_date).execute()
        agenda_data = agenda_res.data

        if not agenda_data:
            raise HTTPException(status_code=404, detail="Agenda not found for this date")

        # Get all distinct dates for the date selector
        dates_res = supabase.table('agendas').select('meeting_date').execute()
        all_dates = sorted(set(item['meeting_date'] for item in dates_res.data), reverse=True)

        # Get saved assignments for this date
        assignments_res = supabase.table('assignments').select("*").eq('meeting_date', meeting_date).execute()
        saved_assignments = {item['role']: item['assigned'] for item in assignments_res.data}

        # Combine agenda with saved assignments
        combined = []
        for agenda in agenda_data:
            for item in agenda['agenda_json']:  # Loop over the list inside agenda_json
                combined.append({
                    "Role": item['Role'],
                    "Original": item['Name'],
                    "Primary": saved_assignments.get(item['Role'], item['Name']),
                    "Backup": item.get('Backup', "—")
                })

        return {
            "allDates": all_dates,
            "agenda": combined
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/agendas/dates")
def get_agenda_dates():
    try:
        response = supabase.table('agendas').select('meeting_date').execute()
        dates = list(set([item['meeting_date'] for item in response.data]))
        dates.sort(reverse=True)
        return {"dates": dates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/members")
def get_members():
    try:
        response = supabase.table('members').select('name').execute()
        members = sorted(set(item['name'] for item in response.data if item['name']))
        return members
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/assignments/dates")
def get_assignment_dates():
    try:
        response = supabase.table('assignments').select('meeting_date').execute()
        dates = list(set([item['meeting_date'] for item in response.data]))
        dates.sort(reverse=True)
        return {"dates": dates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/members/progress")
def get_member_progress():
    try:
        df_roles = supabase.table('agendas').select("*").execute()
        if not df_roles.data:
            return {"report": []}

        import pandas as pd
        from datetime import datetime

        df = pd.DataFrame([item['agenda_json'] for item in df_roles.data])
        df['MeetingDate'] = [item['meeting_date'] for item in df_roles.data]
        df['MeetingDate'] = pd.to_datetime(df['MeetingDate'])

        today = pd.Timestamp.today().normalize()
        report = []

        for name in sorted(df['Name'].dropna().unique()):
            member_roles = df[df['Name'] == name].sort_values('MeetingDate', ascending=False)
            total = len(member_roles)
            recent = member_roles.head(3)['Role'].tolist()
            last_date = member_roles['MeetingDate'].max().date() if total > 0 else None

            if last_date:
                days_since = (today.date() - last_date).days
                gap = "✅" if days_since < 21 else f"❌ No roles in {days_since} days"
            else:
                gap = "🚫 Never assigned"

            report.append({
                "Name": name,
                "Total": total,
                "RecentRoles": recent,
                "LastAssigned": str(last_date) if last_date else "—",
                "Gap": gap
            })

        return {"report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
