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

# --- הגדרות מערכת ---
LOGIN_URL = "https://chabad.lamdem.co.il/auth/login"
AUTHORIZED_USERS = {"user_01": "lamdem8821", "user_02": "smart_bot_99"}

def solve_lesson_video(driver, log_box):
    """מנגנון צפייה בוידאו ודילוג לסוף מהקוד המקורי שלך"""
    time.sleep(12) 
    def try_play_and_skip(d):
        try:
            play_selectors = ["//button[contains(@class, 'vjs-big-play-button')]", "//button[@aria-label='Play']"]
            for s in play_selectors:
                btns = d.find_elements(By.XPATH, s)
                if btns:
                    d.execute_script("arguments[0].click();", btns[0])
                    break
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
        complete_btn = driver.find_elements(By.XPATH, "//button[contains(., 'סימון כהושלם')]")
        if complete_btn:
            driver.execute_script("arguments[0].click();", complete_btn[0])
            log_box.success("✅ בוצע סימון כהושלם")
            time.sleep(3)
    except: pass

def run_process(username, password, log_box, num_videos):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--mute-audio")
    # הגדרת נתיב הדפדפן בשרת Streamlit
    options.binary_location = "/usr/bin/chromium"
    
    driver = None
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 25)

        driver.get(LOGIN_URL)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[formcontrolname='identifier']"))).send_keys(str(username))
        driver.find_element(By.ID, "pwd").send_keys(str(password) + Keys.RETURN)
        log_box.info(f"👤 מחובר: {username}")
        time.sleep(10)

        enter_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'כניסה')]")))
        driver.execute_script("arguments[0].click();", enter_btn)
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
                if "play_circle" in html and "check_circle" not in html:
                    lesson_name = it.text.strip().split('\n')[0]
                    if lesson_name not in blacklist:
                        target_lesson = it
                        break

            if not target_lesson:
                log_box.warning(f"🏁 אין יותר שיעורים ל-{username}")
                break

            log_box.info(f"📺 [{i+1}/{num_videos}] מבצע: {lesson_name}")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_lesson)
            time.sleep(2)
            driver.execute_script("arguments[0].click();", target_lesson)
            time.sleep(8)
            
            if driver.current_url != course_url:
                solve_lesson_video(driver, log_box)
            else:
                blacklist.append(lesson_name)

        driver.quit()
        return True
    except Exception as e:
        if driver: driver.quit()
        log_box.error(f"❌ שגיאה עבור {username}: {str(e)}")
        return False

# --- ממשק ---
st.set_page_config(page_title="אוטומציית למדם", layout="centered")
st.markdown("<h1 style='text-align: right;'>🤖 מערכת אוטומציה למדם</h1>", unsafe_allow_html=True)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    u = st.text_input("שם משתמש")
    p = st.text_input("סיסמה", type="password")
    if st.button("כניסה"):
        if u in AUTHORIZED_USERS and AUTHORIZED_USERS[u] == p:
            st.session_state.logged_in = True
            st.rerun()
else:
    file = st.file_uploader("העלה אקסל (A: תלמיד, B: סיסמה)", type="xlsx")
    
    # שליטה בכמות הסרטונים
    num_videos_to_solve = st.slider("כמות סרטונים לכל תלמיד:", min_value=1, max_value=10, value=3)
    
    days_list = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]
    selected_days = st.multiselect("בחר ימי פעילות:", days_list, default=["שני"])
    target_time = st.time_input("בחר שעת תחילת עבודה")

    if file:
        df = pd.read_excel(file, header=None)
        students_data = df.dropna(subset=[0, 1])
        total_students = len(students_data)
        st.info(f"📋 נטענו {total_students} תלמידים.")

        log_box = st.empty()
        progress_bar = st.progress(0)
        status_text = st.empty()

        if st.button("🚀 הפעל עכשיו (בדיקה)"):
            completed = 0
            for index, row in students_data.iterrows():
                status_text.write(f"מעבד {str(row[0])} ({completed + 1}/{total_students})...")
                if run_process(str(row[0]).strip(), str(row[1]).strip(), log_box, num_videos_to_solve):
                    completed += 1
                progress_bar.progress(completed / total_students)
            st.success("🏁 סיום הבדיקה!")

        if st.button("⏰ הפעל תזמון אוטומטי"):
            israel_tz = pytz.timezone('Asia/Jerusalem')
            # מיפוי ימים לעברית
            day_map = {"ראשון": "Sunday", "שני": "Monday", "שלישי": "Tuesday", "רביעי": "Wednesday", "חמישי": "Thursday", "שישי": "Friday", "שבת": "Saturday"}
            eng_selected_days = [day_map[d] for d in selected_days]
            
            st.warning(f"המערכת ממתינה לשעה {target_time.strftime('%H:%M')} בימי: {', '.join(selected_days)}")
            
            while True:
                now_israel = datetime.now(israel_tz)
                current_day = now_israel.strftime("%A")
                current_time = now_israel.strftime("%H:%M")
                
                # הבדיקה החדשה: האם היום הנוכחי נבחר והאם השעה הגיעה
                if current_day in eng_selected_days and current_time == target_time.strftime("%H:%M"):
                    log_box.success("השעה הגיעה! מתחיל הרצה שבועית...")
                    completed = 0
                    for index, row in students_data.iterrows():
                        run_process(str(row[0]).strip(), str(row[1]).strip(), log_box, num_videos_to_solve)
                        completed += 1
                        progress_bar.progress(completed / total_students)
                    time.sleep(70) # למנוע הרצה כפולה באותה דקה
                
                time.sleep(30)
