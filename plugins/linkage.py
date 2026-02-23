from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import register_link, get_all_links

# Registers the channels
@Client.on_message(filters.command("register") & filters.private)
async def cmd_register(client, message):
    if len(message.command) not in [3, 4]:
        return await message.reply(
            "❌ **Incorrect Usage!**\n\n"
            "**With Vault:** `/register [Alias] [MainID] [StorageID]`\n"
            "**Standalone (No Vault):** `/register [Alias] [MainID]`"
        )
    
    alias = message.command[1]
    main_id = message.command[2]
    # If they only provided 3 words, set storage to None
    storage_id = message.command[3] if len(message.command) == 4 else None

    try:
        await register_link(alias, main_id, storage_id)
        vault_text = f"`{storage_id}`" if storage_id else "None (Standalone)"
        await message.reply(f"✅ **Linked Successfully!**\n\n**Alias:** `{alias}`\n**Main:** `{main_id}`\n**Storage:** {vault_text}")
    except Exception as e:
        await message.reply(f"❌ Database Error: {e}")


# Views the channels
@Client.on_message(filters.command("links") & filters.private)
async def cmd_links(client, message):
    links = await get_all_links()
    
    if not links:
        return await message.reply("📭 No channels are currently linked.")
    
    buttons = []
    for link in links:
        # This matches the callback.py we made earlier!
        buttons.append([InlineKeyboardButton(f"⚙️ {link['alias']}", callback_data=f"manage_{link['alias']}")])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    await message.reply("📋 **Your Linked Channels:**\nSelect an alias to manage it:", reply_markup=reply_markup)
