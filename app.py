import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
import time
from datetime import datetime
import pytz
import os
import json
import threading

# --- הגדרות ---
CONFIG_FILE = "bot_config.json"
DATA_STORAGE = "stored_students.xlsx"
LOG_FILE = "bot_activity.log"
LOGIN_URL = "https://chabad.lamdem.co.il/auth/login"

# מנעול
process_lock = threading.Lock()

def write_log(msg):
    timestamp = datetime.now(pytz.timezone('Asia/Jerusalem')).strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    print(entry)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")

def save_data(days, time_val, vids, uploaded_file=None):
    # שמירה לקובץ
    config = {"days": days, "time": str(time_val), "videos": vids}
    with open(CONFIG_FILE, "w") as f: json.dump(config, f)
    
    # שמירת אקסל
    if uploaded_file:
        with open(DATA_STORAGE, "wb") as f: f.write(uploaded_file.getbuffer())
    
    # עדכון הזיכרון הזמני כדי שלא יקפוץ חזרה
    st.session_state.curr_conf = config
    write_log("✅ הגדרות נשמרו.")

def load_data_initial():
    # פונקציה שטוענת רק אם אין בזיכרון
    if "curr_conf" not in st.session_state:
        settings = {"days": [], "time": "15:00", "videos": 3}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f: settings = json.load(f)
            except: pass
        st.session_state.curr_conf = settings

# --- לוגיקת הבוט ---
def solve_lesson_video(driver):
    time.sleep(5)
    try:
        driver.execute_script("var v = document.querySelector('video'); if(v){ v.muted=true; v.play(); }")
        time.sleep(2)
        play_btns = driver.find_elements(By.XPATH, "//button[contains(@class, 'vjs-big-play-button') or @aria-label='Play']")
        if play_btns: driver.execute_script("arguments[0].click();", play_btns[0])
    except: pass
    time.sleep(5)
    try:
        driver.execute_script("var v = document.querySelector('video'); if(v && v.duration){ v.currentTime = v.duration - 1; }")
    except: pass
    time.sleep(5)
    try:
        btn = driver.find_elements(By.XPATH, "//button[contains(., 'סימון כהושלם')]")
        if btn:
            driver.execute_script("arguments[0].click();", btn[0])
            write_log("   - ✅ בוצע סימון כהושלם")
            return True
    except: pass
    return False

def run_single_student(username, password, num_videos):
    write_log(f"🚀 מתחיל תהליך עבור: {username}")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--mute-audio")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
    options.binary_location = "/usr/bin/chromium"
    
    driver = None
    try:
        service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 30)
        
        driver.get(LOGIN_URL)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[formcontrolname='identifier']"))).send_keys(str(username))
        driver.find_element(By.ID, "pwd").send_keys(str(password) + Keys.RETURN)
        write_log(f"👤 מחובר: {username}")
        time.sleep(10)
        
        try:
            enter_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'כניסה')]")))
            driver.execute_script("arguments[0].click();", enter_btn)
        except:
            write_log("⚠️ לא נמצא כפתור כניסה")
            driver.quit(); return

        time.sleep(10)
        course_url = driver.current_url
        blacklist = []

        for i in range(num_videos):
            driver.get(course_url)
            time.sleep(8)
            
            items = driver.find_elements(By.TAG_NAME, "mat-list-item")
            target = None
            lesson_name = "לא ידוע"
            
            for item in items:
                if "play_circle" in item.get_attribute("innerHTML") and "check_circle" not in item.get_attribute("innerHTML"):
                    txt = item.text.strip().split('\n')[0]
                    if txt not in blacklist:
                        target = item
                        lesson_name = txt
                        break
            
            if not target:
                write_log(f"🏁 אין יותר שיעורים ל-{username}")
                break
                
            write_log(f"📺 [{i+1}/{num_videos}] עובד על: {lesson_name}")
            
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", target)
                time.sleep(8)
                
                if driver.current_url == course_url:
                    try:
                        inner = target.find_element(By.XPATH, f".//*[contains(text(), '{lesson_name}')]")
                        driver.execute_script("arguments[0].click();", inner)
                        time.sleep(8)
                    except: pass
                
                if driver.current_url != course_url:
                    if not solve_lesson_video(driver): blacklist.append(lesson_name)
                else:
                    write_log("⚠️ כשל בכניסה")
                    blacklist.append(lesson_name)
            except Exception as e:
                write_log(f"שגיאה: {e}")
                blacklist.append(lesson_name)

        driver.quit()
    except Exception as e:
        write_log(f"❌ שגיאה קריטית: {e}")
        if driver: driver.quit()

