# --------------------------------------------------------------------------------
#  ShizuMusic © 2026
#  Developed by Bad Munda ❤️
#
#  Unauthorized copying, editing, re-uploading or removing credits
#  from this source code is strictly prohibited.
# --------------------------------------------------------------------------------

import logging

from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message

import config
from ShizuMusic import bot

logger = logging.getLogger(__name__)


# ── DB Helpers ─────────────────────────────────────────────────────────────────

def _col(name: str):
    try:
        from ShizuMusic.database import get_db
        db = get_db()
        return db[name] if db is not None else None
    except Exception:
        return None


def is_group_blocked(chat_id: int) -> bool:
    col = _col("blocked_groups")
    if col is None:
        return False
    try:
        return col.find_one({"_id": chat_id}) is not None
    except Exception:
        return False


def block_group(chat_id: int) -> None:
    col = _col("blocked_groups")
    if col is None:
        return
    try:
        col.update_one({"_id": chat_id}, {"$set": {"_id": chat_id}}, upsert=True)
    except Exception as e:
        logger.error(f"[DB] block_group: {e}")


def unblock_group(chat_id: int) -> None:
    col = _col("blocked_groups")
    if col is None:
        return
    try:
        col.delete_one({"_id": chat_id})
    except Exception as e:
        logger.error(f"[DB] unblock_group: {e}")


def get_blocked_groups() -> list:
    col = _col("blocked_groups")
    if col is None:
        return []
    try:
        return [doc["_id"] for doc in col.find({}, {"_id": 1})]
    except Exception:
        return []


def is_user_blocked(user_id: int) -> bool:
    col = _col("blocked_users")
    if col is None:
        return False
    try:
        return col.find_one({"_id": user_id}) is not None
    except Exception:
        return False


def block_user(user_id: int) -> None:
    col = _col("blocked_users")
    if col is None:
        return
    try:
        col.update_one({"_id": user_id}, {"$set": {"_id": user_id}}, upsert=True)
    except Exception as e:
        logger.error(f"[DB] block_user: {e}")


def unblock_user(user_id: int) -> None:
    col = _col("blocked_users")
    if col is None:
        return
    try:
        col.delete_one({"_id": user_id})
    except Exception as e:
        logger.error(f"[DB] unblock_user: {e}")


def get_blocked_users() -> list:
    col = _col("blocked_users")
    if col is None:
        return []
    try:
        return [doc["_id"] for doc in col.find({}, {"_id": 1})]
    except Exception:
        return []


# ── Filters ────────────────────────────────────────────────────────────────────

def group_not_blocked(_, __, message: Message) -> bool:
    """Custom filter — blocks all commands in blocked groups."""
    if message.chat and message.chat.id:
        if is_group_blocked(message.chat.id):
            return False
    return True


def user_not_blocked(_, __, message: Message) -> bool:
    """Custom filter — blocks all commands from blocked users."""
    if message.from_user and message.from_user.id:
        if is_user_blocked(message.from_user.id):
            return False
    return True


# Export as pyrogram filters to use in other plugins
group_allowed  = filters.create(group_not_blocked)
user_allowed   = filters.create(user_not_blocked)


# ── /gblock command ────────────────────────────────────────────────────────────

