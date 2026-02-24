import time
import asyncio
import psutil
import platform
from pyrogram import Client, filters
from pyrogram.types import Message
import database
from config import is_admin

# Track when the bot process started so we can show uptime
BOT_START_TIME = time.time()


def format_uptime(seconds: float) -> str:
    seconds = int(seconds)
    days,    seconds = divmod(seconds, 86400)
    hours,   seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if days:    parts.append(f"{days}d")
    if hours:   parts.append(f"{hours}h")
    if minutes: parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


def format_bytes(b: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"


def bar(pct, width=10):
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


# ── /start ────────────────────────────────────────────────────────────────────
@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    await message.reply(
        "👾 **Obito VOD CMS is online.**\n\n"
        "Use `/ping` to check system health.\n"
        "Use `/server` for a full live dashboard.\n"
        "Use `/links` to view registered channels."
    )


# ── /ping ─────────────────────────────────────────────────────────────────────
@Client.on_message(filters.command("ping") & filters.private)
async def ping_handler(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply("🚫 **Access Denied.**")

    # FIX: Measure latency by timing the reply itself (not an edit).
    # Editing to the same text causes MESSAGE_NOT_MODIFIED.
    # Instead we time how long message.reply() takes — that IS the round trip.
    tg_start = time.perf_counter()
    sent = await message.reply("`📡 Pinging...`")
    tg_latency = round((time.perf_counter() - tg_start) * 1000)

    # MongoDB round-trip
    db_latency = await database.db_ping()
    db_text = f"`{db_latency}ms`" if db_latency != "Offline" else "🔴 `Offline`"

    # Now edit to the real result — different text so no MESSAGE_NOT_MODIFIED
    await sent.edit(
        f"🚀 **System Ping**\n\n"
        f"📡 **Telegram:**  `{tg_latency}ms`\n"
        f"🗄️ **MongoDB:**   {db_text}"
    )


# ── /server ───────────────────────────────────────────────────────────────────
@Client.on_message(filters.command("server") & filters.private)
async def server_handler(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply("🚫 **Access Denied.**")

    # FIX: Same approach — time the initial reply, then edit with full results.
    tg_start = time.perf_counter()
    sent = await message.reply("`⏳ Collecting system data...`")
    tg_latency = round((time.perf_counter() - tg_start) * 1000)

    # ── Gather stats ──────────────────────────────────────────────────────────
    uptime_str = format_uptime(time.time() - BOT_START_TIME)

    cpu_pct   = psutil.cpu_percent(interval=1)
    cpu_cores = psutil.cpu_count(logical=True)

    ram       = psutil.virtual_memory()
    ram_used  = format_bytes(ram.used)
    ram_total = format_bytes(ram.total)
    ram_pct   = ram.percent

    disk       = psutil.disk_usage("/")
    disk_used  = format_bytes(disk.used)
    disk_total = format_bytes(disk.total)
    disk_pct   = disk.percent

    db_latency = await database.db_ping()
    db_text    = f"`{db_latency}ms`" if db_latency != "Offline" else "🔴 `Offline`"

    await sent.edit(
        f"🖥️ **SERVER DASHBOARD**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🤖 **Bot Uptime:**\n"
        f"    `{uptime_str}`\n\n"
        f"⚡ **CPU Usage:** `{cpu_pct}%`  ({cpu_cores} cores)\n"
        f"    `{bar(cpu_pct)}`\n\n"
        f"🧠 **RAM Usage:** `{ram_used} / {ram_total}` ({ram_pct}%)\n"
        f"    `{bar(ram_pct)}`\n\n"
        f"💾 **Disk Usage:** `{disk_used} / {disk_total}` ({disk_pct}%)\n"
        f"    `{bar(disk_pct)}`\n\n"
        f"📡 **Telegram Ping:** `{tg_latency}ms`\n"
        f"🗄️ **MongoDB Ping:** {db_text}\n\n"
        f"🖱 **Platform:** `{platform.system()} {platform.release()}`"
    )
