import asyncio
from pyrogram import Client, idle
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
        print("Bot is online!")
        try:
            await self.send_message(OWNER_ID, "🚀 **Bot Started on Render**\nEnvironment: Python 3.12")
        except:
            pass

async def main():
    # Start the Flask Keep-Alive server
    start_ping_service()
    
    # Initialize and start the bot
    app = Bot()
    await app.start()
    
    # Keep the bot alive
    await idle()
    
    # Stop gracefully
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
