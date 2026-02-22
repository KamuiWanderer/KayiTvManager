from pyrogram import Client, filters
from database import links_collection

@Client.on_callback_query(filters.regex(r"^manage_"))
async def manage_callback(client, query):
    alias = query.data.split("_")[1]
    data = await links_collection.find_one({"alias": alias})
    
    if not data:
        return await query.answer("❌ Link not found.", show_alert=True)

    text = (
        f"⚙️ **Management: {alias}**\n\n"
        f"📍 Main: `{data['main_id']}`\n"
        f"📦 Storage: `{data['storage_id']}`\n\n"
        "Use `/analyze {alias}` or `/sync {alias}` to manage this pair."
    )
    await query.edit_message_text(text)
