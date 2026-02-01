from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import time
import random

# הכתובת שלך
APP_URL = "https://lamdem-automation-bofurwgar4bmduns9g81fw.streamlit.app/"

def run_proactive_bot():
    print(f"🔄 Starting PROACTIVE Keep-Alive for: {APP_URL}")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    chrome_options.add_argument("--window-size=1920,1080")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        driver.get(APP_URL)
        print("🌍 Entered site. Waiting 15 seconds...")
        time.sleep(15)

        # 1. בדיקה האם האתר ישן (הטיפול הקלאסי)
        try:
            wake_btns = driver.find_elements(By.XPATH, "//button[contains(text(), 'Yes, get this app back up')]")
            if wake_btns:
                print("💤 Site detected as sleeping! Clicking wake up...")
                wake_btns[0].click()
                time.sleep(30)
                driver.refresh()
                print("✅ Clicked wake up and refreshed.")
        except Exception as e:
            print(f"⚠️ Wake button check skipped: {e}")

        # 2. פעילות יזומה (כדי למנוע שינה בפעם הבאה)
        # אנחנו מרעננים את הדף כדי לחדש את ה-Session מול השרת
        print("🔄 Performing proactive refresh...")
        driver.refresh()
        time.sleep(10)

        # גלילה למטה ולמעלה - משדר לשרת שיש משתמש פעיל
        print("Bouncing page (Scroll down/up)...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)
        
        # לחיצה סתמית על הגוף של הדף כדי לוודא שהחלון בפוקוס
        driver.find_element(By.TAG_NAME, "body").click()
        
        print("✅ Keep-alive sequence finished successfully.")

    except Exception as e:
        print(f"❌ Error in bot: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_proactive_bot()
