from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import time

# --- הגדרות ---
# הכתובת של האתר שלך
APP_URL = "https://lamdem-automation-bofurwgar4bmduns9g81fw.streamlit.app/"

# פרטי ההתחברות שבחרנו (מתוך רשימת המורשים שלך)
USERNAME = "user_15"
PASSWORD = "final_step_25"

def run_smart_bot():
    print(f"🚀 Starting bot for: {APP_URL}")
    
    # הגדרות דפדפן (כרום ללא מסך - Headless)
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    # התחזות למשתמש רגיל
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        # 1. כניסה לאתר
        driver.get(APP_URL)
        print("🌍 Entered site. Waiting for load...")
        time.sleep(10) # המתנה לטעינת Streamlit

        # 2. בדיקת מצב שינה (Zzzz) והערה
        try:
            # בדיקה אם יש כפתור להעיר את האתר
            wake_btn = driver.find_elements(By.XPATH, "//button[contains(text(), 'Yes, get this app back up')]")
            if wake_btn:
                print("💤 Site is sleeping! Waking it up...")
                wake_btn[0].click()
                time.sleep(20) # מחכים שהאתר יתעורר
                driver.refresh()
                time.sleep(10)
            else:
                print("✅ Site is already awake.")
        except Exception as e:
            print(f"Wake up check passed or skipped: {e}")

        # 3. התחברות (Login) לפי הקוד ששלחת
        # ב-Streamlit האינפוטים מופיעים לפי הסדר בקוד.
        # האינפוט הראשון = שם משתמש, השני = סיסמה.
        
        print("🔐 Attempting login...")
        inputs = driver.find_elements(By.TAG_NAME, "input")
        
        if len(inputs) >= 2:
            # הזנת שם משתמש
            inputs[0].send_keys(USERNAME)
            time.sleep(0.5)
            
            # הזנת סיסמה ולחיצה על ENTER
            inputs[1].send_keys(PASSWORD)
            time.sleep(0.5)
            inputs[1].send_keys(Keys.RETURN)
            
            print("📤 Credentials sent. Waiting for login...")
            time.sleep(10) # מחכים שהמסך יתחלף
        else:
            print("⚠️ Could not find login inputs! (Maybe already logged in?)")

        # 4. וידוא הצלחה + פעילות
        # אם ההתחברות הצליחה, הכותרת של הדף צריכה להיות "🤖 אוטומציה למדם V8..."
        # אנחנו נבצע גלילה כדי לייצר פעילות
        
        print(f"📄 Page Title: {driver.title}")
        
        # גלילה למטה ולמעלה כדי שהשרת ירשום פעילות WebSocket
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        driver.execute_script("window.scrollTo(0, 0);")
        print("🔄 Scrolled page to register activity.")
        
        time.sleep(5)
        print("✅ Bot finished successfully.")

    except Exception as e:
        print(f"❌ Critical Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_smart_bot()
