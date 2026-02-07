from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import random

# הכתובת שלך
APP_URL = "https://lamdem-automation-bofurwgar4bmduns9g81fw.streamlit.app/"

def run_stay_alive_bot():
    print(f"🔄 Starting STAY-ALIVE Bot for: {APP_URL}")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # התחזות למשתמש אמיתי
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    chrome_options.add_argument("--window-size=1920,1080")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        driver.get(APP_URL)
        print("🌍 Entered site.")
        
        # לולאה שנמשכת כ-50 שניות כדי להחזיק את האתר ער
        # זה מבטיח שהסשן לא יתנתק מיד
        start_time = time.time()
        while time.time() - start_time < 50:
            
            # 1. בדיקה אם האתר ישן (בכל איטרציה!)
            try:
                wake_btns = driver.find_elements(By.XPATH, "//button[contains(text(), 'Yes, get this app back up')]")
                if wake_btns:
                    print("💤 Zzzz detected! Waking up...")
                    wake_btns[0].click()
                    time.sleep(5)
                    driver.refresh()
            except: pass

            # 2. פעילות גלילה אקראית (כדי שהשרת יראה פעילות)
            scroll_y = random.randint(0, 500)
            driver.execute_script(f"window.scrollTo(0, {scroll_y});")
            
            # המתנה קצרה בין בדיקות
            time.sleep(10)
            print(f"⏳ Still on site... ({int(time.time() - start_time)}s)")

        print("✅ Session active for 50s. Done.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_stay_alive_bot()
