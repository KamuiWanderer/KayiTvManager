import os
from motor.motor_asyncio import AsyncIOMotorClient

# MongoDB Setup
MONGODB_URI = os.environ.get("MONGODB_URI")
client = AsyncIOMotorClient(MONGODB_URI)

# Set precisely to the database name seen in your screenshot
db = client["KayiTvManager"] 

links_collection = db["channel_links"]

# --- Pair Management (Matches your linkage.py requirements) ---
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
        await client.admin.command('ping')
        return True
    except Exception:
        return False
