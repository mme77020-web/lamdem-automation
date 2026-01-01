import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options  # שנה לזה (לא Service)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
from datetime import datetime
import pytz

# ... שאר הקוד שלך (ההתחברות, הלוגין וכו')

def run_process(user_id, user_pass, log_box):
    options = Options()
    options.add_argument("--headless=new")  # חובה! המוד החדש והיציב יותר
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--window-size=1920,1080")  # עוזר לטעינה תקינה

    try:
        # כאן בלי Service ובלי Manager – משתמש אוטומטית ב-chromium-driver המותקן
        driver = webdriver.Chrome(options=options)
        
        driver.get("https://chabad.lamdem.co.il/auth/login")
        time.sleep(5)
        
        driver.find_element(By.CSS_SELECTOR, "input[formcontrolname='identifier']").send_keys(str(user_id))
        driver.find_element(By.ID, "pwd").send_keys(str(user_pass) + Keys.RETURN)
        
        log_box.info(f"🔄 עובד על תלמיד: {user_id}")
        time.sleep(10)
        
        # ... הוסף כאן את הלוגיקה המלאה של הסרטונים
        
        driver.quit()
        return True
        
    except Exception as e:
        if 'driver' in locals():
            driver.quit()
        log_box.error(f"❌ שגיאה: {str(e)}")
        return False

# ... שאר הקוד של האפליקציה (הטייטל, הלוגין, האפלוד וכו') נשאר אותו דבר
