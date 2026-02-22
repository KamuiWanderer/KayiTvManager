import os
import time
import requests
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "System Online & Pinging"

def run():
    app.run(host='0.0.0.0', port=8080)

def ping_self():
    # Wait for server to start
    time.sleep(10)
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url:
        print("Keep-Alive: RENDER_EXTERNAL_URL not set. Self-ping disabled.")
        return

    while True:
        try:
            requests.get(url)
            print(f"Keep-Alive: Pinged {url} successfully.")
        except Exception as e:
            print(f"Keep-Alive Error: {e}")
        time.sleep(600) # Ping every 10 minutes

def start_ping_service():
    t1 = Thread(target=run)
    t2 = Thread(target=ping_self)
    t1.start()
    t2.start()
