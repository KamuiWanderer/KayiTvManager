import os, time, requests
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home(): return "Obito CMS Online"

def run(): app.run(host='0.0.0.0', port=8080)

def ping_self():
    time.sleep(30)
    url = os.environ.get("RENDER_EXTERNAL_URL")
    while url:
        try: requests.get(url, timeout=10)
        except: pass
        time.sleep(300)

def start_ping_service():
    Thread(target=run).start()
    Thread(target=ping_self).start()
