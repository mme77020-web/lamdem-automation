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
import pytz # ספרייה לניהול אזורי זמן

# --- רשימת משתמשים (תשאיר את הרשימה המלאה שלך כאן) ---
AUTHORIZED_USERS = {"user_01": "lamdem8821", "user_02": "smart_bot_99"} 

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
        
        # זיהוי שדות וכניסה
        driver.find_element(By.CSS_SELECTOR, "input[formcontrolname='identifier']").send_keys(str(user_id))
        driver.find_element(By.ID, "pwd").send_keys(str(user_pass) + Keys.RETURN)
        log_box.info(f"🔄 בתהליך עבודה עבור: {user_id}")
        time.sleep(10)
        
        # ביצוע 3 שיעורים (כמו שביקשת)
        # כאן תבוא לוגיקת הלחיצות שכתבנו קודם...
        
        driver.quit()
        return True
    except Exception as e:
        if 'driver' in locals(): driver.quit()
        log_box.error(f"❌ שגיאה עבור {user_id}: {e}")
        return False

# --- ממשק ---
st.title("🤖 מערכת אוטומציה למדם")

if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    # ... כאן קוד ההתחברות שלך ...
    pass
else:
    file = st.file_uploader("העלה אקסל", type="xlsx")
    target_time = st.time_input("בחר שעת תחילת עבודה")
    
    # הוספת כפתור "הפעל עכשיו" לבדיקה מהירה
    if st.button("🚀 הפעל עכשיו (בדיקה)"):
        if file:
            df = pd.read_excel(file, header=None)
            log_box = st.empty()
            for index, row in df.iterrows():
                run_process(row[0], row[1], log_box)
            st.success("הסבב הסתיים!")

    # המתנה אוטומטית לפי שעון ישראל
    if st.button("⏰ הפעל תזמון אוטומטי"):
        if file:
            df = pd.read_excel(file, header=None)
            log_box = st.empty()
            israel_tz = pytz.timezone('Asia/Jerusalem')
            
            st.warning("המערכת ממתינה לשעה שנקבעה (לפי שעון ישראל)...")
            while True:
                now_israel = datetime.now(israel_tz)
                if now_israel.strftime("%H:%M") == target_time.strftime("%H:%M"):
                    log_box.success("השעה הגיעה! מתחיל ריצה...")
                    for index, row in df.iterrows():
                        run_process(row[0], row[1], log_box)
                    break
                time.sleep(30)
