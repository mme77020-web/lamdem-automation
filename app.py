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

# --- הגדרות קבועות ---
LOGIN_URL = "https://chabad.lamdem.co.il/auth/login"
AUTHORIZED_USERS = {"user_01": "lamdem8821", "user_02": "smart_bot_99"}

def solve_lesson_video(driver, log_box):
    """טיפול משופר בנגן הוידאו וסימון סיום"""
    time.sleep(10) 
    
    def force_video_finish(d):
        try:
            # מנסה למצוא את כפתור ה-Play הגדול
            play_selectors = ["//button[contains(@class, 'vjs-big-play-button')]", "//button[@aria-label='Play']"]
            for s in play_selectors:
                btns = d.find_elements(By.XPATH, s)
                if btns:
                    d.execute_script("arguments[0].click();", btns[0])
                    break
            
            time.sleep(4)
            # הרצת הוידאו לסוף בצורה ש"למדם" מקבל
            d.execute_script("""
                var v = document.querySelector('video');
                if(v) {
                    v.muted = true;
                    v.play();
                    setTimeout(function(){ v.currentTime = v.duration - 2; }, 3000);
                }
            """)
            time.sleep(8)
            return True
        except: return False

    # בדיקה בדף הראשי וב-Iframes
    force_video_finish(driver)
    for frame in driver.find_elements(By.TAG_NAME, "iframe"):
        try:
            driver.switch_to.frame(frame)
            force_video_finish(driver)
            driver.switch_to.default_content()
        except: driver.switch_to.default_content()

    time.sleep(5)
    
    # ניסיון לחיצה על "סימון כהושלם" בכמה שיטות
    finish_selectors = [
        "//button[contains(., 'סימון כהושלם')]",
        "//span[contains(text(), 'סימון כהושלם')]",
        "//button[contains(@class, 'complete')]"
    ]
    
    found = False
    for selector in finish_selectors:
        btns = driver.find_elements(By.XPATH, selector)
        if btns:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btns[0])
                time.sleep(1)
                driver.execute_script("arguments[0].click();", btns[0])
                found = True
                log_box.success("✅ נשלחה פקודת סימון כהושלם")
                time.sleep(5) # זמן המתנה קריטי לעדכון השרת
                break
            except: pass
    
    if not found:
        log_box.warning("⚠️ לא נמצא כפתור סיום, ייתכן והשיעור כבר הושלם")

def run_process(username, password, log_box):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--mute-audio")
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
        time.sleep(8)

        enter_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'כניסה')]")))
        driver.execute_script("arguments[0].click();", enter_btn)
        time.sleep(10)
        
        course_url = driver.current_url
        blacklist = []

        for i in range(3): 
            driver.get(course_url)
            time.sleep(8)
            
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

            log_box.info(f"📺 [{i+1}/3] מבצע: {lesson_name}")
            
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_lesson)
                time.sleep(2)
                driver.execute_script("arguments[0].click();", target_lesson)
                time.sleep(8)
                
                if driver.current_url != course_url:
                    solve_lesson_video(driver, log_box)
                else:
                    blacklist.append(lesson_name)
            except:
                blacklist.append(lesson_name)

        driver.quit()
        return True
    except Exception as e:
        if driver: driver.quit()
        log_box.error(f"❌ שגיאה ב-{username}: {str(e)}")
        return False

# --- ממשק Streamlit ---
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
    file = st.file_uploader("העלה אקסל (A משתמש, B סיסמה)", type="xlsx")
    days_list = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]
    selected_days = st.multiselect("בחר ימי פעילות:", days_list)
    target_time = st.time_input("בחר שעת תחילת עבודה")

    if file:
        df = pd.read_excel(file, header=None)
        students_data = df.dropna(subset=[0, 1])
        total_students = len(students_data)
        st.success(f"📋 נטענו {total_students} תלמידים.")

        log_box = st.empty()
        progress_bar = st.progress(0)
        status_text = st.empty()

        if st.button("🚀 הפעל עכשיו (בדיקה)"):
            completed = 0
            for index, row in students_data.iterrows():
                status_text.write(f"🔄 מעבד תלמיד {completed + 1} מתוך {total_students}...")
                if run_process(str(row[0]).strip(), str(row[1]).strip(), log_box):
                    completed += 1
                progress_bar.progress(completed / total_students)
            st.success(f"✅ סיום! {completed} תלמידים עובדו.")

        if st.button("⏰ הפעל תזמון אוטומטי"):
            israel_tz = pytz.timezone('Asia/Jerusalem')
            day_map = {"ראשון": "Sunday", "שני": "Monday", "שלישי": "Tuesday", "רביעי": "Wednesday", "חמישי": "Thursday", "שישי": "Friday", "שבת": "Saturday"}
            eng_days = [day_map[d] for d in selected_days]
            st.warning(f"המערכת ממתינה לזמן שנפרע...")
            
            while True:
                now = datetime.now(israel_tz)
                if now.strftime("%A") in eng_days and now.strftime("%H:%M") == target_time.strftime("%H:%M"):
                    for index, row in students_data.iterrows():
                        run_process(str(row[0]).strip(), str(row[1]).strip(), log_box)
                    time.sleep(70)
                time.sleep(30)
