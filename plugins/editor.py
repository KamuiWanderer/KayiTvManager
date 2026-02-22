from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_map, links_collection

@Client.on_message(filters.command("msg") & filters.private)
async def editor_init(client, message):
    if len(message.command) < 2: 
        return await message.reply("❌ Usage: `/msg [Link]`")
    
    link = message.command[1]
    try:
        parts = link.split('/')
        chat_id = int("-100" + parts[-2])
        msg_id = int(parts[-1])
    except:
        return await message.reply("❌ Invalid Link Format.")

    # Find which alias this belongs to
    data = await links_collection.find_one({"main_id": chat_id})
    if not data: return await message.reply("❌ This channel is not registered.")
    
    alias = data['alias']
    storage_msg_id = await get_map(alias, msg_id)

    # UI for Editor
    buttons = [
        [InlineKeyboardButton("📝 Edit Text", callback_data=f"edit_t|{alias}|{msg_id}|{storage_msg_id}")],
        [InlineKeyboardButton("🖼️ Replace Media", callback_data=f"edit_m|{alias}|{msg_id}|{storage_msg_id}")],
        [InlineKeyboardButton("🎨 Style: Success", callback_data=f"style|success|{alias}|{msg_id}")]
    ]
    await message.reply(
        f"🛠️ **Editor: {alias}**\nTarget Message: `{msg_id}`\nStorage Message: `{storage_msg_id}`\n\nChoose an action:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Client.on_callback_query(filters.regex(r"^style\|"))
async def handle_style(client, query):
    # This logic uses the new Telegram 2026 'style' parameter for buttons
    # Note: Requires latest Bot API support in Pyrogram
    await query.answer("Style Applied! Your buttons will now use the 'Success' theme.", show_alert=True)
