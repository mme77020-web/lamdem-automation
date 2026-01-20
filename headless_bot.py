from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import time
import random

# --- הגדרות ---
APP_URL = "https://lamdem-automation-bofurwgar4bmduns9g81fw.streamlit.app/"
USERNAME = "user_15"
PASSWORD = "final_step_25"

# פונקציה שמדמה הקלדה אנושית (לאט ובקצב משתנה)
def human_type(element, text):
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.1, 0.3)) # המתנה אקראית בין אותיות

def run_aggressive_bot():
    print(f"🚀 Starting HUMAN-LIKE bot for: {APP_URL}")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        # 1. כניסה לאתר
        driver.get(APP_URL)
        print("🌍 Entered site. Waiting for load...")
        time.sleep(15) 

        # 2. בדיקה אגרסיבית למצב שינה
        try:
            wake_btn = driver.find_elements(By.XPATH, "//button[contains(text(), 'Yes, get this app back up')]")
            if wake_btn:
                print("💤 Site is sleeping! Waking it up...")
                wake_btn[0].click()
                time.sleep(25) 
                driver.refresh()
                time.sleep(10)
            else:
                print("✅ Site is awake.")
        except:
            pass

        # 3. התחברות אנושית
        print("🔐 Attempting login...")
        inputs = driver.find_elements(By.TAG_NAME, "input")
        
        if len(inputs) >= 2:
            # הקלדה אנושית של שם המשתמש
            inputs[0].clear()
            human_type(inputs[0], USERNAME)
            time.sleep(1)
            
            # הקלדה אנושית של הסיסמה
            inputs[1].clear()
            human_type(inputs[1], PASSWORD)
            time.sleep(0.5)
            inputs[1].send_keys(Keys.RETURN)
            
            print("📤 Credentials sent. Logging in...")
            time.sleep(15) # מחכים שהמסך יתחלף בוודאות
        else:
            print("⚠️ Login inputs not found (maybe already logged in).")

        # 4. סימולציית משתמש פעיל (החלק האגרסיבי)
        # נשארים באתר דקה שלמה ומשחקים עם האלמנטים
        print("🤸 Starting random interaction loop (60 seconds)...")
        
        end_time = time.time() + 60
        body = driver.find_element(By.TAG_NAME, 'body')
        
        while time.time() < end_time:
            action_type = random.choice(['scroll', 'tab', 'arrows', 'hover'])
            
            if action_type == 'scroll':
                # גלילה למקום אקראי
                scroll_amount = random.randint(-300, 300)
                driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                print("   - Scrolled")
            
            elif action_type == 'tab':
                # לחיצה על TAB כדי לעבור בין כפתורים/סליידרים
                body.send_keys(Keys.TAB)
                print("   - Pressed Tab (Focus change)")
            
            elif action_type == 'arrows':
                # לחיצה על חצים (מזיז סליידרים אם הם בפוקוס)
                key = random.choice([Keys.ARROW_RIGHT, Keys.ARROW_LEFT, Keys.ARROW_DOWN])
                body.send_keys(key)
                print("   - Pressed Arrow Key")
            
            elif action_type == 'hover':
                # הזזת עכבר (וירטואלי) לאמצע המסך
                try:
                    action = ActionChains(driver)
                    action.move_by_offset(random.randint(10, 100), random.randint(10, 100)).perform()
                except: pass

            # המתנה אקראית בין פעולות (כמו בן אדם שחושב)
            time.sleep(random.uniform(2, 6))

        print("✅ Bot finished session successfully.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_aggressive_bot()
