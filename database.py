from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI
import time

# Optimized for cross-region (Singapore to Mumbai)
client = AsyncIOMotorClient(
    MONGO_URI,
    connectTimeoutMS=10000,
    serverSelectionTimeoutMS=10000,
    retryWrites=True,
    retryReads=True
)

db = client["downloaderbot"]
links_collection = db["channel_links"]

async def db_ping():
    start = time.perf_counter()
    await db.command("ping")
    return round((time.perf_counter() - start) * 1000)

async def register_link(alias, main_id, storage_id):
    return await links_collection.update_one(
        {"alias": alias},
        {"$set": {
            "alias": alias,
            "main_id": int(main_id),
            "storage_id": int(storage_id)
        }},
        upsert=True
    )

async def get_all_links():
    return await links_collection.find().to_list(length=None)

# Added for Phase 2: Finding the destination for an incoming message
async def get_link_by_main_id(main_id):
    return await links_collection.find_one({"main_id": int(main_id)})
