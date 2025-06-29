from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List
from app.models import supabase
from app.scraper import fetch_and_save_agendas
from app.assignment import get_suggested_assignments
from app.utils.constants import SKIP_ASSIGNMENT_ROLES

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
        # Fetch agenda for selected date
        agenda_res = supabase.table('agendas').select("*").eq('meeting_date', meeting_date).execute()
        if not agenda_res.data:
            raise HTTPException(status_code=404, detail="Agenda not found")

        agenda_data = []
        for item in agenda_res.data:
            agenda_data.extend(item['agenda_json'])

        # Fetch past agendas before this date
        past_res = supabase.table('agendas').select("*").lt('meeting_date', meeting_date).execute()
        past_data = []
        for item in past_res.data:
            for agenda_item in item['agenda_json']:
                if agenda_item['Name']:
                    past_data.append({
                        'Name': agenda_item['Name'],
                        'Role': agenda_item['Role'],
                        'MeetingDate': item['meeting_date']
                    })

        # Fetch all members
        members_res = supabase.table('members').select('name').execute()
        members = [m['name'] for m in members_res.data if m['name']]

        # Fetch saved assignments
        assignments_res = supabase.table('assignments').select("*").eq('meeting_date', meeting_date).execute()
        saved_assignments = {item['role']: item['assigned'] for item in assignments_res.data}

        # Get all distinct dates
        dates_res = supabase.table('agendas').select('meeting_date').execute()
        all_dates = sorted(set(item['meeting_date'] for item in dates_res.data), reverse=True)

        # Get suggested assignments
        suggested = get_suggested_assignments(agenda_data, past_data, members)

        # Override Primary if saved assignments exist
        for item in suggested:
            if item['Role'] in saved_assignments:
                item['Primary'] = saved_assignments[item['Role']]

        return {
            "allDates": all_dates,
            "agenda": suggested
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

from app.utils.constants import SKIP_ASSIGNMENT_ROLES  # If not already imported

@router.get("/members/progress")
def get_member_progress():
    try:
        df_roles = supabase.table('agendas').select("*").execute()
        members_res = supabase.table('members').select('name').execute()

        if not members_res.data:
            return {"report": []}

        import pandas as pd
        from datetime import datetime

        # All member names
        all_members = sorted(set(item['name'] for item in members_res.data if item['name']))

        # Flatten agenda_json
        flat_rows = []
        for record in df_roles.data:
            meeting_date = record['meeting_date']
            for item in record['agenda_json']:
                if item.get('Name'):
                    flat_rows.append({
                        "Name": item['Name'],
                        "Role": item['Role'],
                        "MeetingDate": meeting_date
                    })

        df = pd.DataFrame(flat_rows)

        if not df.empty:
            # Apply skip roles filter
            df = df[
                ~(
                    df["Role"].isin(SKIP_ASSIGNMENT_ROLES) |
                    df["Role"].str.startswith("Theme for the meeting")
                )
            ]
            df['MeetingDate'] = pd.to_datetime(df['MeetingDate'])

        today = pd.Timestamp.today().normalize()
        report = []

        for name in all_members:
            if not df.empty and name in df['Name'].values:
                member_roles = df[df['Name'] == name].sort_values('MeetingDate', ascending=False)
                total = len(member_roles)
                recent = member_roles.head(3)['Role'].tolist()
                last_date = member_roles['MeetingDate'].max().date()

                days_since = (today.date() - last_date).days
                gap = "✅" if days_since < 21 else f"❌ No roles in {days_since} days"
            else:
                total = 0
                recent = []
                last_date = None
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
