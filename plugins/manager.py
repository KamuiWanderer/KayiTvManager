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
        return f"Rate Limited ({e.value}s pause)"
    elif isinstance(e, PeerIdInvalid):
        return "Unknown Chat (Check Admin rights/ID)"
    elif isinstance(e, ChatAdminRequired):
        return "Missing Permissions (Not an Admin)"
    elif isinstance(e, MessageIdInvalid):
        return "Message Not Found (Deleted or invalid)"
    elif isinstance(e, MessageNotModified):
        return "Unchanged text"
    elif isinstance(e, RPCError):
        return f"API Error: {e.MESSAGE}"
    else:
        return f"System Error: {type(e).__name__}"

# --- 1. AUTO-MIRROR (Instantly copy new live messages) ---
@Client.on_message(filters.channel)
async def auto_mirror(client, message):
    links = await get_all_links()
    link_data = next((l for l in links if int(l["main_id"]) == message.chat.id), None)
    
    if not link_data or not link_data.get("storage_id"):
        return  
        
    try:
        copied = await message.copy(chat_id=int(link_data['storage_id']))
        await save_map(link_data['alias'], message.id, copied.id)
    except Exception as e:
        error_msg = translate_error(e)
        print(f"❌ Auto-Mirror Failed for {link_data['alias']}: {error_msg}")

# --- 2. THE ULTIMATE RELOAD COMMAND (Scan + Auto-Sync) ---
# Added 'group=1' to bypass ANY command clashes or conversation traps!
@Client.on_message(filters.command(["resync", "reload"]) & filters.private, group=1)
async def reload_cmd(client, message):
    print(f"🚨 [SYSTEM] Command received: {message.text}") # Forces a log entry!
    
    if len(message.command) != 2:
        return await message.reply("❌ **Usage:** `/resync [Alias]`")
        
    if not USER_SESSION:
        return await message.reply("❌ **System Error:** `USER_SESSION` is missing from Render Environment Variables!")

    alias = message.command[1]
    links = await get_all_links()
    link_data = next((l for l in links if l["alias"] == alias), None)
    
    if not link_data or not link_data.get("storage_id"):
        return await message.reply("❌ Channel not found or no storage vault attached.")
        
    # FORCE THESE TO BE INTEGERS TO FIX PEER_ID_INVALID
    main_id = int(link_data["main_id"])
    storage_id = int(link_data["storage_id"])
    
    status = await message.reply(f"🚀 **Booting up Userbot Engine for `{alias}`...**")
    
    # Initialize the Userbot securely in memory
    user_app = Client("userbot_in_memory", session_string=USER_SESSION, in_memory=True)
    await user_app.start()
    
    # --- CURE THE AMNESIA (Fix for PeerIdInvalid) ---
    try:
        await user_app.get_chat(main_id)
    except (PeerIdInvalid, ValueError, KeyError):
        await status.edit(f"🔄 **Syncing Userbot memory... (Grabbing access hashes)**")
        async for _ in user_app.get_dialogs(limit=200):
            pass  # Silently caches all chat IDs so it recognizes the channel
            
    missing_ids = []
    messages_checked = 0
    last_update_time = time.time()  
    
    # ==========================================
    # PHASE 1: STEALTH SCANNING (Userbot)
    # ==========================================
    try:
        async for msg in user_app.get_chat_history(main_id):
            if msg.empty or msg.service:
                continue 
                
            messages_checked += 1
            
            # Check DB
            vault_id = await get_map(alias, msg.id)
            if not vault_id:
                missing_ids.append(msg.id)
            
            current_time = time.time()
            
            # --- FATIGUE CURVE (Every 50 msgs) ---
            if messages_checked % 50 == 0:
                delay = 5 + ((messages_checked // 100) * 2)
                delay = min(delay, 30) 
                
                try:
                    await status.edit(
                        f"🛡 **PHASE 1: Scanning `{alias}`**\n"
                        f"⏳ **Status:** Anti-Ban Cooldown Active\n"
                        f"🛑 **Paused at:** `{messages_checked}` messages checked\n"
                        f"⏱ **Resuming in:** `{delay} seconds...`\n"
                        f"❌ **Missing Found:** `{len(missing_ids)}`"
                    )
                except MessageNotModified:
                    pass
                
                await asyncio.sleep(delay)
                last_update_time = time.time() 
                
            # --- STOPWATCH UI (Every 7 seconds) ---
            elif current_time - last_update_time >= 7:
                try:
                    await status.edit(
                        f"🔍 **PHASE 1: Scanning `{alias}`**\n"
                        f"⚡️ **Status:** Actively Scanning...\n"
                        f"📊 **Messages Checked:** `{messages_checked}`\n"
                        f"❌ **Missing Found:** `{len(missing_ids)}`"
                    )
                except MessageNotModified:
                    pass
                last_update_time = current_time 

    except Exception as e:
        await user_app.stop()
        return await message.reply(f"⚠️ **Userbot Scan Interrupted:** `{str(e)}`")
        
    await user_app.stop() # Turn off Userbot, hand over to Main Bot
    
    # ==========================================
    # PHASE 2: AUTO-SYNCING (Main Bot)
    # ==========================================
    if not missing_ids:
        return await status.edit(
            f"✅ **Perfect Sync!**\n\n"
            f"📊 **Scanned:** `{messages_checked}` visible messages.\n"
            f"Every single one is safely backed up in the vault. No reload needed."
        )

    missing_ids.sort() # Sync from oldest to newest
    total_missing = len(missing_ids)
    synced, failed = 0, 0
    error_log = {}
    
    sync_last_update = time.time()
    
    for msg_id in missing_ids:
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
            
        # --- SYNC STOPWATCH UI (Every 7 seconds) ---
        if time.time() - sync_last_update >= 7:
            try:
                await status.edit(
                    f"🔄 **PHASE 2: Auto-Syncing `{alias}`**\n\n"
                    f"✅ **Copied:** `{synced}`\n"
                    f"❌ **Failed:** `{failed}`\n"
                    f"📊 **Progress:** `{synced + failed} / {total_missing}`"
                )
            except MessageNotModified:
                pass 
            sync_last_update = time.time()
                
    # ==========================================
    # PHASE 3: FINAL REPORT & ERROR LOGGING
    # ==========================================
    await status.edit(
        f"✅ **Reload Complete for `{alias}`!**\n\n"
        f"🔍 **Total Scanned:** `{messages_checked}`\n"
        f"✅ **Successfully Synced:** `{synced}`\n"
        f"❌ **Failed:** `{failed}`"
    )
    
    # Send detailed errors as a completely separate message if any failed
    if failed > 0:
        error_text = f"⚠️ **Detailed Error Log for `{alias}`:**\n\n"
        for failed_id, reason in error_log.items():
            error_text += f"• **ID {failed_id}:** `{reason}`\n"
            
        if len(error_text) > 4000:
            error_text = error_text[:4000] + "\n\n*(...Log truncated due to Telegram length limits)*"
            
        await message.reply(error_text)
