import os
import time
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

# Get URI from Render
MONGO_URL = os.environ.get("MONGO_URI")

# Initialize Client
client = AsyncIOMotorClient(MONGO_URL)
db = client["KayiTvManager"] 

# Collections
series_collection = db["series_data"]
links_collection = db["channel_links"]

async def db_ping():
    try:
        start_time = time.time()
        await client.admin.command('ping')
        return round((time.time() - start_time) * 1000, 2) 
    except Exception as e:
        print(f"Database Ping Error: {e}")
        return "Offline"

# --- MODULE 1: NEW ARCHITECTURE ---
async def add_episode_file(alias, season_no, ep_no, quality, file_id, storage_msg_id, main_msg_id=None):
    try:
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
        return True
    except Exception as e:
        print(f"Error in add_episode_file: {e}")
        return False

async def get_series(alias):
    return await series_collection.find_one({"Alias": alias})

# --- LEGACY SUPPORT (To prevent plugin crashes) ---
async def register_link(alias, main_id, storage_id=None):
    data = {"main_id": int(main_id), "storage_id": int(storage_id) if storage_id else None}
    await links_collection.update_one({"alias": alias}, {"$set": data}, upsert=True)

async def get_all_links(): 
    return await links_collection.find({}).to_list(length=100)

async def save_map(alias, main_id, storage_id):
    await db[f"map_{alias}"].update_one({"main_id": int(main_id)}, {"$set": {"storage_id": int(storage_id)}}, upsert=True)

async def get_map(alias, main_id):
    res = await db[f"map_{alias}"].find_one({"main_id": int(main_id)})
    return res["storage_id"] if res else None
