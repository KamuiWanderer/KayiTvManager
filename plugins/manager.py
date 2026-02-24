import os
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.errors import (
    FloodWait, PeerIdInvalid, ChatAdminRequired,
    MessageIdInvalid, MessageNotModified, RPCError
)
from database import get_all_links, save_map, get_map
from config import is_admin

USER_SESSION = os.environ.get("USER_SESSION")

# ── Error translator ──────────────────────────────────────────────────────────
def translate_error(e: Exception) -> str:
    if isinstance(e, FloodWait):            return f"Rate Limited ({e.value}s pause)"
    elif isinstance(e, PeerIdInvalid):      return "Unknown Chat (Check Admin rights/ID)"
    elif isinstance(e, ChatAdminRequired):  return "Missing Permissions (Not an Admin)"
    elif isinstance(e, MessageIdInvalid):   return "Message Not Found (Deleted or invalid)"
    elif isinstance(e, MessageNotModified): return "Unchanged text"
    elif isinstance(e, RPCError):           return f"API Error: {e.MESSAGE}"
    else:                                   return f"System Error: {type(e).__name__}"


# ── Safe status edit (swallows MessageNotModified) ────────────────────────────
async def _edit(msg, text: str):
    try:
        await msg.edit(text)
    except MessageNotModified:
        pass


# ── Start userbot + fix PeerIdInvalid amnesia ─────────────────────────────────
async def _start_userbot(status_msg, main_id: int):
    if not USER_SESSION:
        raise RuntimeError("`USER_SESSION` is missing from Render Environment Variables!")

    user_app = Client("userbot_in_memory", session_string=USER_SESSION, in_memory=True)
    await user_app.start()

    try:
        await user_app.get_chat(main_id)
    except (PeerIdInvalid, ValueError, KeyError):
        await _edit(status_msg, "🔄 **Syncing userbot memory...** (resolving channel access)")
        async for _ in user_app.get_dialogs(limit=200):
            pass

    return user_app


# ── Verify a message actually exists in a channel (bot account check) ─────────
async def _message_exists(client, chat_id: int, msg_id: int) -> bool:
    """
    Returns True if the message physically exists in the channel.
    Uses get_messages() — if the result is empty or a stub, it's gone.
    """
    try:
        msgs = await client.get_messages(chat_id, msg_id)
        # Pyrogram returns an empty Message object (msg.empty = True) if not found
        if msgs is None:
            return False
        if isinstance(msgs, list):
            return len(msgs) > 0 and not msgs[0].empty
        return not msgs.empty
    except (MessageIdInvalid, RPCError):
        return False
    except Exception:
        return False


# =============================================================================
# AUTO-MIRROR — fires on every new message posted to a registered main channel
#
# REQUIREMENT: The bot must be an ADMIN of the Main Channel with Post Messages
# permission. Without that, Telegram never delivers channel updates to the bot.
# =============================================================================
@Client.on_message(filters.channel)
async def auto_mirror(client, message):
    if not message.chat or not message.chat.id:
        return

    links = await get_all_links()
    link_data = None
    for l in links:
        try:
            if int(l["main_id"]) == int(message.chat.id):
                link_data = l
                break
        except (ValueError, TypeError):
            continue

    if not link_data or not link_data.get("storage_id"):
        return

    alias      = link_data["alias"]
    storage_id = int(link_data["storage_id"])
    main_id    = int(link_data["main_id"])

    print(f"📨 [MIRROR] New msg in '{alias}' (id={message.id}) → copying to storage...")

    async def _do_copy():
        return await client.copy_message(
            chat_id=storage_id,
            from_chat_id=main_id,
            message_id=message.id
        )

    try:
        copied = await _do_copy()
        await save_map(alias, message.id, copied.id)
        print(f"✅ [MIRROR] '{alias}' msg {message.id} → storage {copied.id}")

    except FloodWait as e:
        print(f"⏳ [MIRROR] FloodWait {e.value}s — retrying...")
        await asyncio.sleep(e.value + 1)
        try:
            copied = await _do_copy()
            await save_map(alias, message.id, copied.id)
            print(f"✅ [MIRROR] Retry success → storage {copied.id}")
        except Exception as ex:
            print(f"❌ [MIRROR] Retry failed for '{alias}': {translate_error(ex)}")

    except Exception as e:
        print(f"❌ [MIRROR] Failed for '{alias}': {translate_error(e)}")


