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
import os
import json
import threading

# --- הגדרות אחסון קבועות ---
CONFIG_FILE = "bot_config.json"
DATA_STORAGE = "stored_students.xlsx"
LOG_FILE = "execution_log.txt"
LOGIN_URL = "https://chabad.lamdem.co.il/auth/login"
AUTHORIZED_USERS = {"user_01": "lamdem8821", "user_02": "smart_bot_99"}

def add_to_log(message):
    timestamp = datetime.now(pytz.timezone('Asia/Jerusalem')).strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def save_settings(days, target_time, num_videos):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"days": days, "time": target_time.strftime("%H:%M"), "num_videos": num_videos}, f)

def load_settings():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                return data["days"], datetime.strptime(data["time"], "%H:%M").time(), data["num_videos"]
        except: pass
    return [], datetime.now().time(), 3

# --- לוגיקת הבוט המנצחת שלך ---
def solve_lesson_video(driver):
    time.sleep(12) 
    def try_play_and_skip(d):
        try:
            play_selectors = ["//button[contains(@class, 'vjs-big-play-button')]", "//button[@aria-label='Play']", "//mat-icon[text()='play_arrow']"]
            for s in play_selectors:
                btns = d.find_elements(By.XPATH, s)
                if btns: d.execute_script("arguments[0].click();", btns[0]); break
            time.sleep(5)
            d.execute_script("var v = document.querySelector('video'); if(v && v.duration) { v.muted = true; v.play(); v.currentTime = v.duration - 3; }")
            return True
        except: return False

    if not try_play_and_skip(driver):
        for frame in driver.find_elements(By.TAG_NAME, "iframe"):
            try:
                driver.switch_to.frame(frame)
                try_play_and_skip(driver)
                driver.switch_to.default_content()
            except: driver.switch_to.default_content()
    
    time.sleep(10)
    try:
        btn = driver.find_elements(By.XPATH, "//button[contains(., 'סימון כהושלם')]")
        if btn: 
            driver.execute_script("arguments[0].click();", btn[0])
            return True
    except: pass
    return False

def run_bot_instance(username, password, num_videos, status_container=None):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.binary_location = "/usr/bin/chromium"
    driver = None
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 25)
        
        driver.get(LOGIN_URL)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[formcontrolname='identifier']"))).send_keys(str(username))
        driver.find_element(By.ID, "pwd").send_keys(str(password) + Keys.RETURN)
        time.sleep(10)

        enter = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'כניסה')]")))
        driver.execute_script("arguments[0].click();", enter)
        time.sleep(12)
        
        course_url = driver.current_url
        success_count = 0
        for i in range(num_videos):
            driver.get(course_url); time.sleep(10)
            items = driver.find_elements(By.TAG_NAME, "mat-list-item")
            for it in items:
                html = it.get_attribute("innerHTML")
                if "play_circle" in html and "check_circle" not in html:
                    if status_container: status_container.info(f"📺 {username}: מבצע שיעור {i+1}")
                    driver.execute_script("arguments[0].click();", it)
                    time.sleep(8)
                    if driver.current_url != course_url: 
                        if solve_lesson_video(driver): success_count += 1
                    break
        
        add_to_log(f"תלמיד {username}: הושלמו {success_count} שיעורים.")
        driver.quit()
        return True
    except Exception as e:
        add_to_log(f"שגיאה בתלמיד {username}: {str(e)}")
        if driver: driver.quit()
        return False

# --- מנוע תזמון רקע ---
def scheduler_loop():
    israel_tz = pytz.timezone('Asia/Jerusalem')
    day_map = {"ראשון": "Sunday", "שני": "Monday", "שלישי": "Tuesday", "רביעי": "Wednesday", "חמישי": "Thursday", "שישי": "Friday", "שבת": "Saturday"}
    while True:
        try:
            if os.path.exists(CONFIG_FILE) and os.path.exists(DATA_STORAGE):
                days, t_time, n_vids = load_settings()
                now = datetime.now(israel_tz)
                if now.strftime("%A") in [day_map[d] for d in days] and now.strftime("%H:%M") == t_time.strftime("%H:%M"):
                    add_to_log("⏰ זמן תזמון הגיע - מתחיל הרצה אוטומטית...")
                    df = pd.read_excel(DATA_STORAGE, header=None).dropna(subset=[0, 1])
                    for _, row in df.iterrows():
                        run_bot_instance(str(row[0]).strip(), str(row[1]).strip(), n_vids)
                    time.sleep(70)
        except Exception as e:
            add_to_log(f"שגיאה במנוע התזמון: {str(e)}")
        time.sleep(30)

if "bg_task" not in st.session_state:
    threading.Thread(target=scheduler_loop, daemon=True).start()
    st.session_state.bg_task = True

# --- ממשק משתמש ---
st.set_page_config(page_title="אוטומציית למדם", layout="centered")
st.title("🤖 מערכת אוטומציה למדם")

if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    u = st.text_input("שם משתמש")
    p = st.text_input("סיסמה", type="password")
    if st.button("כניסה"):
        if u in AUTHORIZED_USERS and AUTHORIZED_USERS[u] == p:
            st.session_state.logged_in = True; st.rerun()
else:
    s_days, s_time, s_vids = load_settings()
    
    st.subheader("⚙️ הגדרות")
    sel_days = st.multiselect("ימי פעילות:", ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"], default=s_days)
    sel_time = st.time_input("שעת התחלה:", value=s_time)
    sel_vids = st.slider("סרטונים לתלמיד:", 1, 10, value=s_vids)
    file = st.file_uploader("העלה אקסל מעודכן", type="xlsx")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 שמור הגדרות"):
            save_settings(sel_days, sel_time, sel_vids)
            if file:
                with open(DATA_STORAGE, "wb") as f: f.write(file.getbuffer())
            st.success("✅ נשמר!")
    
    with col2:
        if st.button("🚀 הפעל עכשיו"):
            if os.path.exists(DATA_STORAGE):
                df = pd.read_excel(DATA_STORAGE, header=None).dropna(subset=[0, 1])
                progress = st.progress(0)
                status = st.empty()
                for i, row in enumerate(df.iterrows()):
                    row = row[1]
                    status.info(f"מעבד תלמיד {i+1} מתוך {len(df)}...")
                    run_bot_instance(str(row[0]).strip(), str(row[1]).strip(), sel_vids, status)
                    progress.progress((i + 1) / len(df))
                st.success("🏁 סבב ידני הסתיים!")
            else:
                st.error("לא נמצא קובץ אקסל שמור. העלה קובץ ולחץ על שמור.")

    st.divider()
    st.subheader("📝 יומן פעילות אחרון")
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = f.readlines()
            st.text_area("הודעות מהבוט:", value="".join(logs[-10:]), height=200) # מראה 10 שורות אחרונות
