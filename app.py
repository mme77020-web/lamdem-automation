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

# --- לוגים ---
def write_log(msg):
    timestamp = datetime.now(pytz.timezone('Asia/Jerusalem')).strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    print(entry)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")

# --- שמירה וטעינה ---
def save_data(days, time_val, vids, uploaded_file=None):
    config = {"days": days, "time": str(time_val), "videos": vids}
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)
    if uploaded_file:
        with open(DATA_STORAGE, "wb") as f:
            f.write(uploaded_file.getbuffer())
    write_log("✅ הגדרות נשמרו.")

def load_data():
    settings = {"days": [], "time": "15:00", "videos": 3}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                settings = json.load(f)
        except: pass
    return settings

# --- הלוגיקה שלך מהקוד שעבד ---
def solve_lesson_video(driver):
    """טיפול בנגן הוידאו (כולל iframes) והרצה לסוף"""
    time.sleep(12) 
    
    def try_play_and_skip(d):
        try:
            play_selectors = [
                "//button[contains(@class, 'vjs-big-play-button')]",
                "//button[@aria-label='Play']",
                "//mat-icon[text()='play_arrow']",
                "//*[contains(@class, 'play')]"
            ]
            for selector in play_selectors:
                btns = d.find_elements(By.XPATH, selector)
                if btns:
                    d.execute_script("arguments[0].click();", btns[0])
                    break
            
            time.sleep(5)
            d.execute_script("""
                var v = document.querySelector('video');
                if(v && v.duration) {
                    v.muted = true;
                    v.play();
                    v.currentTime = v.duration - 3;
                }
            """)
            return True
        except: return False

    # בדיקה בדף הראשי ובתוך iframes
    if not try_play_and_skip(driver):
        for frame in driver.find_elements(By.TAG_NAME, "iframe"):
            try:
                driver.switch_to.frame(frame)
                try_play_and_skip(driver)
                driver.switch_to.default_content()
            except: driver.switch_to.default_content()

    time.sleep(10)
    try:
        complete_btn = driver.find_elements(By.XPATH, "//button[contains(., 'סימון כהושלם')]")
        if complete_btn:
            driver.execute_script("arguments[0].click();", complete_btn[0])
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
    options.binary_location = "/usr/bin/chromium" # חובה בשרת
    
    driver = None
    try:
        # --- התיקון הקריטי: שימוש ב-ChromeType.CHROMIUM ---
        # זה מוריד אוטומטית את הדרייבר שמתאים לגרסה 143 שבשרת
        service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
        driver = webdriver.Chrome(service=service, options=options)
        
        wait = WebDriverWait(driver, 25)

        # התחברות
        driver.get(LOGIN_URL)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[formcontrolname='identifier']"))).send_keys(str(username))
        driver.find_element(By.ID, "pwd").send_keys(str(password) + Keys.RETURN)
        write_log(f"👤 מחובר: {username}")
        time.sleep(10)

        # כניסה לקורס
        try:
            enter_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'כניסה')]")))
            driver.execute_script("arguments[0].click();", enter_btn)
        except:
            write_log("⚠️ לא נמצא כפתור כניסה לקורס")
            driver.quit(); return

        time.sleep(12)
        course_url = driver.current_url
        blacklist = []

        for i in range(num_videos):
            driver.get(course_url)
            time.sleep(10)
            
            items = driver.find_elements(By.TAG_NAME, "mat-list-item")
            target_lesson = None
            lesson_name = ""

            for it in items:
                html = it.get_attribute("innerHTML")
                txt = it.text.strip()
                if "play_circle" in html and "check_circle" not in html:
                    name_clean = txt.replace('play_circle', '').strip().split('\n')[0]
                    if name_clean and name_clean not in blacklist:
                        lesson_name = name_clean
                        target_lesson = it
                        break
            
            if not target_lesson:
                write_log(f"🏁 אין יותר סרטונים לביצוע עבור {username}.")
                break
                
            write_log(f"📺 [{i+1}/{num_videos}] עובד על: {lesson_name}")
            
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_lesson)
                time.sleep(2)
                driver.execute_script("arguments[0].click();", target_lesson)
                time.sleep(8)
                
                # גיבוי לחיצה
                if driver.current_url == course_url:
                    try:
                        inner = target_lesson.find_element(By.XPATH, f".//*[contains(text(), '{lesson_name}')]")
                        driver.execute_script("arguments[0].click();", inner)
                        time.sleep(8)
                    except: pass
                
                if driver.current_url != course_url:
                    if not solve_lesson_video(driver):
                         blacklist.append(lesson_name)
                else:
                    write_log("⚠️ לא הצלחתי להיכנס לשיעור.")
                    blacklist.append(lesson_name)
            except Exception as e:
                write_log(f"שגיאה בשיעור: {e}")
                blacklist.append(lesson_name)

        driver.quit()
        
    except Exception as e:
        write_log(f"❌ קריסה בבוט עבור {username}: {e}")
        if driver: driver.quit()

