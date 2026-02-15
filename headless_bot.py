from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import random
import os

# הכתובת שלך
APP_URL = "https://lamdem-automation-bofurwgar4bmduns9g81fw.streamlit.app/"

def run_diagnostic_bot():
    print(f"🔄 Starting DIAGNOSTIC Bot for: {APP_URL}")
    
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
        print("🌍 Entered site. Waiting 15s for full load...")
        time.sleep(15)
        
        # צילום מסך 1: מצב כניסה
        driver.save_screenshot("1_entry_state.png")

        # 1. ניסיון אגרסיבי להעיר את האתר
        try:
            # חיפוש כל סוגי הכפתורים האפשריים
            wake_btns = driver.find_elements(By.XPATH, "//button[contains(text(), 'Yes, get this app back up')]")
            
            if wake_btns:
                print("💤 Sleep button found! Attempting JS Click...")
                btn = wake_btns[0]
                # שימוש ב-JavaScript כדי ללחוץ (הרבה יותר אמין מסלניום רגיל)
                driver.execute_script("arguments[0].click();", btn)
                print("✅ Click command sent via JS.")
                
                time.sleep(10)
                driver.save_screenshot("2_after_click.png") # צילום אחרי לחיצה
                
                print("🔄 Refreshing page to confirm wakeup...")
                driver.refresh()
                time.sleep(15)
            else:
                print("⚡ No wake-up button found (Site likely active).")
        except Exception as e:
            print(f"⚠️ Wakeup attempt error: {e}")

        # 2. וידוא פעילות (Keep Alive Loop)
        # נשארים 45 שניות כדי לוודא שחיבור ה-WebSocket מתייצב
        print("⏳ Starting keep-alive activity cycle...")
        for i in range(3):
            scroll_y = random.randint(100, 700)
            driver.execute_script(f"window.scrollTo(0, {scroll_y});")
            time.sleep(15)
        
        # צילום מסך סופי לפני יציאה
        driver.save_screenshot("3_final_state.png")
        print("✅ Cycle finished successfully.")

    except Exception as e:
        print(f"❌ Critical Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_diagnostic_bot()
