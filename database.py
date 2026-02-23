import os
import time
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get("MONGO_URI")

if not MONGO_URL:
    raise ValueError("❌ CRITICAL ERROR: MONGO_URI is missing from Render Environment Variables!")

client = AsyncIOMotorClient(MONGO_URL)
db = client["KayiTvManager"] 

# V3.0 Collections
series_collection = db["series_data"]
links_collection = db["channel_links"]

# ==========================================
# MODULE 1: THE V3.0 DOCUMENT ARCHITECTURE 
# ==========================================

async def create_or_update_series(alias, series_name, main_id, storage_id):
    """Initializes a new series in the database."""
    default_template = "<blockquote><b> {series_name} | Season {season_no} </b></blockquote>\n<b>Episode {ep_no} 👇</b>"
    
    doc = {
        "Alias": alias,
        "Series_Name": series_name,
        "Main_Channel_ID": int(main_id),
        "Storage_Channel_ID": int(storage_id) if storage_id else None,
    }
    
    await series_collection.update_one(
        {"Alias": alias},
        {
            "$set": doc, 
            "$setOnInsert": {"Post_Template": default_template, "Seasons": {}}
        },
        upsert=True
    )

async def update_post_template(alias, template_html):
    await series_collection.update_one(
        {"Alias": alias},
        {"$set": {"Post_Template": template_html}}
    )

async def add_episode_file(alias, season_no, ep_no, quality, file_id, storage_msg_id, main_msg_id=None):
    path = f"Seasons.{season_no}.Episodes.{ep_no}.Qualities.{quality}"
    file_data = {
        "file_id": file_id,
        "storage_msg_id": int(storage_msg_id) if storage_msg_id else None,
        "main_msg_id": int(main_msg_id) if main_msg_id else None
    }
    
    await series_collection.update_one(
        {"Alias": alias},
        {"$set": {path: file_data}},
        upsert=True
    )

async def get_series(alias):
    return await series_collection.find_one({"Alias": alias})

async def get_all_series():
    return await series_collection.find({}, {"Alias": 1, "Series_Name": 1}).to_list(length=100)

# ==========================================
# LEGACY HELPER FUNCTIONS (Kept intact to prevent crashes)
# ==========================================

async def db_ping():
    try:
        start_time = time.time()
        await client.admin.command('ping')
        return round((time.time() - start_time) * 1000, 2) 
    except Exception as e:
        print(f"MongoDB Ping Failed: {e}")
        return "Offline"

async def register_link(alias, main_id, storage_id=None):
    update_data = {"main_id": int(main_id), "storage_id": int(storage_id) if storage_id else None}
    await links_collection.update_one({"alias": alias}, {"$set": update_data}, upsert=True)

async def get_all_links(): return await links_collection.find({}).to_list(length=100)
async def get_link_by_main_id(main_id): return await links_collection.find_one({"main_id": int(main_id)})

# Legacy Mapping for manager.py and editor.py
async def save_map(alias, main_id, storage_id):
    await db[f"map_{alias}"].update_one(
        {"main_id": int(main_id)},
        {"$set": {"storage_id": int(storage_id)}},
        upsert=True
    )

async def get_map(alias, main_id):
    data = await db[f"map_{alias}"].find_one({"main_id": int(main_id)})
    return data["storage_id"] if data else None
