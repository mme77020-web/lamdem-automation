import streamlit as st
import pandas as pd
import time
from datetime import datetime, time as dt_time
import pytz
import os
import shutil
import tempfile
import json
import threading
import re
from concurrent.futures import ThreadPoolExecutor

# --- הגדרות מערכת ---
LOGIN_URL = "https://chabad.lamdem.co.il/auth/login"
MAX_WORKERS_PER_ACCOUNT = 2  # כמות תלמידים במקביל לכל חשבון
GLOBAL_MAX_BROWSERS = 3      # הגבלה כללית על כמות דפדפנים פתוחים בשרת למניעת עומס

# תיקייה קבועה לשמירת ההגדרות והלוגים בשרת לינוקס
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# מנעולים וניהול ריצה במקביל
file_lock = threading.Lock()
browser_semaphore = threading.Semaphore(GLOBAL_MAX_BROWSERS)
active_users_running = set()
last_scheduled_run = {}

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

# --- ניהול לוגים (נפרד לכל משתמש בתוך תיקיית data) ---
def get_log_filename(username):
    return os.path.join(DATA_DIR, f"log_{username}.txt")

def write_log(owner_username, msg):
    timestamp = datetime.now(pytz.timezone('Asia/Jerusalem')).strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    print(f"[{owner_username}] {entry}")
    log_file = get_log_filename(owner_username)
    with file_lock:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(entry + "\n")

# --- ניהול קונפיגורציה (שמירה וטעינה אישית לכל משתמש בתוך תיקיית data) ---
def get_config_filename(username):
    return os.path.join(DATA_DIR, f"{username}_config.json")

def get_config(username):
    filename = get_config_filename(username)
    if os.path.exists(filename):
        try:
            with file_lock:
                with open(filename, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
    return {}

def save_config_to_disk(username, sheet_urls_text, days, selected_time, videos, split_by_users=False, batch_size=50, current_offset=0):
    filename = get_config_filename(username)
    config_data = {
        "username": username,
        "sheet_url": sheet_urls_text.strip(),
        "days": days,
        "time": str(selected_time),
        "videos": videos,
        "split_by_users": split_by_users,
        "batch_size": int(batch_size),
        "current_offset": int(current_offset),
        "is_locked": True
    }
    with file_lock:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
    return config_data

def update_user_offset(username, new_offset):
    conf = get_config(username)
    if conf:
        conf["current_offset"] = int(new_offset)
        filename = get_config_filename(username)
        with file_lock:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(conf, f, ensure_ascii=False, indent=2)

def unlock_config(username):
    conf = get_config(username)
    if conf:
        conf["is_locked"] = False
        filename = get_config_filename(username)
        with file_lock:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(conf, f, ensure_ascii=False, indent=2)

# --- פונקציות ליבה (בוט) ---
def load_data_from_sheets(sheet_urls_text, owner_username):
    urls = [u.strip() for u in str(sheet_urls_text).splitlines() if "http" in u]
    all_dfs = []
    
    for url in urls:
        try:
            match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
            if match:
                sheet_id = match.group(1)
                csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
                df = pd.read_csv(csv_url, header=None)
                df = df.dropna(subset=[0, 1])
                all_dfs.append(df)
            else:
                write_log(owner_username, f"⚠️ קישור לא תקין: {url}")
        except Exception as e:
            write_log(owner_username, f"❌ שגיאה בטעינת שיטס ({url}): {e}")
            
    if all_dfs:
        return pd.concat(all_dfs, ignore_index=True)
    return None

def solve_lesson_video(driver, By, owner_username, student_user):
    time.sleep(5)
    try:
        driver.execute_script("var v = document.querySelector('video'); if(v){ v.muted=true; v.play(); }")
        time.sleep(2)
        play_btns = driver.find_elements(By.XPATH, "//button[contains(@class, 'vjs-big-play-button') or @aria-label='Play']")
        if play_btns:
            driver.execute_script("arguments[0].click();", play_btns[0])
    except Exception:
        pass
    time.sleep(5)
    try:
        driver.execute_script("var v = document.querySelector('video'); if(v && v.duration){ v.currentTime = v.duration - 1; }")
    except Exception:
        pass
    time.sleep(5)
    try:
        btn = driver.find_elements(By.XPATH, "//button[contains(., 'סימון כהושלם')]")
        if btn:
            driver.execute_script("arguments[0].click();", btn[0])
            write_log(owner_username, f"   - ✅ {student_user}: בוצע סימון כהושלם")
            return True
    except Exception:
        pass
    return False

def get_chrome_service():
    from selenium.webdriver.chrome.service import Service
    sys_driver = shutil.which("chromedriver") or "/usr/bin/chromedriver"
    if os.path.exists(sys_driver):
        return Service(sys_driver)
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.core.os_manager import ChromeType
    return Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())

