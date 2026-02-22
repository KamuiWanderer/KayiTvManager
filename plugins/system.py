import time
import requests
from pyrogram import Client, filters
from database import db_ping

@Client.on_message(filters.command("ping") & filters.private)
async def ping_handler(client, message):
    start = time.perf_counter()
    sent = await message.reply("📡 `System Diagnostics...`")
    tg_latency = round((time.perf_counter() - start) * 1000)
    
    mongo_latency = await db_ping()
    
    # Check if the local Flask server is responding
    try:
        response = requests.get("http://localhost:8080", timeout=1)
        alive_status = "✅ Active" if response.status_code == 200 else "⚠️ Unresponsive"
    except:
        alive_status = "❌ Offline"

    await sent.edit(
        f"🚀 **Performance Report**\n\n"
        f"🌐 **Telegram API:** `{tg_latency}ms`\n"
        f"🗄️ **Database:** `{mongo_latency}ms`\n"
        f"🩺 **Keep-Alive:** `{alive_status}`\n"
        f"⚡ **Latency Rank:** {'Excellent' if tg_latency < 200 else 'Stable'}"
    )

@Client.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    await message.reply(
        f"👋 **Hello {message.from_user.first_name}!**\n\n"
        "I am your professional Channel Manager. Use me to link public channels to private storage vaults.\n\n"
        "🛠 **Commands:**\n"
        "• `/register` - Link two channels\n"
        "• `/links` - View/Manage linked channels\n"
        "• `/ping` - Check system health"
    )
