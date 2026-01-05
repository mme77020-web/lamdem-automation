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

# --- הגדרות ---
CONFIG_FILE = "bot_config.json"
LOG_FILE = "bot_activity.log"
LOGIN_URL = "https://chabad.lamdem.co.il/auth/login"

# רשימת המשתמשים המורשים
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

# --- מנהל לוגים ---
def write_log(msg):
    timestamp = datetime.now(pytz.timezone('Asia/Jerusalem')).strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    print(entry)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")

# --- פונקציית עזר לטעינת גוגל שיטס ---
def load_data_from_sheet(sheet_url):
    try:
        if not sheet_url: return None
        # המרת קישור רגיל לקישור CSV
        csv_url = sheet_url.replace('/edit?usp=sharing', '/export?format=csv')
        csv_url = csv_url.replace('/edit', '/export?format=csv')
        
        # קריאה ישירה מהאינטרנט
        df = pd.read_csv(csv_url, header=None)
        # סינון שורות ריקות
        df = df.dropna(subset=[0, 1])
        return df
    except Exception as e:
        write_log(f"שגיאה בטעינת הקישור: {e}")
        return None

# --- שמירה וטעינה ---
def save_config_to_file():
    config = {
        "days": st.session_state.ui_days,
        "time": str(st.session_state.ui_time),
        "videos": st.session_state.ui_videos,
        "sheet_url": st.session_state.ui_sheet_url # שמירת הקישור
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)
    
    st.session_state.curr_conf = config
    write_log("✅ הגדרות וקישור נשמרו.")
    st.toast("ההגדרות נשמרו בהצלחה!", icon="💾")

def load_config_to_state():
    if "data_loaded" not in st.session_state:
        default_settings = {"days": [], "time": "15:00", "videos": 3, "sheet_url": ""}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    file_data = json.load(f)
                    default_settings.update(file_data)
            except: pass
        
        try:
            t_obj = datetime.strptime(default_settings["time"], "%H:%M:%S").time()
        except:
            try: t_obj = datetime.strptime(default_settings["time"], "%H:%M").time()
            except: t_obj = dt_time(15, 0)

        st.session_state.ui_days = default_settings["days"]
        st.session_state.ui_time = t_obj
        st.session_state.ui_videos = default_settings["videos"]
        st.session_state.ui_sheet_url = default_settings.get("sheet_url", "")
        st.session_state.data_loaded = True

# --- לוגיקת בוט (אותו קוד בדיוק) ---
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
        write_log(f"❌ שגיאה: {e}")
        if driver: driver.quit()

# --- המנעול העליון לתזמון ---
@st.cache_resource
def start_global_scheduler():
    def scheduler_loop():
        tz = pytz.timezone('Asia/Jerusalem')
        day_map = {"ראשון": "Sunday", "שני": "Monday", "שלישי": "Tuesday", "רביעי": "Wednesday", "חמישי": "Thursday", "שישי": "Friday", "שבת": "Saturday"}
        
        while True:
            try:
                if os.path.exists(CONFIG_FILE):
                    with open(CONFIG_FILE, "r") as f: settings = json.load(f)
                    
                    # בדיקה שיש ימים, שעה וקישור לשיטס
                    if settings.get("days") and settings.get("sheet_url"):
                        now = datetime.now(tz)
                        current_day = now.strftime("%A")
                        current_time = now.strftime("%H:%M")
                        
                        days_eng = [day_map[d] for d in settings["days"] if d in day_map]
                        target_time = settings["time"][:5]
                        
                        if current_day in days_eng and current_time == target_time:
                            write_log("⏰ זמן תזמון הגיע!")
                            # קריאה מהקישור שנשמר
                            df = load_data_from_sheet(settings["sheet_url"])
                            if df is not None:
                                for _, row in df.iterrows():
                                    if len(row) >= 2:
                                        run_single_student(str(row[0]).strip(), str(row[1]).strip(), settings["videos"])
                                write_log("✅ סבב הסתיים.")
                            else:
                                write_log("⚠️ שגיאה בקריאת הנתונים מהשיטס")
                            time.sleep(70) 
            except: pass
            time.sleep(30)

    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()
    return thread

start_global_scheduler()

# --- ממשק משתמש ---
st.set_page_config(page_title="מערכת אוטומציה למדם", layout="centered", page_icon="🤖")

# בדיקת התחברות
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>🔐 התחברות למערכת</h1>", unsafe_allow_html=True)
    
    col_l, col_c, col_r = st.columns([1,2,1])
    with col_c:
        username_input = st.text_input("שם משתמש")
        password_input = st.text_input("סיסמה", type="password")
        
        if st.button("כניסה", use_container_width=True):
            if username_input in AUTHORIZED_USERS and AUTHORIZED_USERS[username_input] == password_input:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("שם משתמש או סיסמה שגויים")

else:
    # --- תוכן המערכת למי שהתחבר ---
    st.title("🤖 אוטומציה למדם V6 (שיטס)")
    
    if st.sidebar.button("יציאה"):
        st.session_state.logged_in = False
        st.rerun()

    load_config_to_state()
    
    # הצגת סטטוס הקישור
    current_url = st.session_state.ui_sheet_url
    if current_url:
        st.success(f"✅ מחובר לגוגל שיטס")
    else:
        st.warning("⚠️ נא להזין קישור לגוגל שיטס")

    col1, col2 = st.columns(2)
    with col1:
        st.multiselect("ימי פעילות", 
                       ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"], 
                       key="ui_days")
    with col2:
        st.time_input("שעת התחלה", step=60, key="ui_time")

    st.slider("כמות שיעורים לתלמיד", 1, 10, key="ui_videos")

    # שדה טקסט לקישור במקום העלאת קובץ
    st.text_input("הדבק כאן קישור ל-Google Sheet (חובה שיהיה פתוח לכולם)", key="ui_sheet_url")

    if st.button("💾 שמור הגדרות"):
        save_config_to_file()

    st.divider()

    if "manual_lock" not in st.session_state: st.session_state.manual_lock = False
    if st.button("🚀 הפעל בדיקה עכשיו (מהקישור)"):
        if st.session_state.ui_sheet_url and not st.session_state.manual_lock:
            st.session_state.manual_lock = True
            def manual_run():
                try:
                    df = load_data_from_sheet(st.session_state.ui_sheet_url)
                    if df is not None:
                        first = df.iloc[0]
                        run_single_student(str(first[0]).strip(), str(first[1]).strip(), st.session_state.ui_videos)
                    else:
                        write_log("שגיאה: לא הצלחתי לקרוא מהקישור. וודא שהוא 'Anyone with the link'")
                finally:
                    st.session_state.manual_lock = False
            threading.Thread(target=manual_run).start()
            st.info("הבדיקה רצה ברקע... בדוק ביומן")
        else:
            st.error("חסר קישור או שהבוט עובד")

    if st.button("🗑️ נקה יומן"):
        open(LOG_FILE, "w").close()
        st.rerun()

    st.subheader("📝 יומן פעילות")
    log_content = "ממתין..."
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            log_content = "".join(f.readlines()[::-1])
    st.text_area("לוג:", value=log_content, height=400)
