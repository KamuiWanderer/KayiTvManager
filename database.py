import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URI = os.environ.get("MONGODB_URI")
client = AsyncIOMotorClient(MONGODB_URI)
db = client["KayiTvBot"]
links_collection = db["channel_links"]

async def add_link(alias, main_id, storage_id):
    await links_collection.update_one(
        {"alias": alias},
        {"$set": {"main_id": int(main_id), "storage_id": int(storage_id)}},
        upsert=True
    )

async def get_link_by_main_id(main_id):
    return await links_collection.find_one({"main_id": int(main_id)})

# Crucial for the Editor to find where to sync the edit
async def get_map(alias, main_id):
    data = await db[f"map_{alias}"].find_one({"main_id": int(main_id)})
    return data["storage_id"] if data else None

async def save_map(alias, main_id, storage_id):
    await db[f"map_{alias}"].update_one(
        {"main_id": int(main_id)},
        {"$set": {"storage_id": int(storage_id)}},
        upsert=True
    )
