import urllib.request
import time

# הכתובת של האתר הגרפי שלך
APP_URL = "https://lamdem-automation-bofurwgar4bmduns9g8lfw.streamlit.app/"

print(f"--- Waking up the App: {APP_URL} ---")

try:
    # ניסיון גישה לאתר כדי להעיר אותו
    with urllib.request.urlopen(APP_URL) as response:
        print(f"Success! Status code: {response.getcode()}")
        print("The app is awake and running.")
except Exception as e:
    print(f"Error pinging the app: {e}")
