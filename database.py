import os
import time
from motor.motor_asyncio import AsyncIOMotorClient

# ── Connection ────────────────────────────────────────────────────────────────
MONGO_URL = os.environ.get("MONGO_URI")
client    = AsyncIOMotorClient(MONGO_URL)
db        = client["KayiTvManager"]

# ── Collections ───────────────────────────────────────────────────────────────
series_collection = db["series_data"]
links_collection  = db["channel_links"]

# ── Health Check ──────────────────────────────────────────────────────────────
async def db_ping() -> float:
    """Returns round-trip time to MongoDB in milliseconds, or 'Offline'."""
    try:
        start = time.time()
        await client.admin.command("ping")
        return round((time.time() - start) * 1000, 2)
    except Exception as e:
        print(f"[DB] Ping error: {e}")
        return "Offline"

# ── Module 1: Series / Episode Data ──────────────────────────────────────────
async def add_episode_file(alias, season_no, ep_no, quality, file_id, storage_msg_id, main_msg_id=None):
    """
    Upserts a quality entry for a given episode into the series document.
    Creates the document if it doesn't exist yet.
    """
    try:
        path = f"Seasons.{season_no}.Episodes.{ep_no}.Qualities.{quality}"
        file_data = {
            "file_id":        file_id,
            "storage_msg_id": int(storage_msg_id) if storage_msg_id else None,
            "main_msg_id":    int(main_msg_id)    if main_msg_id    else None,
        }
        await series_collection.update_one(
            {"Alias": alias},
            {"$set": {path: file_data}},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"[DB] add_episode_file error: {e}")
        return False

async def get_series(alias: str):
    """Returns the full series document for a given alias."""
    return await series_collection.find_one({"Alias": alias})

async def get_all_series():
    """Returns a list of all series documents."""
    return await series_collection.find({}).to_list(length=500)

# ── Legacy: Channel Link Registry ────────────────────────────────────────────
async def register_link(alias: str, main_id, storage_id=None):
    """Registers or updates a main↔storage channel pair under an alias."""
    data = {
        "alias":      alias,
        "main_id":    int(main_id),
        "storage_id": int(storage_id) if storage_id else None,
    }
    await links_collection.update_one({"alias": alias}, {"$set": data}, upsert=True)

async def get_all_links():
    """Returns all registered channel link documents."""
    return await links_collection.find({}).to_list(length=100)

async def get_link(alias: str):
    """Returns the link document for a specific alias."""
    return await links_collection.find_one({"alias": alias})

# ── Sync Map ──────────────────────────────────────────────────────────────────
async def save_map(alias: str, main_msg_id: int, storage_msg_id: int):
    """Saves a main_msg_id ↔ storage_msg_id mapping for an alias."""
    await db[f"map_{alias}"].update_one(
        {"main_id": int(main_msg_id)},
        {"$set": {"storage_id": int(storage_msg_id)}},
        upsert=True
    )

async def get_map(alias: str, main_msg_id: int):
    """Returns the storage_msg_id for a given main_msg_id, or None."""
    res = await db[f"map_{alias}"].find_one({"main_id": int(main_msg_id)})
    return res["storage_id"] if res else None