def run_single_student(student_user, student_pass, num_videos, owner_username):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    with browser_semaphore:
        write_log(owner_username, f"🚀 מתחיל תהליך עבור תלמיד: {student_user}")
        
        user_data_dir = tempfile.mkdtemp(prefix=f"chrome_{student_user}_")
        
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-extensions")
        options.add_argument("--renderer-process-limit=2")
        options.add_argument(f"--user-data-dir={user_data_dir}")
        options.add_argument("--mute-audio")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        sys_chromium = shutil.which("chromium") or "/usr/bin/chromium"
        if os.path.exists(sys_chromium):
            options.binary_location = sys_chromium

        driver = None
        try:
            service = get_chrome_service()
            driver = webdriver.Chrome(service=service, options=options)
            wait = WebDriverWait(driver, 30)
            
            driver.get(LOGIN_URL)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[formcontrolname='identifier']"))).send_keys(str(student_user))
            driver.find_element(By.ID, "pwd").send_keys(str(student_pass) + Keys.RETURN)
            time.sleep(10)
            
            try:
                enter_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'כניסה')]")))
                driver.execute_script("arguments[0].click();", enter_btn)
            except Exception:
                write_log(owner_username, f"⚠️ {student_user}: לא נמצא כפתור כניסה (בדוק שם משתמש/סיסמה)")
                return

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
                    write_log(owner_username, f"🏁 {student_user}: אין יותר שיעורים פתוחים לביצוע")
                    break
                
                write_log(owner_username, f"📺 {student_user} [{i+1}/{num_videos}] עובד על: {lesson_name}")
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
                        except Exception:
                            pass
                    
                    if driver.current_url != course_url:
                        if not solve_lesson_video(driver, By, owner_username, student_user):
                            blacklist.append(lesson_name)
                    else:
                        write_log(owner_username, f"⚠️ {student_user}: כשל בכניסה לשיעור {lesson_name}")
                        blacklist.append(lesson_name)
                except Exception as e:
                    write_log(owner_username, f"⚠️ שגיאה אצל {student_user}: {e}")
                    blacklist.append(lesson_name)

        except Exception as e:
            write_log(owner_username, f"❌ שגיאה כללית אצל {student_user}: {e}")
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            shutil.rmtree(user_data_dir, ignore_errors=True)
            time.sleep(2)

def execute_account_job(owner_username, sheet_urls_text, num_videos, run_type="מתוזמנת"):
    if owner_username in active_users_running:
        write_log(owner_username, "⏳ החשבון כבר נמצא בהרצה פעילה, מדלג על כפילות.")
        return

    active_users_running.add(owner_username)
    try:
        write_log(owner_username, f"--- התחלת הרצה {run_type} ---")
        df = load_data_from_sheets(sheet_urls_text, owner_username)
        if df is not None and not df.empty:
            # סינון שורות תקינות בלבד מרשימת הבחורים
            valid_students = []
            for _, row in df.iterrows():
                if len(row) >= 2:
                    u = str(row[0]).strip()
                    p = str(row[1]).strip()
                    if u and p and u.lower() != "nan":
                        valid_students.append((u, p))

            total_students = len(valid_students)
            if total_students == 0:
                write_log(owner_username, "⚠️ לא נמצאו תלמידים תקינים בקובצי השיטס.")
                return

            # בדיקה אם מופעל מצב "חלוקה לפי משתמשים" (סבבים)
            conf = get_config(owner_username)
            split_by_users = conf.get("split_by_users", False)
            batch_size = int(conf.get("batch_size", 50))
            current_offset = int(conf.get("current_offset", 0))

            if split_by_users and batch_size > 0:
                # אם המיקום הנוכחי עבר את סוף הרשימה (למשל כי מחקו שורות בשיטס), מאפסים להתחלה
                if current_offset >= total_students:
                    current_offset = 0

                end_index = min(current_offset + batch_size, total_students)
                batch_students = valid_students[current_offset:end_index]

                write_log(
                    owner_username,
                    f"👥 מצב סבבים פעיל: מריץ בחורים {current_offset + 1} עד {end_index} (מתוך {total_students} ברשימה)"
                )

                # חישוב המיקום לסבב הבא: אם הגענו לסוף הרשימה, עוצרים ומאפסים ל-0 לפעם הבאה
                if end_index >= total_students:
                    next_offset = 0
                    write_log(owner_username, "🔄 סוף הרשימה הושלם בסבב זה! בפעם הבאה המערכת תתחיל מחדש מבחור מס' 1.")
                else:
                    next_offset = end_index
                    write_log(owner_username, f"📌 מיקום נשמר: בפעם הבאה המערכת תמשיך מבחור מס' {next_offset + 1}.")

                update_user_offset(owner_username, next_offset)
            else:
                batch_students = valid_students

            tasks = []
            with ThreadPoolExecutor(max_workers=MAX_WORKERS_PER_ACCOUNT) as executor:
                for u, p in batch_students:
                    tasks.append(executor.submit(run_single_student, u, p, num_videos, owner_username))
                for task in tasks:
                    task.result()
            write_log(owner_username, f"✅ סיום הרצה {run_type} בהצלחה.")
        else:
            write_log(owner_username, "⚠️ לא נמצאו תלמידים תקינים בקובצי השיטס.")
    finally:
        active_users_running.discard(owner_username)

