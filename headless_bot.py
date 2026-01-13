import urllib.request
import time

# הכתובת של האתר שלך
APP_URL = "https://lamdem-automation-bofurwgar4bmduns9g81fw.streamlit.app/"

def ping_site():
    print(f"Pinging app: {APP_URL}")
    
    # אנחנו יוצרים "בקשה" שמזייפת דפדפן אמיתי (כרום)
    # זה מונע מהשרת לחסום את הבוט ומראה פעילות אמיתית
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        req = urllib.request.Request(APP_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            print(f"Success! Status: {response.getcode()}")
            # קוראים קצת מהתוכן כדי לוודא שהשרת באמת שלח מידע
            content = response.read(100) 
            print("Server responded actively.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    ping_site()
