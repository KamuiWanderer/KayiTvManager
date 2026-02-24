import sys
import asyncio
from pyrogram import Client, idle
from config import API_ID, API_HASH, BOT_TOKEN
from keep_alive import start_ping_service

print("✅ [1/4] Imports loaded.")

if not API_ID or not API_HASH or not BOT_TOKEN:
    print("❌ FATAL: API_ID, API_HASH, or BOT_TOKEN is missing from environment variables.")
    sys.exit(1)

print("✅ [2/4] Environment variables verified.")

class Bot(Client):
    def __init__(self):
        super().__init__(
            "ObitoCMS",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins=dict(root="plugins")
        )

    async def start(self):
        await super().start()
        me = await self.get_me()
        print(f"✅ [4/4] Bot online → @{me.username}")
        start_ping_service()

async def main():
    print("✅ [3/4] Starting bot...")
    app = Bot()
    try:
        await app.start()
        await idle()
    finally:
        await app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ FATAL: {e}")
        sys.exit(1)