# --- מתזמן חכם ---
@st.cache_resource
def start_global_scheduler():
    def scheduler_loop():
        tz = pytz.timezone('Asia/Jerusalem')
        day_map_he_to_en = {
            "ראשון": "Sunday", "שני": "Monday", "שלישי": "Tuesday",
            "רביעי": "Wednesday", "חמישי": "Thursday", "שישי": "Friday", "שבת": "Saturday"
        }
        
        while True:
            try:
                now = datetime.now(tz)
                current_day_en = now.strftime("%A")
                current_time = now.strftime("%H:%M")
                today_key = now.strftime("%Y-%m-%d %H:%M")

                for user_key in AUTHORIZED_USERS.keys():
                    conf = get_config(user_key)
                    if conf.get("is_locked") and conf.get("sheet_url"):
                        raw_days = conf.get("days", [])
                        active_days_en = [day_map_he_to_en.get(d, d) for d in raw_days]
                        target_time = str(conf.get("time", "15:00"))[:5]
                        
                        if current_day_en in active_days_en and current_time == target_time:
                            if last_scheduled_run.get(user_key) != today_key:
                                last_scheduled_run[user_key] = today_key
                                threading.Thread(
                                    target=execute_account_job,
                                    args=(user_key, conf["sheet_url"], conf.get("videos", 3), "מתוזמנת"),
                                    daemon=True
                                ).start()
            except Exception as e:
                print(f"Scheduler Error: {e}")
            
            time.sleep(20)

    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()
    return thread

start_global_scheduler()

# --- ממשק משתמש ---
st.set_page_config(page_title="מערכת אוטומציה למדם", layout="centered", page_icon="🤖")

# תיקון עיצוב לסליידר: שומר על הסליידר משמאל לימין כדי שהנקודה והפס האדום יהיו מסונכרנים בול עם המספר
st.markdown("""
<style>
div[data-testid="stSlider"] > label {
    direction: rtl;
    text-align: right;
    width: 100%;
    display: block;
}
div[data-testid="stSlider"] div[data-baseweb="slider"] {
    direction: ltr !important;
}
</style>
""", unsafe_allow_html=True)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>🔐 התחברות</h1>", unsafe_allow_html=True)
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        u = st.text_input("שם משתמש")
        p = st.text_input("סיסמה", type="password")
        if st.button("כניסה", use_container_width=True):
            if u in AUTHORIZED_USERS and AUTHORIZED_USERS[u] == p:
                st.session_state.logged_in = True
                st.session_state.username = u
                st.rerun()
            else:
                st.error("פרטים שגויים")
