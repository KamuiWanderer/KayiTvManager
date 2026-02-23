import os
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.errors import (
    FloodWait, PeerIdInvalid, ChatAdminRequired, 
    MessageIdInvalid, MessageNotModified, RPCError
)
from database import get_all_links, save_map, get_map

# Grab the Userbot Session from Render Environment Variables
USER_SESSION = os.environ.get("USER_SESSION")

# --- ERROR TRANSLATOR HELPER ---
def translate_error(e: Exception) -> str:
    """Translates raw Pyrogram errors into professional, human-readable messages."""
    if isinstance(e, FloodWait):
        return f"⏳ Rate Limited: Telegram requested a {e.value}s pause."
    elif isinstance(e, PeerIdInvalid):
        return "❌ Unknown Chat: The bot doesn't recognize this ID (Ensure it's an Admin and the ID starts with -100)."
    elif isinstance(e, ChatAdminRequired):
        return "❌ Missing Permissions: The bot lacks Admin rights to post/edit here."
    elif isinstance(e, MessageIdInvalid):
        return "❌ Message Not Found: This message ID does not exist or was deleted."
    elif isinstance(e, MessageNotModified):
        return "⚠️ Unchanged: The new text is exactly the same as the old text."
    elif isinstance(e, RPCError):
        return f"⚠️ Telegram API Error: {e.MESSAGE}"
    else:
        return f"⚠️ System Error: {type(e).__name__} - {str(e)}"

# --- 1. AUTO-MIRROR (Instantly copy new messages) ---
@Client.on_message(filters.channel)
async def auto_mirror(client, message):
    links = await get_all_links()
    link_data = next((l for l in links if l["main_id"] == message.chat.id), None)
    
    if not link_data or not link_data.get("storage_id"):
        return  
        
    try:
        copied = await message.copy(chat_id=link_data['storage_id'])
        await save_map(link_data['alias'], message.id, copied.id)
    except Exception as e:
        error_msg = translate_error(e)
        print(f"❌ Auto-Mirror Failed for {link_data['alias']}: {error_msg}")

# --- 2. BATCH SYNC COMMAND ---
@Client.on_message(filters.command("sync") & filters.private)
async def sync_cmd(client, message):
    if len(message.command) != 4:
        return await message.reply("❌ **Usage:** `/sync [Alias] [Start ID] [End ID]`")
    
    alias = message.command[1]
    start_id = int(message.command[2])
    end_id = int(message.command[3])
    
    links = await get_all_links()
    link_data = next((l for l in links if l["alias"] == alias), None)
    
    if not link_data or not link_data.get("storage_id"):
        return await message.reply("❌ Alias not found or no storage vault attached.")
        
    main_id = link_data["main_id"]
    storage_id = link_data["storage_id"]
    status_msg = await message.reply("🔄 **Starting Sync...**")
    
    total_messages = (end_id - start_id) + 1
    synced, failed = 0, 0
    error_log = {} 
    
    for msg_id in range(start_id, end_id + 1):
        try:
            fwd = await client.copy_message(chat_id=storage_id, from_chat_id=main_id, message_id=msg_id)
            await save_map(alias, msg_id, fwd.id)
            synced += 1
        except FloodWait as e:
            await asyncio.sleep(e.value + 2) 
            try:
                fwd = await client.copy_message(chat_id=storage_id, from_chat_id=main_id, message_id=msg_id)
                await save_map(alias, msg_id, fwd.id)
                synced += 1
            except Exception as retry_e:
                failed += 1
                error_log[msg_id] = translate_error(retry_e)
        except Exception as e:
            failed += 1
            error_log[msg_id] = translate_error(e)
            
        if (synced + failed) % 10 == 0:
            try:
                await status_msg.edit(
                    f"🔄 **Syncing `{alias}`...**\n\n"
                    f"✅ **Copied:** `{synced}`\n"
                    f"❌ **Failed:** `{failed}`\n"
                    f"📊 **Progress:** `{synced + failed} / {total_messages}`"
                )
            except MessageNotModified:
                pass 
                
    error_text = ""
    if failed > 0:
        error_text = "\n\n⚠️ **Error Report (Last 3):**\n"
        last_errors = list(error_log.items())[-3:]
        for failed_id, reason in last_errors:
            error_text += f"• **ID {failed_id}:** `{reason}`\n"
        if failed > 3:
            error_text += f"*(...and {failed - 3} other similar errors)*"
    
    await status_msg.edit(
        f"✅ **Sync Complete for `{alias}`!**\n\n"
        f"✅ **Successfully Synced:** `{synced}`\n"
        f"❌ **Failed/Skipped:** `{failed}`\n"
        f"📊 **Total Processed:** `{total_messages}`{error_text}"
    )

