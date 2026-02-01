from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
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

        # 1. ניסיון להעיר אם האתר ישן (הכפתור הכחול)
        try:
            wake_btns = driver.find_elements(By.XPATH, "//button[contains(text(), 'Yes, get this app back up')]")
            if wake_btns:
                print("💤 Site detected as sleeping! Clicking wake up...")
                wake_btns[0].click()
                time.sleep(30)
                driver.refresh()
                print("✅ Clicked wake up and refreshed.")
        except Exception as e:
            print(f"⚠️ Check skipped: {e}")

        # 2. פעולה יזומה: ריענון הדף (F5)
        # זה הפתרון הכי טוב נגד "שינה". זה מאפס את הטיימר של Streamlit.
        print("🔄 Performing proactive refresh...")
        driver.refresh()
        time.sleep(10)

        # 3. גלילה למטה ולמעלה (סימולציה של פעילות)
        print("Bouncing page (Scroll down/up)...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        
        print("✅ Keep-alive sequence finished successfully.")

    except Exception as e:
        print(f"❌ Error in bot: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_proactive_bot()
