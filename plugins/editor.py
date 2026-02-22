from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_map, links_collection

@Client.on_message(filters.command("msg") & filters.private)
async def editor_init(client, message):
    if len(message.command) < 2: return await message.reply("Usage: `/msg [Link]`")
    
    # Simple link parser
    link = message.command[1]
    msg_id = int(link.split('/')[-1])
    
    buttons = [
        [InlineKeyboardButton("📝 Text", callback_data=f"edit_t|{msg_id}"),
         InlineKeyboardButton("🖼️ Media", callback_data=f"edit_m|{msg_id}")],
        [InlineKeyboardButton("🎨 Button Style", callback_data=f"style|{msg_id}")]
    ]
    await message.reply("🛠️ **Editor Mode**\nSelect an action for this message:", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_message(filters.command("help") & filters.private)
async def help_cmd(client, message):
    await message.reply(
        "📖 **Obito Guide**\n\n"
        "• `/register [Alias] [MainID] [StorageID]`\n"
        "• `/analyze [Alias]` - Check patterns\n"
        "• `/sync [Alias]` - Mirror history in order\n"
        "• `/msg [Link]` - Edit post visually"
    )
