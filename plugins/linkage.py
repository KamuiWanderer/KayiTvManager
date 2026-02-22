from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import register_link, get_all_links

@Client.on_message(filters.command("register") & filters.private)
async def handle_registration(client, message):
    args = message.command
    if len(args) != 4:
        return await message.reply("❌ **Usage:** `/register Alias MainID StorageID`\nEx: `/register Marvel -100123 -100456` ")
    
    name, m_id, s_id = args[1], args[2], args[3]
    await register_link(name, m_id, s_id)
    await message.reply(f"✅ **Registered:** `{name}`\n🔗 **Main:** `{m_id}`\n📦 **Storage:** `{s_id}`")

@Client.on_message(filters.command("links") & filters.private)
async def view_links(client, message):
    all_links = await get_all_links()
    if not all_links:
        return await message.reply("📭 No channels linked yet.")

    text = "📋 **Managed Channel Pairs**\n\n"
    buttons = []
    
    for item in all_links:
        text += f"🔹 **{item['alias']}**\n┗ Main: `{item['main_id']}`\n"
        # Adding a button for each alias for future management
        buttons.append([InlineKeyboardButton(f"⚙️ Manage {item['alias']}", callback_data=f"manage_{item['alias']}")])

    await message.reply(text, reply_markup=InlineKeyboardMarkup(buttons))