# --- 3. THE STEALTH ANALYZE COMMAND (USERBOT HYBRID) ---
@Client.on_message(filters.command("analyze") & filters.private)
async def analyze_cmd(client, message):
    if len(message.command) != 2:
        return await message.reply("❌ **Usage:** `/analyze [Alias]`\n*(No IDs needed, the Userbot will scan the live channel!)*")
        
    if not USER_SESSION:
        return await message.reply("❌ **System Error:** `USER_SESSION` is missing from Render Environment Variables!")

    alias = message.command[1]
    links = await get_all_links()
    link_data = next((l for l in links if l["alias"] == alias), None)
    
    if not link_data or not link_data.get("storage_id"):
        return await message.reply("❌ Channel not found or no storage vault attached.")
        
    main_id = link_data["main_id"]
    status = await message.reply(f"🚀 **Booting up Userbot Engine for `{alias}`...**")
    
    # Initialize the Userbot securely in memory so it doesn't conflict with your main bot
    user_app = Client("userbot_in_memory", session_string=USER_SESSION, in_memory=True)
    await user_app.start()
    
    missing_ids = []
    messages_checked = 0
    last_update_time = time.time()  # Start the stopwatch
    
    try:
        # Userbot reads the history of the channel
        async for msg in user_app.get_chat_history(main_id):
            if msg.empty or msg.service:
                continue # Skip deleted or system messages
                
            messages_checked += 1
            
            # Check if this visible message exists in our database
            vault_id = await get_map(alias, msg.id)
            if not vault_id:
                missing_ids.append(msg.id)
            
            current_time = time.time()
            
            # --- THE FATIGUE CURVE LOGIC (Every 50 msgs) ---
            if messages_checked % 50 == 0:
                # Math: 5s base + 2s per 100 messages, capped at 30s
                delay = 5 + ((messages_checked // 100) * 2)
                delay = min(delay, 30) 
                
                try:
                    await status.edit(
                        f"🛡 **Analyzing Channel:** `{alias}`\n"
                        f"⏳ **Status:** Anti-Ban Cooldown Active\n"
                        f"🛑 **Paused at:** `{messages_checked}` messages checked\n"
                        f"⏱ **Resuming in:** `{delay} seconds...`\n"
                        f"❌ **Missing Found:** `{len(missing_ids)}`"
                    )
                except MessageNotModified:
                    pass
                
                await asyncio.sleep(delay)
                
                # Reset stopwatch after waking up from sleep
                last_update_time = time.time() 
                
                try:
                    await status.edit(
                        f"🔍 **Analyzing Channel:** `{alias}`\n"
                        f"⚡️ **Status:** Actively Scanning...\n"
                        f"📊 **Messages Checked:** `{messages_checked}`\n"
                        f"❌ **Missing Found:** `{len(missing_ids)}`"
                    )
                except MessageNotModified:
                    pass

            # --- THE STOPWATCH UI UPDATE (Every 7 seconds) ---
            elif current_time - last_update_time >= 7:
                try:
                    await status.edit(
                        f"🔍 **Analyzing Channel:** `{alias}`\n"
                        f"⚡️ **Status:** Actively Scanning...\n"
                        f"📊 **Messages Checked:** `{messages_checked}`\n"
                        f"❌ **Missing Found:** `{len(missing_ids)}`"
                    )
                except MessageNotModified:
                    pass
                last_update_time = current_time # Reset stopwatch

    except Exception as e:
        await message.reply(f"⚠️ **Userbot Scan Interrupted:** `{str(e)}`")
    finally:
        await user_app.stop() # Always turn the Userbot off when done!
        
    # --- FINAL REPORT ---
    if not missing_ids:
        await status.edit(
            f"✅ **Perfect Sync!**\n\n"
            f"📊 **Scanned:** `{messages_checked}` visible messages.\n"
            f"Every single one is safely backed up in the vault."
        )
    else:
        # Sort them lowest to highest ID for easy syncing
        missing_ids.sort()
        
        report = (
            f"⚠️ **Scan Complete! Found {len(missing_ids)} missing messages.**\n\n"
            f"📊 **Total Scanned:** `{messages_checked}`\n"
            f"🔍 **First missing ID:** `{missing_ids[0]}`\n"
            f"🔍 **Last missing ID:** `{missing_ids[-1]}`\n\n"
        )
        
        # If there are a manageable amount, list them. If tons, just give the range.
        if len(missing_ids) <= 15:
            report += f"**Missing IDs:** `{', '.join(map(str, missing_ids))}`\n\n"
            
        report += f"**Fix it by running:**\n`/sync {alias} {missing_ids[0]} {missing_ids[-1]}`"
        
        await status.edit(report)
