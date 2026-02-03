import streamlit as st
import pandas as pd
import time
from datetime import datetime, time as dt_time
import pytz
import os
import json
import threading
import re
from concurrent.futures import ThreadPoolExecutor

# --- הגדרות מערכת ---
CONFIG_FILE = "bot_config.json"
LOG_FILE = "bot_activity.log"
LOGIN_URL = "https://chabad.lamdem.co.il/auth/login"
MAX_WORKERS = 3 

log_lock = threading.Lock()

AUTHORIZED_USERS = {
    "user_01": "lamdem8821",
    "user_02": "smart_bot_99",
    "user_03": "chabad_user_1",
    "user_04": "vip_access_10",
    "user_05": "helper_2024",
    "user_06": "gold_member_5",
    "user_07": "student_fix_1",
    "user_08": "fast_pass_77",
    "user_09": "learn_bot_44",
    "user_10": "auto_finish_2",
    "user_11": "admin_team_1",
    "user_12": "master_user_9",
    "user_13": "login_safe_0",
    "user_14": "power_user_x",
    "user_15": "final_step_25"
}

# --- ניהול לוגים ---
def write_log(msg):
    timestamp = datetime.now(pytz.timezone('Asia/Jerusalem')).strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    print(entry)
    with log_lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry + "\n")

# --- ניהול קונפיגורציה (שמירה וטעינה) ---
def get_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except: pass
    return {}

def save_config_to_disk(sheet_url, days, selected_time, videos):
    config_data = {
        "sheet_url": sheet_url,
        "days": days,
        "time": str(selected_time),
        "videos": videos,
        "is_locked": True # סימון שההגדרות נעולות
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f)
    return config_data

def unlock_config():
    # קריאת ההגדרות הקיימות
    conf = get_config()
    if conf:
        conf["is_locked"] = False # ביטול נעילה
        with open(CONFIG_FILE, "w") as f:
            json.dump(conf, f)

# --- פונקציות ליבה (בוט) ---
def load_data_from_sheet(sheet_url):
    try:
        if not sheet_url or "http" not in sheet_url: return None
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', sheet_url)
        if match:
            sheet_id = match.group(1)
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
            df = pd.read_csv(csv_url, header=None)
            df = df.dropna(subset=[0, 1])
            return df
        return None
    except Exception as e:
        write_log(f"Error loading sheet: {e}")
        return None

def solve_lesson_video(driver, By):
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
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.core.os_manager import ChromeType

    write_log(f"🚀 מתחיל תהליך עבור: {username}")
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--mute-audio")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
    
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
            write_log(f"⚠️ {username}: לא נמצא כפתור כניסה")
            driver.quit(); return

        time.sleep(12)
        course_url = driver.current_url
        blacklist = []

        for i in range(num_videos):
            driver.get(course_url)
            time.sleep(8)
            
            items = driver.find_elements(By.TAG_NAME, "mat-list-item")
            target = None
            lesson_name = "Unknown"
            
            for item in items:
                html = item.get_attribute("innerHTML")
                if "play_circle" in html and "check_circle" not in html:
                    full_text = item.text.strip()
                    lines = [line.strip() for line in full_text.split('\n') if line.strip() and "play_circle" not in line]
                    clean_name = lines[0] if lines else "Lesson"
                    if clean_name not in blacklist:
                        target = item
                        lesson_name = clean_name
                        break
            
            if not target:
                write_log(f"🏁 {username}: אין יותר שיעורים לביצוע")
                break
            
            write_log(f"📺 {username} [{i+1}/{num_videos}] עובד על: {lesson_name}")
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
                    if not solve_lesson_video(driver, By): blacklist.append(lesson_name)
                else:
                    write_log(f"⚠️ {username}: כשל בכניסה לשיעור")
                    blacklist.append(lesson_name)
            except Exception as e:
                write_log(f"שגיאה אצל {username}: {e}")
                blacklist.append(lesson_name)

        driver.quit()
    except Exception as e:
        write_log(f"❌ שגיאה כללית אצל {username}: {e}")
        if driver: driver.quit()

def run_batch_students(df, num_videos):
    tasks = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for _, row in df.iterrows():
            if len(row) >= 2:
                u = str(row[0]).strip()
                p = str(row[1]).strip()
                tasks.append(executor.submit(run_single_student, u, p, num_videos))
        for task in tasks:
            task.result()