# --- מנוע תזמון ---
def scheduler():
    tz = pytz.timezone('Asia/Jerusalem')
    day_map = {"ראשון": "Sunday", "שני": "Monday", "שלישי": "Tuesday", "רביעי": "Wednesday", "חמישי": "Thursday", "שישי": "Friday", "שבת": "Saturday"}
    
    while True:
        try:
            settings = load_data()
            if os.path.exists(DATA_STORAGE) and settings["days"]:
                now = datetime.now(tz)
                current_day = now.strftime("%A")
                current_time = now.strftime("%H:%M")
                
                days_eng = [day_map[d] for d in settings["days"]]
                target_time = settings["time"]
                if len(target_time) > 5: target_time = target_time[:5]
                
                if current_day in days_eng and current_time == target_time:
                    write_log("⏰ זמן תזמון הגיע! מתחיל הרצה...")
                    df = pd.read_excel(DATA_STORAGE, header=None).dropna(subset=[0,1])
                    for _, row in df.iterrows():
                        run_single_student(str(row[0]).strip(), str(row[1]).strip(), settings["videos"])
                    time.sleep(70)
        except Exception as e:
            print(f"Scheduler Error: {e}")
        time.sleep(30)

if "sched" not in st.session_state:
    threading.Thread(target=scheduler, daemon=True).start()
    st.session_state.sched = True

# --- ממשק משתמש ---
st.set_page_config(page_title="אוטומציית למדם", layout="centered")
st.title("🤖 מערכת אוטומציה למדם")

curr_conf = load_data()

if os.path.exists(DATA_STORAGE):
    st.success("✅ קובץ נתונים שמור בשרת.")
else:
    st.warning("⚠️ לא נמצא קובץ נתונים. נא להעלות ולשמור.")

col1, col2 = st.columns(2)
with col1:
    days = st.multiselect("ימי פעילות", ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"], default=curr_conf["days"])
with col2:
    try: t_val = datetime.strptime(curr_conf["time"], "%H:%M").time()
    except: t_val = datetime.now().time()
    t_input = st.time_input("שעת התחלה", value=t_val)

vids = st.slider("כמות שיעורים לתלמיד", 1, 10, value=curr_conf["videos"])
file = st.file_uploader("עדכון קובץ אקסל (A=משתמש, B=סיסמה)", type="xlsx")

if st.button("💾 שמור הגדרות וקובץ"):
    save_data(days, t_input, vids, file)
    st.rerun()

st.divider()

col_a, col_b = st.columns(2)
with col_a:
    if st.button("🚀 הפעל בדיקה מיידית (תלמיד ראשון)"):
        if os.path.exists(DATA_STORAGE):
            df = pd.read_excel(DATA_STORAGE, header=None).dropna(subset=[0,1])
            first = df.iloc[0]
            st.info(f"מריץ על {first[0]}...")
            run_single_student(str(first[0]).strip(), str(first[1]).strip(), vids)
            st.success("בדיקה הסתיימה.")
        else:
            st.error("אין קובץ שמור.")

with col_b:
    if st.button("🗑️ נקה יומן"):
        open(LOG_FILE, "w").close()
        st.rerun()

st.subheader("📝 יומן פעילות")
log_content = "ממתין לפעילות..."
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
        if lines: log_content = "".join(lines[::-1])

st.text_area("לוגים:", value=log_content, height=300)
