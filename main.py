import sys
import os

print("✅ Checkpoint 1: Basic imports successful.")

try:
    import asyncio
    from pyrogram import Client, idle
    from keep_alive import start_ping_service
    print("✅ Checkpoint 2: Pyrogram and Flask imported.")

    # Fetching variables directly from Environment
    api_id_str = os.environ.get("API_ID")
    print(f"✅ Checkpoint 3: API_ID found: {bool(api_id_str)}")
    
    # This will crash if API_ID is missing from Render Environment Variables!
    API_ID = int(api_id_str) 

    API_HASH = os.environ.get("API_HASH")
    print(f"✅ Checkpoint 4: API_HASH found: {bool(API_HASH)}")

    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    print(f"✅ Checkpoint 5: BOT_TOKEN found: {bool(BOT_TOKEN)}")

except Exception as e:
    print(f"❌ CRASH DURING SETUP: {e}")
    sys.exit(1)

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
        print("🚀 Obito CMS is online!")
        start_ping_service()

async def main():
    try:
        print("✅ Checkpoint 6: Starting bot initialization...")
        app = Bot()
        await app.start()
        await idle()
        await app.stop()
    except Exception as e:
        print(f"❌ CRASH DURING RUNTIME: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ FATAL ERROR: {e}")
