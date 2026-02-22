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

from pyrogram import Client, filters

@Client.on_message(filters.command(["start", "help"]) & filters.private)
async def start_command(client, message):
    welcome_text = (
        "👋 **Hello! I am your professional Channel Manager Bot.**\n\n"
        "I am designed to seamlessly link public channels to private storage vaults, "
        "sync your content, and allow you to edit messages in both places simultaneously.\n\n"
        "🛠 **Available Commands:**\n"
        "• `/register [Alias] [MainID] [StorageID]` - Link a new channel pair.\n"
        "• `/links` - View and manage your currently linked channels.\n"
        "• `/msg [Message Link]` - Edit a specific message in both the main channel and storage vault.\n"
        "• `/sync [Alias] [Start ID] [End ID]` - Batch forward old messages into the storage vault.\n"
        "• `/analyze [Alias]` - Check for missing messages in the vault.\n"
        "• `/ping` - Check my system health and database latency.\n\n"
        "💡 *Tip: Make sure I am an Administrator in both the Main Channel and the Storage Vault!*"
    )
    
    await message.reply(welcome_text)
