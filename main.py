import asyncio
from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID
from keep_alive import start_ping_service

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
        print("Bot Online.")
        try:
            await self.send_message(OWNER_ID, "🔄 **Bot Restarted**\nRegion: Render-Singapore ↔ Atlas-Mumbai")
        except Exception as e:
            print(f"Owner DM failed: {e}")

if __name__ == "__main__":
    start_ping_service() # Starts Flask server
    app = Bot()
    app.run()
