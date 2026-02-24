import time
from pyrogram import Client, filters
import database  # Import the whole module

@Client.on_message(filters.command("ping") & filters.private)
async def ping_handler(client, message):
    try:
        start = time.perf_counter()
        sent = await message.reply("📡 `System Diagnostics...`")
        tg_latency = round((time.perf_counter() - start) * 1000)
        
        # Test DB connection
        mongo_latency = await database.db_ping()
        
        await sent.edit(
            f"🚀 **Performance Report**\n\n"
            f"🌐 **Telegram API:** `{tg_latency}ms`\n"
            f"🗄️ **Database:** `{mongo_latency}ms`"
        )
    except Exception as e:
        await message.reply(f"❌ **Ping Logic Error:** `{e}`")

@Client.on_message(filters.command("test_db") & filters.private)
async def test_db_handler(client, message):
    try:
        sent = await message.reply("🛠 `Testing Module 1 Database Logic...`")
        
        success = await database.add_episode_file(
            alias="TestSeries",
            season_no=1,
            ep_no=1,
            quality="720p",
            file_id="TEST_ID",
            storage_msg_id=123
        )
        
        if success:
            await sent.edit("✅ **Module 1 Success!** Data tree created in MongoDB.")
        else:
            await sent.edit("❌ **Module 1 Failed.** Check logs.")
            
    except Exception as e:
        await message.reply(f"❌ **DB Test Crash:** `{e}`")

@Client.on_message(filters.command("server") & filters.private)
async def server_handler(client, message):
    # Simplest possible version to check if it even triggers
    await message.reply("📟 **Server command received!** (If you see this, the command is working).")