# --- תזמון ---
def scheduler():
    tz = pytz.timezone('Asia/Jerusalem')
    day_map = {"ראשון": "Sunday", "שני": "Monday", "שלישי": "Tuesday", "רביעי": "Wednesday", "חמישי": "Thursday", "שישי": "Friday", "שבת": "Saturday"}
    
    while True:
        try:
            if os.path.exists(CONFIG_FILE) and os.path.exists(DATA_STORAGE):
                with open(CONFIG_FILE, "r") as f: settings = json.load(f) # קריאה ישירה מהקובץ לתזמון
                
                if settings["days"]:
                    now = datetime.now(tz)
                    current_day = now.strftime("%A")
                    current_time = now.strftime("%H:%M")
                    days_eng = [day_map[d] for d in settings["days"]]
                    target_time = settings["time"]
                    if len(target_time) > 5: target_time = target_time[:5]
                    
                    if current_day in days_eng and current_time == target_time:
                        if not process_lock.locked():
                            with process_lock: 
                                write_log("⏰ התחלת סבב מתוזמן...")
                                df = pd.read_excel(DATA_STORAGE, header=None).dropna(subset=[0,1])
                                for _, row in df.iterrows():
                                    run_single_student(str(row[0]).strip(), str(row[1]).strip(), settings["videos"])
                                write_log("✅ סבב מתוזמן הסתיים.")
                                time.sleep(70)
        except: pass
        time.sleep(30)

if "sched" not in st.session_state:
    threading.Thread(target=scheduler, daemon=True).start()
    st.session_state.sched = True

# --- ממשק ---
st.set_page_config(page_title="אוטומציית למדם", layout="centered")
st.title("🤖 אוטומציה למדם")

# 1. טעינה ראשונית לזיכרון
load_data_initial()
# 2. שימוש בנתונים מהזיכרון (לא מהקובץ)
curr_conf = st.session_state.curr_conf

if os.path.exists(DATA_STORAGE): st.success("✅ נתונים שמורים.")
else: st.warning("⚠️ העלה קובץ.")

col1, col2 = st.columns(2)
with col1: days = st.multiselect("ימים", ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"], default=curr_conf["days"])
with col2: 
    try: t_val = datetime.strptime(curr_conf["time"], "%H:%M").time()
    except: t_val = datetime.now().time()
    t_input = st.time_input("שעה", value=t_val)

vids = st.slider("כמות שיעורים", 1, 10, value=curr_conf["videos"])
file = st.file_uploader("אקסל (A=משתמש, B=סיסמה)", type="xlsx")

if st.button("💾 שמור הגדרות"):
    save_data(days, t_input, vids, file)
    st.success("נשמר בהצלחה!")
    time.sleep(1)
    st.rerun() # רענון כדי לראות את השינויים

st.divider()

if st.button("🚀 בדיקה מיידית"):
    if os.path.exists(DATA_STORAGE) and not process_lock.locked():
        def manual_run():
            with process_lock:
                df = pd.read_excel(DATA_STORAGE, header=None).dropna(subset=[0,1])
                first = df.iloc[0]
                run_single_student(str(first[0]).strip(), str(first[1]).strip(), vids)
        threading.Thread(target=manual_run).start()
        st.info("הבדיקה רצה ברקע...")
    else:
        st.error("הבוט עובד או שאין קובץ.")

if st.button("🗑️ נקה יומן"):
    open(LOG_FILE, "w").close()
    st.rerun()

st.subheader("📝 יומן")
log_content = "ממתין..."
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        log_content = "".join(f.readlines()[::-1])
st.text_area("לוג:", value=log_content, height=400)
