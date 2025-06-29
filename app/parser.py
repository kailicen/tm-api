from bs4 import BeautifulSoup
from app.utils.cleaner import clean_name
from app.models import supabase

def fetch_known_members():
    response = supabase.table('members').select('name').execute()

    # ✅ Proper check: no .error attribute, instead check if data is empty
    if not response.data:
        print(f"⚠️ Failed to fetch members from Supabase or no members found.")
        return set()

    known_names = set(item['name'].strip() for item in response.data if item.get('name'))
    print(f"✅ Fetched {len(known_names)} known members from Supabase.")
    return known_names


def match_cleaned_name(name, known_names):
    name = name.strip().lower()
    for member in known_names:
        member_clean = member.lower().strip()
        if member_clean == name:  # Full exact match
            return member
        if member_clean.startswith(name):  # Partial prefix match
            return member
    return clean_name(name)  # fallback


def parse_agenda_html(html, agenda_label="Unknown"):
    soup = BeautifulSoup(html, "html.parser")
    roles = []

    # ✅ You need to fetch members here
    known_names = fetch_known_members()

    rows = soup.select("table.agendaTable tbody tr")
    timer_seen = False

    for index, row in enumerate(rows):
        cols = row.find_all("td")
        if len(cols) >= 2:
            role_tag = cols[1].find("b")
            role = role_tag.get_text(strip=True) if role_tag else ""
            name_tag = row.select_one(".fth-member-name")
            name = name_tag.get_text(strip=True) if name_tag else ""

            normalized = normalize_role(role)
            if not normalized:
                continue

            if normalized.startswith("Table Topics Evaluation"):
                if "-" in normalized:
                    raw_names = normalized.split("-", 1)[1].strip()
                    name_list = [n.strip() for n in raw_names.split(",") if n.strip()]
                else:
                    name_list = [name.strip()] if name.strip() else []

                cleaned_names = [match_cleaned_name(n, known_names) for n in name_list]

                if len(cleaned_names) >= 1:
                    roles.append(("Table Topics Evaluation odd #", cleaned_names[0], agenda_label, index))
                else:
                    roles.append(("Table Topics Evaluation odd #", "", agenda_label, index))

                if len(cleaned_names) >= 2:
                    roles.append(("Table Topics Evaluation even #", cleaned_names[1], agenda_label, index + 0.1))
                else:
                    roles.append(("Table Topics Evaluation even #", "", agenda_label, index + 0.1))

                continue

            if "timer" in normalized.lower():
                if timer_seen:
                    print(f"⚠️ Skipping extra Timer role at row {index}: {normalized}")
                    continue
                timer_seen = True

            roles.append((normalized, clean_name(name), agenda_label, index))

    print(f"✅ Parsed {len(roles)} roles for meeting {agenda_label}")
    return roles

def normalize_role(role):
    return role.strip() if role.strip() else None
