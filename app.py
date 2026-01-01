import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
from datetime import datetime
import pytz

# רשימת משתמשים
AUTHORIZED_USERS = {"user_01": "lamdem8821", "user_02": "smart_bot_99"}

def run_process(user_id, user_pass, log_box):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.binary_location = "/usr/bin/chromium"
    
    try:
        # כאן התיקון הקריטי שפותר את השגיאה שראית בתמונה
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        
        driver.get("https://chabad.lamdem.co.il/auth/login")
        time.sleep(5)
        
        driver.find_element(By.CSS_SELECTOR, "input[formcontrolname='identifier']").send_keys(str(user_id))
        driver.find_element(By.ID, "pwd").send_keys(str(user_pass) + Keys.RETURN)
        time.sleep(8)
        
        log_box.info(f"🔄 עובד כעת על תלמיד: {user_id}")
        # כאן הבוט יבצע את הלוגיקה שלו
        
        driver.quit()
        return True
    except Exception as e:
        if 'driver' in locals(): driver.quit()
        log_box.error(f"❌ שגיאה עבור {user_id}: {str(e)}")
        return False

# עיצוב הממשק
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
    file = st.file_uploader("העלה קובץ אקסל", type="xlsx")
    days_list = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]
    selected_days = st.multiselect("בחר ימי פעילות:", days_list, default=["שני"])
    target_time = st.time_input("בחר שעת תחילת עבודה")

    if file:
        df = pd.read_excel(file, header=None)
        total_students = len(df)
        st.success(f"📋 נטענו {total_students} תלמידים.")
        
        log_box = st.empty()
        progress_bar = st.progress(0)
        status_text = st.empty()

        if st.button("🚀 הפעל עכשיו (בדיקה)"):
            completed = 0
            for index, row in df.iterrows():
                status_text.write(f"🔄 מעבד תלמיד {completed + 1} מתוך {total_students}...")
                if run_process(str(row[0]), str(row[1]), log_box):
                    completed += 1
                progress_bar.progress(completed / total_students)
            st.success(f"✅ סיום! {completed} תלמידים הושלמו.")

        if st.button("⏰ הפעל תזמון אוטומטי"):
            israel_tz = pytz.timezone('Asia/Jerusalem')
            day_map = {"ראשון": "Sunday", "שני": "Monday", "שלישי": "Tuesday", "רביעי": "Wednesday", "חמישי": "Thursday", "שישי": "Friday", "שבת": "Saturday"}
            eng_days = [day_map[d] for d in selected_days]
            st.warning(f"ממתין לשעה {target_time.strftime('%H:%M')} בימי: {', '.join(selected_days)}")
            
            while True:
                now = datetime.now(israel_tz)
                if now.strftime("%A") in eng_days and now.strftime("%H:%M") == target_time.strftime("%H:%M"):
                    completed = 0
                    for index, row in df.iterrows():
                        if run_process(str(row[0]), str(row[1]), log_box):
                            completed += 1
                        progress_bar.progress(completed / total_students)
                    time.sleep(70)
                time.sleep(30)
