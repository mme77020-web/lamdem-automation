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
from datetime import datetime, time as dt_time
import pytz
import os
import json
import threading
import re 
from concurrent.futures import ThreadPoolExecutor

# --- הגדרות ---
CONFIG_FILE = "bot_config.json"
LOG_FILE = "bot_activity.log"
LOGIN_URL = "https://chabad.lamdem.co.il/auth/login"
MAX_WORKERS = 3  # <--- מספר הבוטים שרצים במקביל

# מנעול לכתיבה ללוג כדי למנוע התנגשויות בין תהליכים
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

def write_log(msg):
    timestamp = datetime.now(pytz.timezone('Asia/Jerusalem')).strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    print(entry)
    # שימוש בנעילה כדי שבוטים מקבילים לא יכתבו אחד על השני
    with log_lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry + "\n")

# --- חילוץ ID ובודק הרשאות ---
def load_data_from_sheet(sheet_url):
    try:
        if not sheet_url: return None
        
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', sheet_url)
        
        if match:
            sheet_id = match.group(1)
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
            
            df = pd.read_csv(csv_url, header=None)
            df = df.dropna(subset=[0, 1])
            return df
        else:
            write_log("שגיאה: הקישור לא נראה כמו קישור תקין של גוגל שיטס")
            return None

    except Exception as e:
        write_log(f"שגיאה בקריאת השיטס ({e}). וודא שהקובץ מוגדר כ-Public")
        return None

def save_config_to_file():
    config = {
        "days": st.session_state.ui_days,
        "time": str(st.session_state.ui_time),
        "videos": st.session_state.ui_videos,
        "sheet_url": st.session_state.ui_sheet_url
    }
    with open(CONFIG_FILE, "w") as f: json.dump(config, f)
    st.session_state.curr_conf = config
    write_log("✅ הגדרות נשמרו.")
    st.toast("נשמר!", icon="💾")

def load_config_to_state():
    if "data_loaded" not in st.session_state:
        default_settings = {"days": [], "time": "15:00", "videos": 3, "sheet_url": ""}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    file_data = json.load(f)
                    default_settings.update(file_data)
            except: pass
        
        try: t_obj = datetime.strptime(default_settings["time"], "%H:%M:%S").time()
        except: 
            try: t_obj = datetime.strptime(default_settings["time"], "%H:%M").time()
            except: t_obj = dt_time(15, 0)

        st.session_state.ui_days = default_settings["days"]
        st.session_state.ui_time = t_obj
        st.session_state.ui_videos = default_settings["videos"]
        st.session_state.ui_sheet_url = default_settings.get("sheet_url", "")
        st.session_state.data_loaded = True

# --- לוגיקת בוט ---
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
                    if not solve_lesson_video(driver): blacklist.append(lesson_name)
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

# פונקציה המריצה את כל הרשימה במקביל
def run_batch_students(df, num_videos):
    tasks = []
    # שימוש ב-ThreadPoolExecutor להרצת 3 במקביל
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for _, row in df.iterrows():
            if len(row) >= 2:
                u = str(row[0]).strip()
                p = str(row[1]).strip()
                # שליחת המשימה לביצוע ברקע
                tasks.append(executor.submit(run_single_student, u, p, num_videos))
        
        # (אופציונלי) המתנה שכולם יסיימו
        for task in tasks:
            task.result()

@st.cache_resource
def start_global_scheduler():
    def scheduler_loop():
        tz = pytz.timezone('Asia/Jerusalem')
        day_map = {"ראשון": "Sunday", "שני": "Monday", "שלישי": "Tuesday", "רביעי": "Wednesday", "חמישי": "Thursday", "שישי": "Friday", "שבת": "Saturday"}
        
        while True:
            try:
                if os.path.exists(CONFIG_FILE):
                    with open(CONFIG_FILE, "r") as f: settings = json.load(f)
                    if settings.get("days") and settings.get("sheet_url"):
                        now = datetime.now(tz)
                        current_day = now.strftime("%A")
                        current_time = now.strftime("%H:%M")
                        
                        days_eng = [day_map[d] for d in settings["days"] if d in day_map]
                        target_time = settings["time"][:5]
                        
                        if current_day in days_eng and current_time == target_time:
                            write_log("⏰ זמן תזמון הגיע! מתחיל הרצה במקביל...")
                            df = load_data_from_sheet(settings["sheet_url"])
                            if df is not None:
                                run_batch_students(df, settings["videos"])
                                write_log("✅ סבב מתוזמן הסתיים.")
                            time.sleep(70) 
            except: pass
            time.sleep(30)
    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()
    return thread

start_global_scheduler()

# --- ממשק משתמש ---
st.set_page_config(page_title="מערכת אוטומציה למדם", layout="centered", page_icon="🤖")

if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>🔐 התחברות</h1>", unsafe_allow_html=True)
    col_l, col_c, col_r = st.columns([1,2,1])
    with col_c:
        u = st.text_input("שם משתמש")
        p = st.text_input("סיסמה", type="password")
        if st.button("כניסה", use_container_width=True):
            if u in AUTHORIZED_USERS and AUTHORIZED_USERS[u] == p:
                st.session_state.logged_in = True
                st.rerun()
            else: st.error("פרטים שגויים")
else:
    st.title(f"🤖 אוטומציה למדם V8 (טורבו x{MAX_WORKERS})")
    if st.sidebar.button("יציאה"):
        st.session_state.logged_in = False
        st.rerun()

    load_config_to_state()
    
    if st.session_state.ui_sheet_url:
        st.success("✅ מחובר לגוגל שיטס")
    else:
        st.warning("⚠️ נא להזין קישור לגוגל שיטס")

    col1, col2 = st.columns(2)
    with col1:
        st.multiselect("ימי פעילות", ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"], key="ui_days")
    with col2:
        st.time_input("שעת התחלה", step=60, key="ui_time")

    st.slider("כמות שיעורים", 1, 10, key="ui_videos")
    st.text_input("הדבק כאן קישור לשיטס (Public):", key="ui_sheet_url")

    if st.button("💾 שמור הגדרות"):
        save_config_to_file()

    st.divider()

    if "manual_lock" not in st.session_state: st.session_state.manual_lock = False
    
    # כפתור הפעלה ידנית - מריץ כעת על כל הרשימה במקביל!
    if st.button("🚀 הפעל בדיקה ידנית (על כל הרשימה)"):
        if st.session_state.ui_sheet_url and not st.session_state.manual_lock:
            st.session_state.manual_lock = True
            def manual_run():
                try:
                    write_log("--- התחלת הרצה ידנית (מקבילית) ---")
                    df = load_data_from_sheet(st.session_state.ui_sheet_url)
                    if df is not None:
                        # שימוש בפונקציה החדשה שמריצה 3 במקביל
                        run_batch_students(df, st.session_state.ui_videos)
                    else: write_log("שגיאה בטעינת השיטס. בדוק שהקישור ציבורי.")
                finally: 
                    st.session_state.manual_lock = False
                    write_log("--- סיום הרצה ידנית ---")

            threading.Thread(target=manual_run).start()
            st.info(f"תהליך החל! 3 בוטים ירוצו במקביל על הרשימה.")
        else: st.error("חסר קישור או שתהליך כבר רץ")

    if st.button("🗑️ נקה יומן"):
        open(LOG_FILE, "w").close()
        st.rerun()

    st.subheader("📝 יומן פעילות")
    log_c = "ריק"
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f: log_c = "".join(f.readlines()[::-1])
    st.text_area("לוג:", value=log_c, height=400)
