import urllib.request

# הכתובת של האתר הגרפי שלך
APP_URL = "https://lamdem-automation-bofurwgar4bmduns9g8lfw.streamlit.app/"

print(f"Pinging app: {APP_URL}")

try:
    with urllib.request.urlopen(APP_URL) as response:
        print(f"Success! Status: {response.getcode()}")
except Exception as e:
    print(f"Error: {e}")
