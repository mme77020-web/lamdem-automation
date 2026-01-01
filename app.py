from selenium import webdriver
from selenium.webdriver.chrome.options import Options
# ... שאר הייבואים (הסר את ChromeDriverManager ואת Service אם לא צריך)

def run_process(user_id, user_pass, log_box):
    options = Options()
    options.add_argument("--headless=new")  # חובה לגרסאות חדשות, יותר יציב
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")  # עוזר ביציבות

    # אין צורך ב-Service או Manager – Selenium משתמש אוטומטית ב-chromedriver המותקן
    try:
        driver = webdriver.Chrome(options=options)
        
        driver.get("https://chabad.lamdem.co.il/auth/login")
        time.sleep(5)
        
        driver.find_element(By.CSS_SELECTOR, "input[formcontrolname='identifier']").send_keys(str(user_id))
        driver.find_element(By.ID, "pwd").send_keys(str(user_pass) + Keys.RETURN)
        
        log_box.info(f"🔄 עובד על תלמיד: {user_id}")
        time.sleep(10)
        
        # ... הלוגיקה של הסרטונים שלך כאן
        
        driver.quit()
        return True
        
    except Exception as e:
        if 'driver' in locals():
            driver.quit()
        log_box.error(f"❌ שגיאה: {e}")
        return False