@bot.on_message(
    filters.command("gblock")
    & filters.user(config.OWNER_ID)
)
async def gblock_cmd(_, message: Message) -> None:
    """
    Block a group from using any bot commands.
    Usage:
      /gblock              — block current group
      /gblock -100xxxxxxx  — block by chat ID
    """
    args = message.command[1:]

    if args:
        try:
            chat_id = int(args[0])
        except ValueError:
            await message.reply(
                "<b>❍ Invalid chat ID.</b>\n"
                "<b>❍ Usage: /gblock -100xxxxxxx</b>",
                parse_mode=ParseMode.HTML,
            )
            return
    else:
        if message.chat.type.name in ("PRIVATE",):
            await message.reply(
                "<b>❍ Use this command in a group or provide a chat ID.</b>\n"
                "<b>❍ Usage: /gblock -100xxxxxxx</b>",
                parse_mode=ParseMode.HTML,
            )
            return
        chat_id = message.chat.id

    if is_group_blocked(chat_id):
        await message.reply(
            f"<b>❍ Group <code>{chat_id}</code> is already blocked.</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    block_group(chat_id)
    await message.reply(
        f"<b>❍ Group Blocked ✅</b>\n"
        f"<b>❍ Chat ID :</b> <code>{chat_id}</code>\n"
        f"<b>❍ No commands will work in this group now.</b>",
        parse_mode=ParseMode.HTML,
    )


# ── /gunblock command ──────────────────────────────────────────────────────────

@bot.on_message(
    filters.command("gunblock")
    & filters.user(config.OWNER_ID)
)
async def gunblock_cmd(_, message: Message) -> None:
    """
    Unblock a previously blocked group.
    Usage:
      /gunblock              — unblock current group
      /gunblock -100xxxxxxx  — unblock by chat ID
    """
    args = message.command[1:]

    if args:
        try:
            chat_id = int(args[0])
        except ValueError:
            await message.reply(
                "<b>❍ Invalid chat ID.</b>\n"
                "<b>❍ Usage: /gunblock -100xxxxxxx</b>",
                parse_mode=ParseMode.HTML,
            )
            return
    else:
        if message.chat.type.name in ("PRIVATE",):
            await message.reply(
                "<b>❍ Use this command in a group or provide a chat ID.</b>\n"
                "<b>❍ Usage: /gunblock -100xxxxxxx</b>",
                parse_mode=ParseMode.HTML,
            )
            return
        chat_id = message.chat.id

    if not is_group_blocked(chat_id):
        await message.reply(
            f"<b>❍ Group <code>{chat_id}</code> is not blocked.</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    unblock_group(chat_id)
    await message.reply(
        f"<b>❍ Group Unblocked ✅</b>\n"
        f"<b>❍ Chat ID :</b> <code>{chat_id}</code>\n"
        f"<b>❍ Commands are now enabled in this group.</b>",
        parse_mode=ParseMode.HTML,
    )


# ── /ublock command ────────────────────────────────────────────────────────────

@bot.on_message(
    filters.command("ublock")
    & filters.user(config.OWNER_ID)
)
async def ublock_cmd(_, message: Message) -> None:
    """
    Block a user from using any bot commands.
    Usage:
      /ublock               — reply to a user's message
      /ublock 123456789     — block by user ID
    """
    args = message.command[1:]
    user_id   = None
    user_name = None

    if message.reply_to_message and message.reply_to_message.from_user:
        user_id   = message.reply_to_message.from_user.id
        user_name = message.reply_to_message.from_user.first_name

    elif args:
        try:
            user_id = int(args[0])
        except ValueError:
            await message.reply(
                "<b>❍ Invalid user ID.</b>\n"
                "<b>❍ Usage: /ublock 123456789  or reply to a user.</b>",
                parse_mode=ParseMode.HTML,
            )
            return
    else:
        await message.reply(
            "<b>❍ Reply to a user's message or provide a user ID.</b>\n"
            "<b>❍ Usage: /ublock 123456789</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    # Owner cannot be blocked
    if user_id == config.OWNER_ID:
        await message.reply(
            "<b>❍ You cannot block yourself (owner).</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    if is_user_blocked(user_id):
        await message.reply(
            f"<b>❍ User <code>{user_id}</code> is already blocked.</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    block_user(user_id)
    name_str = f" (<b>{user_name}</b>)" if user_name else ""
    await message.reply(
        f"<b>❍ User Blocked ✅</b>\n"
        f"<b>❍ User ID :</b> <code>{user_id}</code>{name_str}\n"
        f"<b>❍ This user cannot use any bot commands now.</b>",
        parse_mode=ParseMode.HTML,
    )


# ── /uunblock command ──────────────────────────────────────────────────────────

@bot.on_message(
    filters.command("uunblock")
    & filters.user(config.OWNER_ID)
)
async def uunblock_cmd(_, message: Message) -> None:
    """
    Unblock a previously blocked user.
    Usage:
      /uunblock               — reply to a user's message
      /uunblock 123456789     — unblock by user ID
    """
    args = message.command[1:]
    user_id   = None
    user_name = None

    if message.reply_to_message and message.reply_to_message.from_user:
        user_id   = message.reply_to_message.from_user.id
        user_name = message.reply_to_message.from_user.first_name

    elif args:
        try:
            user_id = int(args[0])
        except ValueError:
            await message.reply(
                "<b>❍ Invalid user ID.</b>\n"
                "<b>❍ Usage: /uunblock 123456789  or reply to a user.</b>",
                parse_mode=ParseMode.HTML,
            )
            return
    else:
        await message.reply(
            "<b>❍ Reply to a user's message or provide a user ID.</b>\n"
            "<b>❍ Usage: /uunblock 123456789</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    if not is_user_blocked(user_id):
        await message.reply(
            f"<b>❍ User <code>{user_id}</code> is not blocked.</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    unblock_user(user_id)
    name_str = f" (<b>{user_name}</b>)" if user_name else ""
    await message.reply(
        f"<b>❍ User Unblocked ✅</b>\n"
        f"<b>❍ User ID :</b> <code>{user_id}</code>{name_str}\n"
        f"<b>❍ This user can now use bot commands again.</b>",
        parse_mode=ParseMode.HTML,
    )


# ── /blocklist command ─────────────────────────────────────────────────────────

@bot.on_message(
    filters.command("blocklist")
    & filters.user(config.OWNER_ID)
)
async def blocklist_cmd(_, message: Message) -> None:
    """Show all blocked groups and users."""

    groups = get_blocked_groups()
    users  = get_blocked_users()

    groups_text = (
        "\n".join(f"  • <code>{g}</code>" for g in groups)
        if groups else "  None"
    )
    users_text = (
        "\n".join(f"  • <code>{u}</code>" for u in users)
        if users else "  None"
    )

    text = (
        "<b>❍ Block List</b>\n\n"
        f"<b>❍ Blocked Groups ({len(groups)}):</b>\n{groups_text}\n\n"
        f"<b>❍ Blocked Users ({len(users)}):</b>\n{users_text}"
    )

    await message.reply(text, parse_mode=ParseMode.HTML)
