from dotenv import load_dotenv
import os

load_dotenv()

CLUB_NUMBER = os.getenv("CLUB_NUMBER")
PASSWORD = os.getenv("PASSWORD")
CHROME_DRIVER_PATH = "./chromedriver.exe"
AGENDA_URL = "https://hobart.toastmastersclubs.org/agenda.html"
TARGET_DATE = "2025-07-08"
