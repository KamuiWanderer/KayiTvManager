import asyncio
import os
from pyrogram import Client, idle
from keep_alive import start_ping_service

# Fetching variables directly from Environment (Render)
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

class Bot(Client):
    def __init__(self):
        super().__init__(
            "ObitoCMS",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins=dict(root="plugins") # This loads all our new features automatically
        )

    async def start(self):
        await super().start()
        print("🚀 Obito CMS is online!")
        # Self-pinging Flask server starts here
        start_ping_service()

async def main():
    app = Bot()
    await app.start()
    await idle() # Keeps the bot running until you stop it
    await app.stop()

if __name__ == "__main__":
    # Python 3.12+ safe entry point
    asyncio.run(main())
