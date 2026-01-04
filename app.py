import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager # רכיב חדש לתיקון גרסאות
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

# --- פונקציית לוגים (כותבת מיד לקובץ) ---
def write_log(msg):
    # הדפסה גם למסך וגם לקובץ
    timestamp = datetime.now(pytz.timezone('Asia/Jerusalem')).strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    print(entry) # מציג בלוגים של השרת
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")

# --- שמירה וטעינה של הגדרות ---
def save_data(days, time_val, vids, uploaded_file=None):
    # שמירת הגדרות
    config = {"days": days, "time": str(time_val), "videos": vids}
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)
    # שמירת אקסל
    if uploaded_file:
        with open(DATA_STORAGE, "wb") as f:
            f.write(uploaded_file.getbuffer())
    write_log("✅ הגדרות ונתונים נשמרו בדיסק בהצלחה.")

def load_data():
    settings = {"days": [], "time": "15:00", "videos": 3}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                settings = json.load(f)
        except: pass
    return settings

# --- הבוט עצמו ---
def run_single_student(username, password, num_videos):
    write_log(f"🚀 מתחיל תהליך עבור: {username}")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.binary_location = "/usr/bin/chromium" # נתיב הכרום בשרת
    
    driver = None
    try:
        # התקנה אוטומטית של הדרייבר המתאים
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        driver.get(LOGIN_URL)
        time.sleep(5)
        
        # התחברות
        try:
            driver.find_element(By.CSS_SELECTOR, "input[formcontrolname='identifier']").send_keys(str(username))
            driver.find_element(By.ID, "pwd").send_keys(str(password) + Keys.RETURN)
        except Exception as e:
            write_log(f"❌ שגיאה בהתחברות ל-{username}: {e}")
            return

        time.sleep(10)
        
        # כניסה לקורס
        try:
            enter_btn = driver.find_element(By.XPATH, "//button[contains(., 'כניסה')]")
            driver.execute_script("arguments[0].click();", enter_btn)
        except:
            write_log(f"⚠️ לא נמצא כפתור כניסה ל-{username}, אולי הסיסמה שגויה?")
            return

        time.sleep(10)
        url = driver.current_url
        completed = 0
        
        for i in range(num_videos):
            driver.get(url)
            time.sleep(8)
            
            # מציאת שיעור לא גמור
            items = driver.find_elements(By.TAG_NAME, "mat-list-item")
            target = None
            for item in items:
                if "play_circle" in item.get_attribute("innerHTML") and "check_circle" not in item.get_attribute("innerHTML"):
                    target = item
                    break
            
            if not target:
                write_log(f"🏁 אין יותר שיעורים זמינים ל-{username}")
                break
                
            # ביצוע השיעור
            write_log(f"📺 {username}: צופה בשיעור {i+1}...")
            driver.execute_script("arguments[0].click();", target)
            time.sleep(8)
            
            # לוגיקת סיום וידאו
            try:
                # לחיצה על Play
                driver.execute_script("var v = document.querySelector('video'); if(v){v.muted=true; v.play();}")
                time.sleep(5)
                # הרצה לסוף
                driver.execute_script("var v = document.querySelector('video'); if(v && v.duration){v.currentTime = v.duration - 2;}")
                time.sleep(5)
                # סימון כהושלם
                btn = driver.find_element(By.XPATH, "//button[contains(., 'סימון כהושלם')]")
                driver.execute_script("arguments[0].click();", btn)
                write_log(f"✅ {username}: שיעור {i+1} סומן בהצלחה!")
                completed += 1
            except Exception as e:
                write_log(f"⚠️ בעיה בשיעור {i+1} ל-{username}: {e}")
                
        driver.quit()
        write_log(f"✨ סיים טיפול ב-{username}. סה\"כ הושלמו: {completed}")
        
    except Exception as e:
        write_log(f"❌ קריסה כללית בבוט עבור {username}: {e}")
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
                
                # בדיקת זמן
                days_eng = [day_map[d] for d in settings["days"]]
                target_time = settings["time"] # כבר מגיע כמחרוזת בגלל ה-JSON

                # תיקון פורמט זמן אם צריך
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

# הפעלת התזמון ברקע
if "sched" not in st.session_state:
    threading.Thread(target=scheduler, daemon=True).start()
    st.session_state.sched = True

# --- ממשק משתמש ---
st.set_page_config(page_title="אוטומציית למדם", layout="centered")
st.title("🤖 מערכת אוטומציה למדם")

# טעינת נתונים קיימים
curr_conf = load_data()

# הצגת סטטוס קבצים
if os.path.exists(DATA_STORAGE):
    st.success("✅ קיים קובץ תלמידים שמור בשרת (לא יימחק בסגירה).")
else:
    st.warning("⚠️ לא נמצא קובץ תלמידים. נא להעלות ולשמור.")

# טופס הגדרות
col1, col2 = st.columns(2)
with col1:
    days = st.multiselect("ימי פעילות", ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"], default=curr_conf["days"])
with col2:
    # המרה חזרה לזמן כדי להציג בתיבה
    try: t_val = datetime.strptime(curr_conf["time"], "%H:%M").time()
    except: t_val = datetime.now().time()
    t_input = st.time_input("שעת התחלה", value=t_val)

vids = st.slider("כמות שיעורים לתלמיד", 1, 10, value=curr_conf["videos"])
file = st.file_uploader("עדכון קובץ אקסל", type="xlsx")

if st.button("💾 שמור הגדרות וקובץ (חובה ללחוץ!)"):
    save_data(days, t_input, vids, file)
    st.rerun()

st.divider()

col_a, col_b = st.columns(2)
with col_a:
    if st.button("🚀 הפעל בדיקה מיידית (תלמיד ראשון בלבד)"):
        if os.path.exists(DATA_STORAGE):
            df = pd.read_excel(DATA_STORAGE, header=None).dropna(subset=[0,1])
            first_student = df.iloc[0]
            st.info(f"מריץ בדיקה על: {first_student[0]}...")
            run_single_student(str(first_student[0]).strip(), str(first_student[1]).strip(), vids)
            st.success("בדיקה הסתיימה - בדוק את היומן למטה")
        else:
            st.error("אין קובץ שמור להרצה.")

with col_b:
    if st.button("🗑️ נקה יומן"):
        open(LOG_FILE, "w").close()
        st.rerun()

st.subheader("📝 יומן פעילות (מתעדכן בזמן אמת)")
# קריאת הלוגים
log_content = "אין עדיין פעילות..."
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
        log_content = "".join(lines[::-1]) # הופך סדר - חדש למעלה

st.text_area("לוגים:", value=log_content, height=300)
