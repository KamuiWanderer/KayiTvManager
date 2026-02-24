import os

# ── Telegram API Credentials ──────────────────────────────────────────────────
# Set these in your Render Environment Variables panel, never hardcode them.
API_ID   = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# ── MongoDB ───────────────────────────────────────────────────────────────────
MONGO_URI = os.environ.get("MONGO_URI", "")

# ── Userbot (for /resync scanning) ───────────────────────────────────────────
USER_SESSION = os.environ.get("USER_SESSION", "")

# ── Access Control ────────────────────────────────────────────────────────────
# SUDO_USERS  : Full access — can register/delete channels, run /restore, etc.
# ADMINS: Operational access — upload, post, resync, view. Cannot touch channel registration or run destructive recovery commands.

SUDO_USERS = [
    986380678,  # Owner
]

ADMINS = []

def is_sudo(user_id: int) -> bool:
    return user_id in SUDO_USERS

def is_admin(user_id: int) -> bool:
    """Returns True for both admins AND sudo users."""
    return user_id in SUDO_USERS or user_id in ADMINS
