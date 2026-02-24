import time
import requests
from pyrogram import Client, filters
from database import db_ping

# Try to import psutil safely
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

bot_start_time = time.time()

def get_readable_time(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    return f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"

@Client.on_message(filters.command("ping") & filters.private)
async def ping_handler(client, message):
    start = time.perf_counter()
    sent = await message.reply("📡 `System Diagnostics...`")
    tg_latency = round((time.perf_counter() - start) * 1000)
    mongo_latency = await db_ping()
    
    await sent.edit(
        f"🚀 **Performance Report**\n\n"
        f"🌐 **Telegram API:** `{tg_latency}ms`\n"
        f"🗄️ **Database:** `{mongo_latency}ms`"
    )

@Client.on_message(filters.command("server") & filters.private)
async def server_handler(client, message):
    try:
        uptime = get_readable_time(time.time() - bot_start_time)
        
        if not PSUTIL_AVAILABLE:
            return await message.reply(f"🟢 **Bot is Alive**\n\n⌚ **Uptime:** `{uptime}`\n⚠️ `psutil` library failed to load.")

        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        
        stats = (
            "**🖥️ SERVER DASHBOARD**\n\n"
            f"**⌚ Uptime:** `{uptime}`\n"
            f"**⚙️ CPU Load:** `{cpu}%`\n"
            f"**🖨️ RAM Usage:** `{ram}%`"
        )
        await message.reply(stats)
    except Exception as e:
        await message.reply(f"❌ **Server Cmd Error:** `{str(e)}`")

@Client.on_message(filters.command(["start", "help"]) & filters.private)
async def start_command(client, message):
    await message.reply("👋 **Obito CMS is Active.**\n\nTry `/ping` or `/server` to test the connection.")
