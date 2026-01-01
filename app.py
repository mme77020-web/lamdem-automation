import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import time
from datetime import datetime

# --- רשימת המשתמשים המורשים לאפליקציה ---
AUTHORIZED_USERS = {
    "user_01": "lamdem8821", "user_02": "smart_bot_99", "user_03": "chabad_user_1",
    "user_04": "vip_access_10", "user_05": "helper_2024", "user_06": "gold_member_5",
    "user_07": "student_fix_1", "user_08": "fast_pass_77", "user_09": "learn_bot_44",
    "user_10": "auto_finish_2", "user_11": "admin_team_1", "user_12": "master_user_9",
    "user_13": "login_safe_0", "user_14": "power_user_x", "user_15": "final_step_25"
}

def solve_lesson_video(driver):
    time.sleep(12) 
    try:
        driver.execute_script("""
            var v = document.querySelector('video');
            if(v){ v.muted=true; v.play(); v.currentTime=v.duration-3; }
        """)
        time.sleep(10)
        btns = driver.find_elements(By.XPATH, "//button[contains(., 'סימון כהושלם')]")
        if btns: driver.execute_script("arguments[0].click();", btns[0])
    except: pass

def run_process(user_id, user_pass, log_box):
    options = Options()
    options.add_argument("--headless") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--mute-audio")
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get("https://chabad.lamdem.co.il/auth/login")
        time.sleep(5)
        
        driver.find_element(By.CSS_SELECTOR, "input[formcontrolname='identifier']").send_keys(str(user_id))
        driver.find_element(By.ID, "pwd").send_keys(str(user_pass) + Keys.RETURN)
        log_box.info(f"מתחבר למשתמש: {user_id}")
        time.sleep(10)
        
        # כניסה לקורס וביצוע משימות (הלוגיקה המקורית)
        enter_btn = driver.find_element(By.XPATH, "//button[contains(., 'כניסה')]")
        driver.execute_script("arguments[0].click();", enter_btn)
        time.sleep(12)
        
        course_url = driver.current_url
        for i in range(3):
            driver.get(course_url)
            time.sleep(8)
            items = driver.find_elements(By.TAG_NAME, "mat-list-item")
            for it in items:
                if "play_circle" in it.get_attribute("innerHTML") and "check_circle" not in it.get_attribute("innerHTML"):
                    log_box.write(f"📖 מבצע שיעור {i+1} עבור {user_id}...")
                    driver.execute_script("arguments[0].click();", it)
                    time.sleep(8)
                    if driver.current_url != course_url:
                        solve_lesson_video(driver)
                    break
        driver.quit()
        return True
    except Exception as e:
        if 'driver' in locals(): driver.quit()
        log_box.error(f"שגיאה עבור {user_id}: {str(e)}")
        return False

# --- ממשק משתמש בעברית ---
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
            st.error("פרטים שגויים")
else:
    st.sidebar.success("ברוך הבא!")
    if st.sidebar.button("התנתק"):
        st.session_state.logged_in = False
        st.rerun()

    file = st.file_uploader("העלה אקסל (עמודה A: ת.ז, עמודה B: סיסמה)", type="xlsx")
    days = st.multiselect("בחר ימי פעילות", ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"])
    target_time = st.time_input("שעת התחלה")

    if st.button("🚀 הפעל אוטומציה"):
        if file and days:
            df = pd.read_excel(file)
            st.success(f"המערכת תמתין לזמן שנקבע. נטענו {len(df)} תלמידים.")
            
            day_map = {"ראשון": "Sunday", "שני": "Monday", "שלישי": "Tuesday", "רביעי": "Wednesday", "חמישי": "Thursday", "שישי": "Friday", "שבת": "Saturday"}
            selected_days_eng = [day_map[d] for d in days]
            
            log_box = st.empty()
            while True:
                now = datetime.now()
                if now.strftime("%A") in selected_days_eng and now.strftime("%H:%M") == target_time.strftime("%H:%M"):
                    for index, row in df.iterrows():
                        run_process(row.iloc[0], row.iloc[1], log_box)
                    time.sleep(70) 
                time.sleep(30)