# --- מתזמן ---
@st.cache_resource
def start_global_scheduler():
    def scheduler_loop():
        tz = pytz.timezone('Asia/Jerusalem')
        day_map_he_to_en = {"ראשון": "Sunday", "שני": "Monday", "שלישי": "Tuesday", "רביעי": "Wednesday", "חמישי": "Thursday", "שישי": "Friday", "שבת": "Saturday"}
        
        while True:
            try:
                # טעינת קונפיגורציה מהקובץ
                conf = get_config()
                
                # רצים רק אם יש קובץ והוא במצב "נעול" (מוכן לעבודה)
                if conf.get("is_locked") and conf.get("sheet_url"):
                    now = datetime.now(tz)
                    current_day_en = now.strftime("%A")
                    current_time = now.strftime("%H:%M")
                    
                    active_days_en = []
                    raw_days = conf.get("days", [])
                    for d in raw_days:
                        if d in day_map_he_to_en: active_days_en.append(day_map_he_to_en[d])
                        else: active_days_en.append(d)
                    
                    target_time = str(conf.get("time", "15:00"))[:5]
                    
                    if current_day_en in active_days_en and current_time == target_time:
                        write_log(f"⏰ זמן תזמון ({current_time}) הגיע! מתחיל הרצה...")
                        df = load_data_from_sheet(conf["sheet_url"])
                        if df is not None:
                            run_batch_students(df, conf.get("videos", 3))
                            write_log("✅ סבב מתוזמן הסתיים.")
                        time.sleep(70) 
            except Exception as e:
                print(f"Scheduler Error: {e}")
            
            time.sleep(30) 

    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()
    return thread

start_global_scheduler()

# --- ממשק משתמש ---
st.set_page_config(page_title="מערכת אוטומציה למדם", layout="centered", page_icon="🤖")

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = None

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>🔐 התחברות</h1>", unsafe_allow_html=True)
    col_l, col_c, col_r = st.columns([1,2,1])
    with col_c:
        u = st.text_input("שם משתמש")
        p = st.text_input("סיסמה", type="password")
        if st.button("כניסה", use_container_width=True):
            if u in AUTHORIZED_USERS and AUTHORIZED_USERS[u] == p:
                st.session_state.logged_in = True
                st.session_state.username = u
                st.rerun()
            else: st.error("פרטים שגויים")
else:
    st.title(f"🤖 אוטומציה ({st.session_state.username})")
    
    # טעינת הגדרות שמורות
    saved_config = get_config()
    is_locked = saved_config.get("is_locked", False)
    
    # --- מצב 1: המערכת נעולה ומוכנה לעבודה ---
    if is_locked:
        st.success("✅ ההגדרות נעולות והמערכת רצה ברקע")
        
        st.info(f"📄 שיטס פעיל: {saved_config.get('sheet_url')}")
        st.info(f"🕒 זמן הפעלה: {saved_config.get('time')} | ימים: {', '.join(saved_config.get('days', []))}")
        st.info(f"📺 כמות שיעורים: {saved_config.get('videos')}")

        if st.button("✏️ שחרר נעילה לעריכה"):
            unlock_config()
            st.rerun()
            
        st.divider()
        
        if st.button("🚀 הפעל בדיקה ידנית כעת (לפי ההגדרות הנעולות)"):
            if not st.session_state.get("manual_lock", False):
                st.session_state.manual_lock = True
                def manual_run_locked():
                    try:
                        write_log(f"--- התחלת הרצה ידנית נעולה ---")
                        df = load_data_from_sheet(saved_config['sheet_url'])
                        if df is not None:
                            run_batch_students(df, saved_config['videos'])
                    finally:
                        st.session_state.manual_lock = False
                        write_log("--- סיום ---")
                threading.Thread(target=manual_run_locked).start()
                st.toast("הבוט יצא לדרך!", icon="🚀")

    # --- מצב 2: מצב עריכה (התיבות פתוחות) ---
    else:
        st.warning("⚠️ המערכת במצב עריכה - יש לשמור ולנעול כדי שהבוט האוטומטי יפעל")
        
        # ברירות מחדל
        default_days = saved_config.get("days", [])
        default_time_str = str(saved_config.get("time", "15:00"))
        try: default_time = datetime.strptime(default_time_str[:5], "%H:%M").time()
        except: default_time = dt_time(15, 0)
        default_videos = saved_config.get("videos", 3)
        default_sheet = saved_config.get("sheet_url", "")

        col1, col2 = st.columns(2)
        with col1:
            selected_days = st.multiselect("ימי פעילות", ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"], default=default_days)
        with col2:
            selected_time = st.time_input("שעת התחלה", value=default_time)

        num_videos = st.slider("כמות שיעורים", 1, 10, value=default_videos)
        sheet_url_input = st.text_input("קישור לשיטס (Public):", value=default_sheet)

        if st.button("🔒 שמור ונעל הגדרות (חובה!)", type="primary"):
            if sheet_url_input and "http" in sheet_url_input:
                save_config_to_disk(sheet_url_input, selected_days, selected_time, num_videos)
                st.rerun()
            else:
                st.error("חובה להזין קישור תקין לשיטס")

    # --- יציאה וניקוי ---
    if st.sidebar.button("יציאה"):
        st.session_state.logged_in = False
        st.rerun()

    st.subheader("📝 לוג פעילות")
    if st.button("🗑️ נקה"):
        open(LOG_FILE, "w").close()
        st.rerun()
        
    log_c = "ריק"
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f: log_c = "".join(f.readlines()[::-1])
    st.text_area("לוג:", value=log_c, height=300)
