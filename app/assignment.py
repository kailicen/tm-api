import pandas as pd
import random
from app.utils.constants import SKIP_ASSIGNMENT_ROLES

def canonicalize_role(role):
    role = str(role).strip().lower()
    if role.startswith("speaker"):
        return "Speaker"
    elif role.startswith("evaluator"):
        return "Evaluator"
    elif "timer" in role:
        return "Timer"
    elif "table topics" in role and "evaluation" in role:
        return "Table Topics Evaluation"
    elif "table topics" in role:
        return "Table Topics"
    return role.title()

def get_suggested_assignments(agenda_data, past_data, members):
    # ✅ Step 1: Prepare Agenda DataFrame
    agenda_df = pd.DataFrame(agenda_data)
    agenda_df = agenda_df[~agenda_df["Role"].isin(SKIP_ASSIGNMENT_ROLES) & ~agenda_df["Role"].str.startswith("Theme for the meeting")]
    agenda_df = agenda_df.reset_index(drop=True)

    if agenda_df.empty:
        raise Exception("No valid agenda found for this date")

    # ✅ Step 2: Build Past Roles Dictionary
    past_df = pd.DataFrame(past_data)
    if not past_df.empty:
        past_df['MeetingDate'] = pd.to_datetime(past_df['MeetingDate'])
        past_roles = (
            past_df.sort_values('MeetingDate', ascending=False)
            .groupby('Name')['Role']
            .apply(lambda x: list(x)[:3])
            .to_dict()
        )
    else:
        past_roles = {}

    # ✅ Step 3: Detect Pre-assigned Members (Used Members)
    raw_names = agenda_df["Name"]
    used_members = set(str(n).strip() for n in raw_names if pd.notna(n) and str(n).strip() != "")

    available_members = [m for m in members if m not in used_members]
    random.shuffle(available_members)

    assignments = []

    # ✅ Step 4: Assign Primary Roles
    for _, row in agenda_df.iterrows():
        role = row["Role"]
        raw_name = row.get("Name")
        name = "" if pd.isna(raw_name) else str(raw_name).strip()
        canon_role = canonicalize_role(role)

        if role in SKIP_ASSIGNMENT_ROLES:
            primary = ""
        elif name:  # If already assigned in the agenda
            primary = name
        else:
            eligible = [
                m for m in available_members
                if canon_role not in [canonicalize_role(r) for r in past_roles.get(m, [])]
            ]
            if not eligible:
                eligible = available_members.copy()

            primary = eligible.pop() if eligible else ""

            if primary:
                used_members.add(primary)
                if primary in available_members:
                    available_members.remove(primary)

        assignments.append({
            "Role": role,
            "Original": name,
            "Primary": primary,
            "Backup": ""
        })

    # ✅ Step 5: Assign Backups
    for assignment in assignments:
        if available_members:
            backup = available_members.pop()
            assignment["Backup"] = backup
        else:
            assignment["Backup"] = ""

    # ✅ Step 6: Clean Up
    df = pd.DataFrame(assignments)
    for col in ["Original", "Primary", "Backup"]:
        df[col] = df[col].replace("nan", "").fillna("")

    return df.to_dict(orient="records")
