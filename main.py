import asyncio
import sys
from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID
from keep_alive import start_ping_service

# --- FIX FOR PYTHON 3.12+ ASYNCIO ERROR ---
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
# ------------------------------------------

class Bot(Client):
    def __init__(self):
        super().__init__(
            "ProductionBot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins=dict(root="plugins")
        )

    async def start(self):
        await super().start()
        print("Bot is online!")
        try:
            await self.send_message(OWNER_ID, "🔄 **Bot Restarted Successfully!**\nSystem: Render (Python 3.14)")
        except Exception as e:
            print(f"Could not notify owner: {e}")

    async def stop(self, *args):
        await super().stop()
        print("Bot stopped.")

async def run_bot():
    # Start the Flask server
    start_ping_service()
    
    # Initialize and start the bot
    app = Bot()
    await app.start()
    
    # Keep the bot running until interrupted
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        loop.run_until_complete(run_bot())
    except KeyboardInterrupt:
        pass
