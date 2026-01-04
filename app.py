import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime
import pytz
import threading
import json
import os

# --- קבצי שמירה בשרת ---
CONFIG_FILE = "bot_settings.json"
EXCEL_STORAGE = "students_data.xlsx"
LOGIN_URL = "https://chabad.lamdem.co.il/auth/login"
AUTHORIZED_USERS = {"user_01": "lamdem8821", "user_02": "smart_bot_99"}

# פונקציות עזר לשמירת מצב
def save_config(days, target_time, num_videos):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"days": days, "time": target_time.strftime("%H:%M"), "num_videos": num_videos}, f)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            return data["days"], datetime.strptime(data["time"], "%H:%M").time(), data["num_videos"]
    return ["שני"], datetime.now().time(), 3

# --- לוגיקת הבוט (ללא שינוי מהמקור שעבד לך) ---
def solve_lesson_video(driver):
    time.sleep(12) 
    def try_play_and_skip(d):
        try:
            play_selectors = ["//button[contains(@class, 'vjs-big-play-button')]", "//button[@aria-label='Play']"]
            for s in play_selectors:
                btns = d.find_elements(By.XPATH, s)
                if btns: d.execute_script("arguments[0].click();", btns[0]); break
            time.sleep(5)
            d.execute_script("var v = document.querySelector('video'); if(v && v.duration) { v.muted = true; v.play(); v.currentTime = v.duration - 3; }")
            return True
        except: return False
    
    try_play_and_skip(driver)
    time.sleep(10)
    try:
        btn = driver.find_elements(By.XPATH, "//button[contains(., 'סימון כהושלם')]")
        if btn: driver.execute_script("arguments[0].click();", btn[0])
    except: pass

def run_bot_instance(username, password, num_videos):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.binary_location = "/usr/bin/chromium"
    driver = None
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(LOGIN_URL)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[formcontrolname='identifier']"))).send_keys(str(username))
        driver.find_element(By.ID, "pwd").send_keys(str(password) + Keys.RETURN)
        time.sleep(10)
        enter = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'כניסה')]")))
        driver.execute_script("arguments[0].click();", enter)
        time.sleep(10)
        url = driver.current_url
        for i in range(num_videos):
            driver.get(url); time.sleep(8)
            items = driver.find_elements(By.TAG_NAME, "mat-list-item")
            for it in items:
                if "play_circle" in it.get_attribute("innerHTML") and "check_circle" not in it.get_attribute("innerHTML"):
                    driver.execute_script("arguments[0].click();", it)
                    time.sleep(8)
                    if driver.current_url != url: solve_lesson_video(driver)
                    break
        driver.quit()
    except:
        if driver: driver.quit()

# --- מנוע תזמון רקע ---
def background_scheduler():
    israel_tz = pytz.timezone('Asia/Jerusalem')
    day_map = {"ראשון": "Sunday", "שני": "Monday", "שלישי": "Tuesday", "רביעי": "Wednesday", "חמישי": "Thursday", "שישי": "Friday", "שבת": "Saturday"}
    
    while True:
        if os.path.exists(CONFIG_FILE) and os.path.exists(EXCEL_STORAGE):
            days, t_time, n_vids = load_config()
            now = datetime.now(israel_tz)
            if now.strftime("%A") in [day_map[d] for d in days] and now.strftime("%H:%M") == t_time.strftime("%H:%M"):
                df = pd.read_excel(EXCEL_STORAGE, header=None).dropna(subset=[0, 1])
                for _, row in df.iterrows():
                    run_bot_instance(str(row[0]).strip(), str(row[1]).strip(), n_vids)
                time.sleep(70)
        time.sleep(30)

# הפעלת תהליך הרקע פעם אחת בלבד
if "scheduler_started" not in st.session_state:
    threading.Thread(target=background_scheduler, daemon=True).start()
    st.session_state.scheduler_started = True

# --- ממשק משתמש ---
st.set_page_config(page_title="אוטומציית למדם", layout="centered")
st.title("🤖 מערכת אוטומציה למדם - עבודה ברקע")

if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    u = st.text_input("שם משתמש")
    p = st.text_input("סיסמה", type="password")
    if st.button("כניסה"):
        if u in AUTHORIZED_USERS and AUTHORIZED_USERS[u] == p:
            st.session_state.logged_in = True; st.rerun()
else:
    # טעינת הגדרות קיימות (אם יש)
    saved_days, saved_time, saved_vids = load_config()
    
    st.subheader("⚙️ הגדרות תזמון (נשמרות אוטומטית)")
    sel_days = st.multiselect("ימי פעילות:", ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"], default=saved_days)
    sel_time = st.time_input("שעת תחילת עבודה:", value=saved_time)
    sel_vids = st.slider("סרטונים לתלמיד:", 1, 10, value=saved_vids)
    
    uploaded_file = st.file_uploader("העלה/עדכן אקסל (A משתמש, B סיסמה)", type="xlsx")
    
    if st.button("💾 שמור הגדרות והפעל"):
        save_config(sel_days, sel_time, sel_vids)
        if uploaded_file:
            with open(EXCEL_STORAGE, "wb") as f:
                f.write(uploaded_file.getbuffer())
        st.success("✅ ההגדרות והקובץ נשמרו בשרת! המערכת תפעל ברקע גם אם תסגור את האתר.")

    if os.path.exists(EXCEL_STORAGE):
        st.info("📊 קיים קובץ נתונים שמור בשרת. ניתן להחליפו בכל עת.")
