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

def get_readable_size(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0

@Client.on_message(filters.command("server") & filters.private)
async def server_status(client, message):
    start_ping = time.time()
    reply = await message.reply_text("🔄 **Checking Render vitals...**")
    
    # Calculate Latencies
    tg_ping = round((time.time() - start_ping) * 1000, 2)
    mongo_ping = await db_ping()
    
    # Fetch System Metrics via psutil
    uptime = get_readable_time(time.time() - bot_start_time)
    cpu_usage = psutil.cpu_percent(interval=0.5) 
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    stats_msg = (
        "**🖥️ OBITO CMS: SYSTEM HEALTH**\n\n"
        f"**🟢 Bot Uptime:** `{uptime}`\n"
        f"**🌐 Telegram Ping:** `{tg_ping} ms`\n"
        f"**🗄️ Database Ping:** `{mongo_ping} ms`\n\n"
        f"**⚙️ CPU Usage:** `{cpu_usage}%`\n"
        f"**🖨️ RAM Usage:** `{ram.percent}%` ({get_readable_size(ram.used)} / {get_readable_size(ram.total)})\n"
        f"**💽 Disk Space:** `{disk.percent}%` ({get_readable_size(disk.used)} / {get_readable_size(disk.total)})\n"
    )
    
    await reply.edit_text(stats_msg)
