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
import re
from concurrent.futures import ThreadPoolExecutor
import sys

# --- הגדרות ---
LOGIN_URL = "https://chabad.lamdem.co.il/auth/login"
MAX_WORKERS = 3  # מספר הבוטים במקביל

# קבלת הקישור והגדרות משורת הפקודה או משתנים קבועים
# כאן אתה יכול להדביק את הקישור לשיטס באופן קבוע, או שנלמד אותך להשתמש ב-Secrets
SHEET_URL = "הדבק_כאן_את_הקישור_לשיטס_שלך" 
VIDEOS_TO_WATCH = 3

def log(msg):
    print(f"[LOG] {msg}")

def load_data_from_sheet(sheet_url):
    try:
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', sheet_url)
        if match:
            sheet_id = match.group(1)
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
            df = pd.read_csv(csv_url, header=None)
            df = df.dropna(subset=[0, 1])
            return df
        return None
    except Exception as e:
        log(f"Error loading sheet: {e}")
        return None

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
            return True
    except: pass
    return False

def run_single_student(username, password, num_videos):
    log(f"🚀 Processing: {username}")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--mute-audio")
    options.add_argument("--window-size=1920,1080")
    
    driver = None
    try:
        service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 30)
        
        driver.get(LOGIN_URL)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[formcontrolname='identifier']"))).send_keys(str(username))
        driver.find_element(By.ID, "pwd").send_keys(str(password) + Keys.RETURN)
        time.sleep(10)
        
        try:
            enter_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'כניסה')]")))
            driver.execute_script("arguments[0].click();", enter_btn)
        except:
            log(f"⚠️ {username}: Login button not found")
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
                log(f"🏁 {username}: No more lessons.")
                break
            
            log(f"📺 {username} [{i+1}/{num_videos}] watching: {lesson_name}")
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
                    else: log(f"✅ {username}: Completed {lesson_name}")
                else:
                    blacklist.append(lesson_name)
            except Exception as e:
                log(f"Error {username}: {e}")
                blacklist.append(lesson_name)

        driver.quit()
    except Exception as e:
        log(f"❌ Critical error {username}: {e}")
        if driver: driver.quit()

if __name__ == "__main__":
    log("--- Starting Batch Run ---")
    if "docs.google.com" not in SHEET_URL:
        log("❌ Error: Please update the SHEET_URL variable in the code with your Google Sheet link.")
        sys.exit(1)

    df = load_data_from_sheet(SHEET_URL)
    if df is not None:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            for _, row in df.iterrows():
                if len(row) >= 2:
                    u = str(row[0]).strip()
                    p = str(row[1]).strip()
                    executor.submit(run_single_student, u, p, VIDEOS_TO_WATCH)
    else:
        log("Could not load data from sheet.")
