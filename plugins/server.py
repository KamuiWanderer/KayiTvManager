import time
import psutil
from pyrogram import Client, filters
from database import db_ping

# Track the exact moment the bot starts up
bot_start_time = time.time()

def get_readable_time(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    return f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"

@Client.on_message(filters.command("server") & filters.private)
async def server_status(client, message):
    try:
        start_ping = time.time()
        reply = await message.reply_text("🔄 **Accessing Render Core...**")
        
        # Latencies
        tg_ping = round((time.time() - start_ping) * 1000, 2)
        mongo_ping = await db_ping()
        
        # System Metrics
        uptime = get_readable_time(time.time() - bot_start_time)
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        
        stats_msg = (
            "**🖥️ OBITO CMS: VITAL SIGNS**\n\n"
            f"**🟢 Uptime:** `{uptime}`\n"
            f"**🌐 Latency:** `{tg_ping}ms`\n"
            f"**🗄️ Database:** `{mongo_ping}ms`\n\n"
            f"**⚙️ CPU Load:** `{cpu}%`\n"
            f"**🖨️ RAM Usage:** `{ram}%`"
        )
        
        await reply.edit_text(stats_msg)
    except Exception as e:
        await message.reply_text(f"❌ **Server Module Error:** `{e}`")
