import asyncio
from pyrogram import Client, filters
from database import links_collection, save_map, get_link_by_main_id

# 1. LIVE MIRRORING (Multi-Channel Aware)
@Client.on_message(filters.chat_type.CHANNEL & ~filters.service)
async def auto_mirror(client, message):
    data = await get_link_by_main_id(message.chat.id)
    if not data: return
    
    # Copy without forward tag
    copied = await message.copy(chat_id=data['storage_id'])
    await save_map(data['alias'], message.id, copied.id)

# 2. ANALYSIS
@Client.on_message(filters.command("analyze") & filters.private)
async def analyze_chnl(client, message):
    if len(message.command) < 2: return await message.reply("Usage: `/analyze Marvel`")
    alias = message.command[1]
    data = await links_collection.find_one({"alias": alias})
    if not data: return await message.reply("Alias not found.")

    status = await message.reply("🔬 Scanning... ⏳")
    eps, files = 0, 0
    async for m in client.get_chat_history(data['main_id']):
        text = (m.text or m.caption or "")
        if "Episode" in text and "👇" in text: eps += 1
        if m.video or m.document: files += 1
    await status.edit(f"📊 **{alias} Report**\n\n🎬 Episodes: `{eps}`\n📽️ Files: `{files}`")

# 3. SEQUENTIAL SYNC (History Gap Filler)
@Client.on_message(filters.command("sync") & filters.private)
async def sync_history(client, message):
    if len(message.command) < 2: return await message.reply("Usage: `/sync Alias`")
    alias = message.command[1]
    data = await links_collection.find_one({"alias": alias})
    
    prog = await message.reply("🔄 Starting Sequential Sync...")
    count = 0
    async for m in client.get_chat_history(data['main_id'], reverse=True):
        if m.service: continue
        copied = await m.copy(chat_id=data['storage_id'])
        await save_map(alias, m.id, copied.id)
        count += 1
        if count % 20 == 0: await prog.edit(f"🔄 Syncing... `{count}` done.")
        await asyncio.sleep(0.5)
    await prog.edit(f"✅ Sync Complete: `{count}` messages mirrored.")
