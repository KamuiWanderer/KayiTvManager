import asyncio
from pyrogram import Client, filters
from database import links_collection, save_map, get_link_by_main_id,get_all_links
from pyrogram.errors import FloodWait



# 1. LIVE MIRROR (Fixed filter syntax here!)
@Client.on_message(filters.channel & ~filters.service)
async def auto_mirror(client, message):
    data = await get_link_by_main_id(message.chat.id)
    if not data: return
    
    copied = await message.copy(chat_id=data['storage_id'])
    await save_map(data['alias'], message.id, copied.id)

# 2. ANALYZE
@Client.on_message(filters.command("analyze") & filters.private)
async def analyze_chnl(client, message):
    if len(message.command) < 2: return await message.reply("Usage: `/analyze Alias`")
    alias = message.command[1]
    data = await links_collection.find_one({"alias": alias})
    if not data: return await message.reply("Alias not found.")

    status = await message.reply("🔬 Scanning... ⏳")
    eps, files = 0, 0
    async for m in client.get_chat_history(data['main_id']):
        text = (m.text or m.caption or "")
        if "Episode" in text and "👇" in text: eps += 1
        if m.video or m.document: files += 1
    await status.edit(f"📊 **{alias} Report**\n🎬 Episodes: `{eps}`\n📽️ Files: `{files}`")

# 3. SYNC
@Client.on_message(filters.command("sync") & filters.private)
async def sync_cmd(client, message):
    if len(message.command) != 4:
        return await message.reply("❌ **Usage:** `/sync [Alias] [Start ID] [End ID]`")
    
    alias = message.command[1]
    start_id = int(message.command[2])
    end_id = int(message.command[3])
    
    # 1. Verify link exists
    links = await get_all_links()
    link_data = next((l for l in links if l["alias"] == alias), None)
    
    if not link_data:
        return await message.reply(f"❌ Could not find alias `{alias}` in database.")
        
    main_id = link_data["main_id"]
    storage_id = link_data.get("storage_id")
    
    if not storage_id:
        return await message.reply("❌ This is a standalone channel. There is no storage vault to sync to!")
        
    status_msg = await message.reply("🔄 **Starting Sync...**")
    
    total_messages = (end_id - start_id) + 1
    synced = 0
    failed = 0
    
    # 2. Iterate through IDs from oldest to newest (Fixes the Pyrogram error)
    for msg_id in range(start_id, end_id + 1):
        try:
            # Copy message without 'forwarded from' tag
            fwd = await client.copy_message(
                chat_id=storage_id,
                from_chat_id=main_id,
                message_id=msg_id
            )
            # Map the new ID
            await save_map(alias, msg_id, fwd.id)
            synced += 1
            
        except FloodWait as e:
            await asyncio.sleep(e.value + 2) # Pause if Telegram rate limits us
            
        except Exception:
            # Message might be deleted, or it's a service message
            failed += 1
            
        # 3. Live Progress Bar (Updates every 10 messages to avoid spamming the API)
        if (synced + failed) % 10 == 0:
            try:
                await status_msg.edit(
                    f"🔄 **Syncing `{alias}`...**\n\n"
                    f"✅ **Copied:** `{synced}`\n"
                    f"❌ **Failed/Skipped:** `{failed}`\n"
                    f"📊 **Progress:** `{synced + failed} / {total_messages}`"
                )
            except Exception:
                pass # Ignore "message is not modified" errors
                
    await status_msg.edit(
        f"✅ **Sync Complete for `{alias}`!**\n\n"
        f"✅ **Successfully Synced:** `{synced}`\n"
        f"❌ **Failed/Skipped:** `{failed}`\n"
        f"📊 **Total Processed:** `{total_messages}`"
    )
