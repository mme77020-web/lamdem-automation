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

# --- רשימת משתמשים מורשים לאפליקציה (שמות וסיסמאות) ---
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

def run_process(user_id, user_pass, log_placeholder):
    options = Options()
    options.add_argument("--mute-audio")
    options.add_argument("--headless") # מריץ ברקע (חובה לענן)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        driver.get("https://chabad.lamdem.co.il/auth/login")
        time.sleep(5)
        driver.find_element(By.CSS_SELECTOR, "input[formcontrolname='identifier']").send_keys(str(user_id))
        driver.find_element(By.ID, "pwd").send_keys(str(user_pass) + Keys.RETURN)
        time.sleep(10)
        
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
                    log_placeholder.write(f"📖 מבצע שיעור {i+1} עבור {user_id}...")
                    driver.execute_script("arguments[0].click();", it)
                    time.sleep(8)
                    if driver.current_url != course_url:
                        solve_lesson_video(driver)
                    break
        driver.quit()
    except:
        if driver: driver.quit()

# --- ממשק האפליקציה בעברית ---
st.set_page_config(page_title="אוטומציית למדם", page_icon="🤖")
st.markdown("<h1 style='text-align: right;'>🤖 מערכת אוטומציה למדם</h1>", unsafe_content_ Wood=True)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    with st.container():
        st.write("אנא התחבר למערכת:")
        input_user = st.text_input("שם משתמש")
        input_pass = st.text_input("סיסמה", type="password")
        if st.button("כניסה"):
            if input_user in AUTHORIZED_USERS and AUTHORIZED_USERS[input_user] == input_pass:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("שם משתמש או סיסמה שגויים")
else:
    st.sidebar.success(f"מחובר: {st.session_state.get('user', 'משתמש מורשה')}")
    if st.sidebar.button("התנתקות"):
        st.session_state.logged_in = False
        st.rerun()

    uploaded_file = st.file_uploader("העלה קובץ אקסל (עמודה A: ת.ז, עמודה B: סיסמה)", type="xlsx")
    
    day_map = {
        "ראשון": "Sunday", "שני": "Monday", "שלישי": "Tuesday", 
        "רביעי": "Wednesday", "חמישי": "Thursday", "שישי": "Friday", "שבת": "Saturday"
    }
    
    selected_days_hebrew = st.multiselect("בחר ימי פעילות:", list(day_map.keys()))
    selected_days_english = [day_map[d] for d in selected_days_hebrew]
    
    target_time = st.time_input("בחר שעת תחילת עבודה (בכל יום שנבחר):")

    if st.button("🚀 הפעל תזמון אוטומטי"):
        if uploaded_file and selected_days_english:
            df = pd.read_excel(uploaded_file)
            st.success(f"נטענו {len(df)} תלמידים. המערכת תפעל בימים {', '.join(selected_days_hebrew)} בשעה {target_time}")
            
            log_box = st.empty()
            while True:
                now = datetime.now()
                if now.strftime("%A") in selected_days_english and now.strftime("%H:%M") == target_time.strftime("%H:%M"):
                    st.toast("הזמן הגיע! מתחיל עבודה...")
                    for index, row in df.iterrows():
                        run_process(row.iloc[0], row.iloc[1], log_box)
                    st.success("הסבב היומי הסתיים.")
                    time.sleep(70) 
                time.sleep(30)