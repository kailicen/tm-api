import os
import time
import shutil
import datetime
import pandas as pd
from dateutil.parser import parse as parse_date
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from app.models import supabase
from app.parser import parse_agenda_html
from app.utils.config import CHROME_DRIVER_PATH, CLUB_NUMBER, PASSWORD, AGENDA_URL, TARGET_DATE


def setup_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1200,800")
    return webdriver.Chrome(service=Service(CHROME_DRIVER_PATH), options=options)


def login(driver, logs):
    logs.append("🔐 Logging in...")
    driver.get("https://hobart.toastmastersclubs.org")
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "adminlogin"))).click()
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "clubnumber")))
    driver.find_element(By.ID, "clubnumber").send_keys(CLUB_NUMBER)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.XPATH, "//button[.//span[text()='Login']]").click()
    try:
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='Keep These and Close']]"))
        ).click()
    except:
        logs.append("ℹ️ No cookie prompt.")
    logs.append("✅ Login successful.")


def fetch_agendas(driver, target_date, logs):
    logs.append(f"📅 Fetching agendas up to {target_date}")
    driver.get(AGENDA_URL)
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "GotoAgenda")))
    dropdown = driver.find_element(By.ID, "GotoAgenda")

    agenda_values = []
    for opt in dropdown.find_elements(By.TAG_NAME, "option"):
        value = opt.get_attribute("value")
        text = opt.text.strip()
        if value and "View Another" not in text:
            try:
                date = parse_date(text, fuzzy=True).date()
                agenda_values.append((value, date))
            except:
                logs.append(f"⚠️ Could not parse date from: {text}")

    agenda_values.sort(key=lambda x: x[1])
    all_roles = []

    for value, date in agenda_values:
        if date > target_date:
            continue
        logs.append(f"🔄 Loading agenda for {date}")
        Select(driver.find_element(By.ID, "GotoAgenda")).select_by_value(value)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "MeetingAgenda")))
        time.sleep(1)

        html = driver.page_source
        parsed_roles = parse_agenda_html(html, agenda_label=str(date))
        all_roles += parsed_roles
    return all_roles


def save_to_supabase(all_roles, logs):
    logs.append(f"📤 Uploading {len(all_roles)} roles to Supabase...")

    # Group roles by meeting date
    agenda_by_date = {}
    for role, name, meeting_date, sort_order in all_roles:
        if meeting_date not in agenda_by_date:
            agenda_by_date[meeting_date] = []
        agenda_by_date[meeting_date].append({
            "Role": role,
            "Name": name,
            "SortOrder": sort_order
        })

    records = []
    for meeting_date, agenda_items in agenda_by_date.items():
        records.append({
            "meeting_date": meeting_date,
            "agenda_json": agenda_items  # Store full agenda as JSON array
        })

    # Clean up existing records for these dates
    for meeting_date in agenda_by_date.keys():
        supabase.table('agendas').delete().eq('meeting_date', meeting_date).execute()

    # Insert new records (one per meeting date)
    response = supabase.table('agendas').insert(records).execute()

    if response.data:
        logs.append(f"✅ Uploaded {len(records)} agendas (one per meeting date).")
    else:
        logs.append(f"❌ Bulk insert failed. No data returned.")


def fetch_and_save_agendas(target_date=None):
    logs = []

    if target_date is None:
        target_date = TARGET_DATE
    if isinstance(target_date, str):
        target_date = datetime.datetime.strptime(target_date, "%Y-%m-%d").date()

    driver = setup_driver()
    try:
        login(driver, logs)
        all_roles = fetch_agendas(driver, target_date, logs)
    except Exception as e:
        logs.append(f"❌ Error: {e}")
        return logs
    finally:
        driver.quit()
        logs.append("👋 Closed browser.")

    save_to_supabase(all_roles, logs)
    logs.append(f"🎉 Done. Total roles fetched: {len(all_roles)}")
    return logs


# CLI support
if __name__ == "__main__":
    logs = fetch_and_save_agendas()
    for l in logs:
        print(l)