else:
    current_user = st.session_state.username
    st.title(f"🤖 אוטומציה ({current_user})")
    
    saved_config = get_config(current_user)
    is_locked = saved_config.get("is_locked", False)
    is_running_now = current_user in active_users_running

    if is_running_now:
        st.warning("⚡ הבוט של החשבון שלך רץ כרגע ברקע! לחץ על 'רענן לוג' למטה כדי לראות התקדמות.")

    if is_locked:
        st.success("✅ ההגדרות שלך נעולות והמערכת מתוזמנת ברקע")
        
        sheets_list = [s.strip() for s in str(saved_config.get('sheet_url', '')).splitlines() if s.strip()]
        st.info(f"📄 כמות קובצי שיטס פעילים בחשבון: {len(sheets_list)}")
        st.info(f"🕒 זמן הפעלה: {saved_config.get('time')} | ימים: {', '.join(saved_config.get('days', []))}")
        st.info(f"📺 כמות שיעורים לתלמיד: {saved_config.get('videos')}")

        if saved_config.get("split_by_users", False):
            b_size = saved_config.get("batch_size", 50)
            c_offset = saved_config.get("current_offset", 0)
            st.info(f"👥 חלוקה לפי משתמשים פעילה: {b_size} בחורים בסבב | ההרצה הבאה תתחיל מבחור מס' {c_offset + 1}")
            if st.button("🔄 אפס סבב בחורים להתחלה (בחור מס' 1)"):
                update_user_offset(current_user, 0)
                st.toast("המיקום אופס! ההרצה הבאה תתחיל מבחור מס' 1", icon="🔄")
                time.sleep(1)
                st.rerun()

        if st.button("✏️ שחרר נעילה לעריכה"):
            unlock_config(current_user)
            st.rerun()
            
        st.divider()
        
        if st.button("🚀 הפעל הרצה ידנית כעת", disabled=is_running_now):
            threading.Thread(
                target=execute_account_job,
                args=(current_user, saved_config['sheet_url'], saved_config['videos'], "ידנית"),
                daemon=True
            ).start()
            st.toast("הבוט יצא לדרך!", icon="🚀")
            time.sleep(1)
            st.rerun()

    else:
        st.warning(f"⚠️ עריכת הגדרות עבור {current_user}")
        
        default_days = saved_config.get("days", [])
        default_time_str = str(saved_config.get("time", "15:00"))
        try:
            default_time = datetime.strptime(default_time_str[:5], "%H:%M").time()
        except Exception:
            default_time = dt_time(15, 0)
        default_videos = saved_config.get("videos", 3)
        default_sheet = saved_config.get("sheet_url", "")
        default_split = saved_config.get("split_by_users", False)
        default_batch = int(saved_config.get("batch_size", 50))
        saved_offset = int(saved_config.get("current_offset", 0))

        col1, col2 = st.columns(2)
        with col1:
            selected_days = st.multiselect(
                "ימי פעילות",
                ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"],
                default=default_days
            )
        with col2:
            selected_time = st.time_input("שעת התחלה", value=default_time)

        num_videos = st.slider("כמות שיעורים", 1, 10, value=default_videos)

        st.markdown("---")
        split_by_users = st.checkbox("👥 חלוקה לפי משתמשים (הרצה בסבבים יומיים)", value=default_split)
        if split_by_users:
            batch_size = st.number_input(
                "כמות בחורים בכל סבב (למשל 50):",
                min_value=1,
                max_value=5000,
                value=default_batch,
                step=5
            )
            st.caption(f"📌 מיקום נוכחי בזיכרון: יתחיל מבחור מס' {saved_offset + 1} (כשמגיע לסוף הרשימה, עוצר ומתחיל מחדש ביום הבא).")
        else:
            batch_size = default_batch

        sheet_url_input = st.text_area(
            "קישורים לשיטס (Public) - אפשר להכניס כמה קישורים, כל קישור בשורה נפרדת:",
            value=default_sheet,
            height=100
        )

        if st.button("🔒 שמור ונעל הגדרות עבורי", type="primary"):
            if sheet_url_input and "http" in sheet_url_input:
                save_config_to_disk(
                    current_user,
                    sheet_url_input,
                    selected_days,
                    selected_time,
                    num_videos,
                    split_by_users=split_by_users,
                    batch_size=batch_size,
                    current_offset=saved_offset
                )
                st.rerun()
            else:
                st.error("חובה להזין לפחות קישור תקין אחד לשיטס")

    if st.sidebar.button("יציאה"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun()

    st.subheader(f"📝 לוג פעילות אישי ({current_user})")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 רענן לוג", use_container_width=True):
            st.rerun()
    with col_btn2:
        if st.button("🗑️ נקה לוג אישי", use_container_width=True):
            user_log = get_log_filename(current_user)
            with file_lock:
                open(user_log, "w", encoding="utf-8").close()
            st.rerun()
        
    log_c = "ריק"
    user_log = get_log_filename(current_user)
    if os.path.exists(user_log):
        with file_lock:
            with open(user_log, "r", encoding="utf-8") as f:
                log_c = "".join(f.readlines()[::-1])
    st.text_area("לוג:", value=log_c, height=300)
