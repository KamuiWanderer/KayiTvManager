import re
from pyrogram import Client, filters
from database import get_all_links, get_map

# Global dictionary to track users who are in the middle of editing a message
# Format: {user_id: {"storage_chat_id": 123, "storage_msg_id": 456, "main_chat_id": 789, "main_msg_id": 10}}
EDIT_STATE = {}

@Client.on_message(filters.command("msg") & filters.private)
async def msg_command(client, message):
    if len(message.command) < 2:
        return await message.reply(
            "❌ **Incorrect Usage!**\n\n"
            "**Format:** `/msg [Telegram Link]`\n"
            "**Example:** `/msg https://t.me/VefaSultanUrduSubs/9`"
        )
    
    link = message.command[1]
    
    if "t.me/" not in link:
        return await message.reply("❌ **Invalid Link Format.**\nPlease provide a valid Telegram message link.")
    
    # --- 1. SMART LINK EXTRACTOR ---
    try:
        parts = link.rstrip("/").split("/")
        msg_id = int(parts[-1])
        
        # If it's a private link (t.me/c/123456789/9)
        if "c" in parts:
            c_index = parts.index("c")
            main_chat = int("-100" + parts[c_index + 1])
        else:
            # If it's a public link (t.me/Username/9)
            main_chat = parts[-2]
            
    except Exception as e:
        return await message.reply(f"❌ **Could not extract ID from the link.**\nError: {e}")

    # --- 2. FIND THE ALIAS AND DATABASE MATCH ---
    status_msg = await message.reply("🔍 Searching database for this channel...")
    links = await get_all_links()
    
    target_alias = None
    storage_chat_id = None
    main_chat_id_db = None
    
    # Resolve the chat ID if the user provided a public username link
    if isinstance(main_chat, str):
        try:
            chat_obj = await client.get_chat(main_chat)
            main_chat_resolved = chat_obj.id
        except Exception:
            return await status_msg.edit("❌ **Could not find that public channel.**\nMake sure the bot is an admin there.")
    else:
        main_chat_resolved = main_chat

    # Match the resolved ID against our registered links
    for l in links:
        if l["main_id"] == main_chat_resolved:
            target_alias = l["alias"]
            storage_chat_id = l["storage_id"]
            main_chat_id_db = l["main_id"]
            break
            
    if not target_alias:
        return await status_msg.edit(f"❌ This channel is not registered in the bot.\nUse `/register` to link it first.")
        
    # --- 3. FETCH THE STORAGE MESSAGE ID (IF IT HAS A VAULT) ---
    storage_msg_id = None
    if storage_chat_id:
        storage_msg_id = await get_map(target_alias, msg_id)
        
        if not storage_msg_id:
            return await status_msg.edit(
                "❌ **Map not found!**\n"
                "This message hasn't been synced to the storage vault yet. "
                "Make sure the bot has forwarded it first."
            )

    # --- 4. LOCK TARGET AND WAIT FOR TEXT ---
    EDIT_STATE[message.from_user.id] = {
        "storage_chat_id": storage_chat_id,
        "storage_msg_id": storage_msg_id,
        "main_chat_id": main_chat_id_db,
        "main_msg_id": msg_id
    }

    mode_text = "Main + Storage" if storage_chat_id else "Main Channel Only (Standalone)"
    vault_info = f"**Storage ID:** `{storage_msg_id}`\n" if storage_chat_id else ""

    await status_msg.edit(
        f"✅ **Target Locked! ({mode_text})**\n\n"
        f"**Alias:** `{target_alias}`\n"
        f"**Main ID:** `{msg_id}`\n"
        f"{vault_info}\n"
        f"👇 **Send the new text or caption** you want to replace it with.\n"
        f"*(Or type `/cancel` to abort)*"
    )

# --- 5. HANDLE THE REPLACEMENT TEXT ---
@Client.on_message(filters.private & filters.text & ~filters.command(["msg", "register", "links", "sync", "analyze", "start", "ping", "help"]))
async def process_new_text(client, message):
    user_id = message.from_user.id
    
    # Ignore messages if the user isn't currently editing anything
    if user_id not in EDIT_STATE:
        return 
        
    if message.text.lower() == "/cancel":
        del EDIT_STATE[user_id]
        return await message.reply("🚫 **Edit cancelled.**")
        
    data = EDIT_STATE[user_id]
    status = await message.reply("🔄 **Editing message(s)...**")
    
    try:
        # Edit the main channel message (Try Text first, fallback to Caption if it's media)
        try:
            await client.edit_message_text(
                chat_id=data["main_chat_id"],
                message_id=data["main_msg_id"],
                text=message.text.html # Keeps your bold/italics formatting
            )
        except Exception:
            await client.edit_message_caption(
                chat_id=data["main_chat_id"],
                message_id=data["main_msg_id"],
                caption=message.text.html
            )
        
        # Edit the storage vault message (only if it exists!)
        if data["storage_chat_id"] and data["storage_msg_id"]:
            try:
                await client.edit_message_text(
                    chat_id=data["storage_chat_id"],
                    message_id=data["storage_msg_id"],
                    text=message.text.html
                )
            except Exception:
                await client.edit_message_caption(
                    chat_id=data["storage_chat_id"],
                    message_id=data["storage_msg_id"],
                    caption=message.text.html
                )
            
        await status.edit("✅ **Successfully updated the message!**")
        
    except Exception as e:
        await status.edit(f"❌ **Failed to edit:**\n`{e}`")
        
    # Clear user from the editing state so they can use normal commands again
    del EDIT_STATE[user_id]
