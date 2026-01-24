from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time

# כתובת האתר שלך (ודא שזה נכון!)
APP_URL = "https://lamdem-automation-bofurwgar4bmduns9g81fw.streamlit.app/"

def run_smart_monitor():
    print(f"🕵️ Monitor starting for: {APP_URL}")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        driver.get(APP_URL)
        print("🌍 Entered site. Checking status...")
        time.sleep(10) # נותן רגע לאתר להיטען

        # בדיקה חכמה: האם הכפתור "התעורר" קיים?
        wake_btn = driver.find_elements(By.XPATH, "//button[contains(text(), 'Yes, get this app back up')]")
        
        if wake_btn:
            # אם מצאנו כפתור - האתר ישן. לוחצים עליו!
            print("💤 Site is sleeping. Waking it up now!")
            wake_btn[0].click()
            time.sleep(20)
            driver.refresh()
            print("✅ Wake up signal sent.")
        else:
            # אם לא מצאנו כפתור - האתר ער. לא עושים כלום!
            print("⚡ Site is already awake. No action needed.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_smart_monitor()