# =============================================================================
# /sync [Alias]
#
# Full three-way verification + recovery, in sequence.
#
# For every message in the main channel history, checks ALL THREE conditions:
#   1. Is it in the main channel?           (userbot scan)
#   2. Is it recorded in the DB map?        (get_map)
#   3. Does that storage msg ACTUALLY EXIST in the storage channel? (get_messages)
#
# A message is only considered "synced" if all three are true.
# If DB says synced but the storage message is gone → treated as missing.
# Copies everything missing in oldest→newest order to guarantee sequence.
# After completion, auto_mirror handles all future messages.
# =============================================================================
@Client.on_message(filters.command("sync") & filters.private, group=1)
async def sync_cmd(client, message):
    if not is_admin(message.from_user.id):
        return await message.reply("🚫 **Access Denied.**")

    if len(message.command) != 2:
        return await message.reply(
            "❌ **Usage:** `/sync [Alias]`\n\n"
            "Scans the full main channel history, verifies every message is "
            "actually present in the storage vault (not just recorded in DB), "
            "and copies anything missing — oldest to newest."
        )

    alias = message.command[1]
    links = await get_all_links()
    link_data = next((l for l in links if l["alias"] == alias), None)

    if not link_data:
        return await message.reply(f"❌ Alias `{alias}` not found. Use `/links` to see registered channels.")
    if not link_data.get("storage_id"):
        return await message.reply(f"❌ `{alias}` has no storage vault attached.")

    main_id    = int(link_data["main_id"])
    storage_id = int(link_data["storage_id"])

    status = await message.reply(
        f"🚀 **Starting Full Sync — `{alias}`**\n\n"
        f"🔍 Phase 1: Scanning main channel history...\n"
        f"_(Three-way check: main channel → DB map → storage channel)_"
    )

    # ── PHASE 1: Scan with userbot ────────────────────────────────────────────
    try:
        user_app = await _start_userbot(status, main_id)
    except RuntimeError as e:
        return await status.edit(f"❌ **Setup Error:** {e}")

    # Categorise every message we find:
    missing_ids    = []  # not in DB at all
    ghost_ids      = []  # in DB but storage message doesn't actually exist
    messages_checked = 0
    last_ui_update = time.time()

    try:
        async for msg in user_app.get_chat_history(main_id):
            if msg.empty or msg.service:
                continue

            messages_checked += 1
            main_msg_id = msg.id

            # Check 1: is it in the DB map?
            storage_msg_id = await get_map(alias, main_msg_id)

            if not storage_msg_id:
                # Not in DB at all — definitely missing
                missing_ids.append(main_msg_id)
            else:
                # Check 2: does the storage message physically exist?
                exists = await _message_exists(client, storage_id, storage_msg_id)
                if not exists:
                    # DB says it's there but it's not — ghost entry
                    ghost_ids.append(main_msg_id)

            # Anti-flood pause every 50 messages
            if messages_checked % 50 == 0:
                delay = min(5 + ((messages_checked // 100) * 2), 30)
                await _edit(status,
                    f"🛡 **Phase 1: Scanning `{alias}`** _(anti-flood pause)_\n\n"
                    f"📊 **Checked:** `{messages_checked}` messages\n"
                    f"❓ **Not in DB:** `{len(missing_ids)}`\n"
                    f"👻 **In DB but gone from storage:** `{len(ghost_ids)}`\n"
                    f"⏱ **Resuming in:** `{delay}s`"
                )
                await asyncio.sleep(delay)
                last_ui_update = time.time()

            elif time.time() - last_ui_update >= 7:
                await _edit(status,
                    f"🔍 **Phase 1: Scanning `{alias}`**\n\n"
                    f"📊 **Checked:** `{messages_checked}` messages\n"
                    f"❓ **Not in DB:** `{len(missing_ids)}`\n"
                    f"👻 **In DB but gone from storage:** `{len(ghost_ids)}`"
                )
                last_ui_update = time.time()

    except Exception as e:
        await user_app.stop()
        return await status.edit(f"⚠️ **Scan interrupted:** `{e}`")

    await user_app.stop()

    # ── PHASE 2: Copy everything that needs fixing ────────────────────────────
    # Combine both lists — missing entirely + ghost entries both need a fresh copy
    to_copy = sorted(set(missing_ids + ghost_ids))  # oldest → newest

    if not to_copy:
        return await status.edit(
            f"✅ **`{alias}` is perfectly synced!**\n\n"
            f"📊 Scanned `{messages_checked}` messages.\n"
            f"Every message is recorded in DB **and** physically present in the vault.\n\n"
            f"🟢 Live mirroring is active for new messages."
        )

    total  = len(to_copy)
    synced = 0
    failed = 0
    error_log = {}
    last_ui_update = time.time()

    await _edit(status,
        f"📦 **Phase 2: Copying `{total}` messages to vault...**\n\n"
        f"❓ Not in DB: `{len(missing_ids)}`\n"
        f"👻 In DB but missing from storage: `{len(ghost_ids)}`\n\n"
        f"⏳ Progress: `0 / {total}`"
    )

    for msg_id in to_copy:
        try:
            copied = await client.copy_message(
                chat_id=storage_id,
                from_chat_id=main_id,
                message_id=msg_id
            )
            await save_map(alias, msg_id, copied.id)
            synced += 1

        except FloodWait as e:
            await asyncio.sleep(e.value + 2)
            try:
                copied = await client.copy_message(
                    chat_id=storage_id,
                    from_chat_id=main_id,
                    message_id=msg_id
                )
                await save_map(alias, msg_id, copied.id)
                synced += 1
            except Exception as ex:
                failed += 1
                error_log[msg_id] = translate_error(ex)

        except Exception as e:
            failed += 1
            error_log[msg_id] = translate_error(e)

        if time.time() - last_ui_update >= 7:
            await _edit(status,
                f"📦 **Phase 2: Copying to vault...**\n\n"
                f"✅ **Copied:** `{synced}`\n"
                f"❌ **Failed:** `{failed}`\n"
                f"📊 **Progress:** `{synced + failed} / {total}`"
            )
            last_ui_update = time.time()

    # ── Final report ──────────────────────────────────────────────────────────
    await status.edit(
        f"✅ **Sync Complete — `{alias}`**\n\n"
        f"🔍 **Scanned:** `{messages_checked}` messages\n"
        f"❓ **Were missing from DB:** `{len(missing_ids)}`\n"
        f"👻 **Were ghost entries (DB yes, storage no):** `{len(ghost_ids)}`\n"
        f"✅ **Successfully copied:** `{synced}`\n"
        f"❌ **Failed:** `{failed}`\n\n"
        f"{'⚠️ See error log below.' if failed else '🟢 All messages are now fully synced. Live mirroring is active.'}"
    )

    if failed:
        err_text = f"⚠️ **Error Log — `{alias}`**\n\n"
        for mid, reason in error_log.items():
            err_text += f"• **msg {mid}:** `{reason}`\n"
        if len(err_text) > 4000:
            err_text = err_text[:4000] + "\n\n_(truncated)_"
        await message.reply(err_text)


# =============================================================================
# /audit [Alias]
#
# Scan-only. Same three-way check as /sync but copies nothing.
# Shows you exactly what's missing and why before you commit to a /sync.
# =============================================================================
@Client.on_message(filters.command("audit") & filters.private, group=1)
async def audit_cmd(client, message):
    if not is_admin(message.from_user.id):
        return await message.reply("🚫 **Access Denied.**")

    if len(message.command) != 2:
        return await message.reply(
            "❌ **Usage:** `/audit [Alias]`\n\n"
            "Three-way scan: checks main channel → DB map → storage channel.\n"
            "Reports gaps without copying anything."
        )

    alias = message.command[1]
    links = await get_all_links()
    link_data = next((l for l in links if l["alias"] == alias), None)

    if not link_data:
        return await message.reply(f"❌ Alias `{alias}` not found.")
    if not link_data.get("storage_id"):
        return await message.reply(f"❌ `{alias}` has no storage vault attached.")

    main_id    = int(link_data["main_id"])
    storage_id = int(link_data["storage_id"])

    status = await message.reply(
        f"🔎 **Auditing `{alias}`...**\n"
        f"_(Three-way check — nothing will be copied)_"
    )

    try:
        user_app = await _start_userbot(status, main_id)
    except RuntimeError as e:
        return await status.edit(f"❌ **Setup Error:** {e}")

    missing_ids      = []
    ghost_ids        = []
    messages_checked = 0
    last_ui_update   = time.time()

    try:
        async for msg in user_app.get_chat_history(main_id):
            if msg.empty or msg.service:
                continue

            messages_checked += 1
            storage_msg_id = await get_map(alias, msg.id)

            if not storage_msg_id:
                missing_ids.append(msg.id)
            else:
                exists = await _message_exists(client, storage_id, storage_msg_id)
                if not exists:
                    ghost_ids.append(msg.id)

            if messages_checked % 50 == 0:
                delay = min(5 + ((messages_checked // 100) * 2), 30)
                await _edit(status,
                    f"🛡 **Auditing `{alias}`** _(anti-flood pause)_\n\n"
                    f"📊 **Checked:** `{messages_checked}`\n"
                    f"❓ **Not in DB:** `{len(missing_ids)}`\n"
                    f"👻 **Ghost entries:** `{len(ghost_ids)}`\n"
                    f"⏱ **Resuming in:** `{delay}s`"
                )
                await asyncio.sleep(delay)
                last_ui_update = time.time()

            elif time.time() - last_ui_update >= 7:
                await _edit(status,
                    f"🔎 **Auditing `{alias}`**\n\n"
                    f"📊 **Checked:** `{messages_checked}`\n"
                    f"❓ **Not in DB:** `{len(missing_ids)}`\n"
                    f"👻 **Ghost entries:** `{len(ghost_ids)}`"
                )
                last_ui_update = time.time()

    except Exception as e:
        await user_app.stop()
        return await status.edit(f"⚠️ **Audit interrupted:** `{e}`")

    await user_app.stop()

    total_issues = len(missing_ids) + len(ghost_ids)

    if total_issues == 0:
        return await status.edit(
            f"✅ **Audit Complete — `{alias}` is perfectly synced!**\n\n"
            f"📊 Scanned `{messages_checked}` messages.\n"
            f"Every message is in DB **and** physically present in the storage vault."
        )

    # Build a compact preview (max 15 entries per category)
    def _preview(id_list, label):
        if not id_list:
            return ""
        lines = "\n".join([f"  • `msg {mid}`" for mid in id_list[:15]])
        more  = f"\n  _(+ {len(id_list) - 15} more)_" if len(id_list) > 15 else ""
        return f"\n**{label}:** `{len(id_list)}`\n{lines}{more}\n"

    report  = f"⚠️ **Audit Complete — `{alias}` has `{total_issues}` issue(s)**\n\n"
    report += f"📊 **Scanned:** `{messages_checked}` messages\n"
    report += _preview(missing_ids, "❓ Not in DB (never recorded)")
    report += _preview(ghost_ids,   "👻 In DB but gone from storage vault")
    report += f"\nRun `/sync {alias}` to fix all issues."

    await status.edit(report)
