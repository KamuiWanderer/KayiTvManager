import time
import traceback
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
    try:
        start_ping = time.time()
        reply = await message.reply_text("🔄 **Checking Render vitals...**")
        
        # Calculate Latencies
        tg_ping = round((time.time() - start_ping) * 1000, 2)
        mongo_ping = await db_ping()
        
        # Fetch System Metrics via psutil
        uptime = get_readable_time(time.time() - bot_start_time)
        cpu_usage = psutil.cpu_percent(interval=0.2) 
        ram = psutil.virtual_memory()
        
        # Cloud containers often block root directory access, so we wrap this in a try-except
        try:
            disk = psutil.disk_usage('/')
            disk_text = f"`{disk.percent}%` ({get_readable_size(disk.used)} / {get_readable_size(disk.total)})"
        except Exception:
            disk_text = "⚠️ `Access Restricted by Render`"
        
        stats_msg = (
            "**🖥️ OBITO CMS: SYSTEM HEALTH**\n\n"
            f"**🟢 Bot Uptime:** `{uptime}`\n"
            f"**🌐 Telegram Ping:** `{tg_ping} ms`\n"
            f"**🗄️ Database Ping:** `{mongo_ping} ms`\n\n"
            f"**⚙️ CPU Usage:** `{cpu_usage}%`\n"
            f"**🖨️ RAM Usage:** `{ram.percent}%` ({get_readable_size(ram.used)} / {get_readable_size(ram.total)})\n"
            f"**💽 Disk Space:** {disk_text}\n"
        )
        
        await reply.edit_text(stats_msg)
        
    except Exception as e:
        # If it STILL fails, it will print the exact error directly to your Telegram chat
        error_trace = traceback.format_exc()
        print(f"SERVER CMD ERROR:\n{error_trace}")
        await message.reply_text(f"❌ **Fatal Error generating stats:**\n`{e}`")
