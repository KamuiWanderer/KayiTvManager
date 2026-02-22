import os
import time
from motor.motor_asyncio import AsyncIOMotorClient

# MongoDB Setup - Updated to match your Render dashboard!
MONGO_URL = os.environ.get("MONGO_URI")

# 🚨 SAFETY TRIPWIRE: Prevents the bot from silently using localhost
if not MONGO_URL:
    raise ValueError("❌ CRITICAL ERROR: MONGO_URI is missing from Render Environment Variables!")

client = AsyncIOMotorClient(MONGO_URL)

# Set precisely to the database name seen in your screenshot
db = client["KayiTvManager"] 
links_collection = db["channel_links"]

# --- Pair Management ---
async def register_link(alias, main_id, storage_id):
    await links_collection.update_one(
        {"alias": alias},
        {"$set": {"main_id": int(main_id), "storage_id": int(storage_id)}},
        upsert=True
    )

async def get_all_links():
    return await links_collection.find({}).to_list(length=100)

async def get_link_by_main_id(main_id):
    return await links_collection.find_one({"main_id": int(main_id)})

# --- Message Mapping for Editor & Sync ---
async def save_map(alias, main_id, storage_id):
    await db[f"map_{alias}"].update_one(
        {"main_id": int(main_id)},
        {"$set": {"storage_id": int(storage_id)}},
        upsert=True
    )

async def get_map(alias, main_id):
    data = await db[f"map_{alias}"].find_one({"main_id": int(main_id)})
    return data["storage_id"] if data else None

# --- Database Health Check ---
async def db_ping():
    try:
        start_time = time.time()
        await client.admin.command('ping')
        end_time = time.time()
        # Returns the latency in milliseconds
        return round((end_time - start_time) * 1000, 2) 
    except Exception as e:
        print(f"MongoDB Ping Failed: {e}")
        return "Offline"
