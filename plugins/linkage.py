from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import register_link, get_all_links

# Registers the channels
@Client.on_message(filters.command("register") & filters.private)
async def cmd_register(client, message):
    if len(message.command) != 4:
        return await message.reply(
            "❌ **Incorrect Usage!**\n\n"
            "Format: `/register [Alias] [MainID] [StorageID]`\n"
            "Example: `/register Vefa -10012345678 -10098765432`"
        )
    
    alias = message.command[1]
    main_id = message.command[2]
    storage_id = message.command[3]

    try:
        await register_link(alias, main_id, storage_id)
        await message.reply(f"✅ **Linked Successfully!**\n\n**Alias:** `{alias}`\n**Main:** `{main_id}`\n**Storage:** `{storage_id}`")
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
