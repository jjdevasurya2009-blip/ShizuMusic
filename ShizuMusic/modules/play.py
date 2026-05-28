# --------------------------------------------------------------------------------
#  ShizuMusic © 2026
#  Developed by Bad Munda ❤️
# --------------------------------------------------------------------------------

import asyncio
import re
import time

from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.errors import RPCError, UserAlreadyParticipant
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import config

from ShizuMusic import bot
from ShizuMusic.core.player import play_song
from ShizuMusic.core.queue import (
    add_to_queue,
    queue_size,
)

from ShizuMusic.utils.formatters import (
    fmt_time,
    iso_to_human,
    iso_to_sec,
    short,
)

from ShizuMusic.utils.youtube import search_yt


# ─────────────────────────────────────────────
# BLOCKED WORDS
# ─────────────────────────────────────────────

BLOCKED_WORDS = [
    "porn",
    "xxx",
    "xnxx",
    "xvideos",
    "sex",
    "fuck",
    "lund",
    "drug",
    "cocaine",
    "weed",
    "charas",
]


# ─────────────────────────────────────────────
# STATE
# ─────────────────────────────────────────────

_last_cmd: dict[int, float] = {}
_pending: dict[int, tuple] = {}


# ─────────────────────────────────────────────
# DB TRACK
# ─────────────────────────────────────────────

def _db_track(chat_id: int, user_id: int):

    try:

        from ShizuMusic.database import (
            add_served_chat,
            add_served_user,
        )

        add_served_chat(chat_id)

        if user_id:
            add_served_user(user_id)

    except Exception:
        pass


# ─────────────────────────────────────────────
# ASSISTANT CHECK
# ─────────────────────────────────────────────

async def _is_assistant_in(
    chat_id: int,
    assistant_username: str,
):

    from ShizuMusic import assistant

    try:

        member = await assistant.get_chat_member(
            chat_id,
            assistant_username,
        )

        return member.status is not None

    except Exception as e:

        err = str(e).lower()

        if "banned" in err:
            return "banned"

        return False


# ─────────────────────────────────────────────
# AUTO JOIN ASSISTANT
# ─────────────────────────────────────────────

async def _try_join_assistant(
    chat_id: int,
    pm: Message,
) -> bool:

    from ShizuMusic import assistant

    try:

        chat = await bot.get_chat(chat_id)

        if chat.username:

            link = f"https://t.me/{chat.username}"

        else:

            try:
                link = await bot.export_chat_invite_link(chat_id)

            except Exception:
                link = None

    except Exception:
        link = None

    if not link:

        await pm.edit_text(
            "<b>❍ ᴀᴅᴅ ᴀssɪsᴛᴀɴᴛ ᴍᴀɴᴜᴀʟʟʏ</b>",
            parse_mode=ParseMode.HTML,
        )

        return False

    try:

        if "https://t.me/+" in link:

            link = link.replace(
                "https://t.me/+",
                "https://t.me/joinchat/",
            )

        await assistant.join_chat(link)

        await asyncio.sleep(2)

        return True

    except UserAlreadyParticipant:
        return True

    except RPCError as e:

        await pm.edit_text(
            f"<b>❍ ᴀssɪsᴛᴀɴᴛ ᴊᴏɪɴ ғᴀɪʟᴇᴅ</b>\n"
            f"<code>{e.MESSAGE}</code>",
            parse_mode=ParseMode.HTML,
        )

        return False

    except Exception as e:

        await pm.edit_text(
            f"<b>❍ ᴊᴏɪɴ ᴇʀʀᴏʀ</b>\n"
            f"<code>{e}</code>",
            parse_mode=ParseMode.HTML,
        )

        return False


# ─────────────────────────────────────────────
# COOLDOWN
# ─────────────────────────────────────────────

async def _run_pending(
    chat_id: int,
    delay: int,
):

    await asyncio.sleep(delay)

    if chat_id in _pending:

        msg, reply = _pending.pop(chat_id)

        try:
            await reply.delete()
        except Exception:
            pass

        await play_handler(bot, msg)


# ─────────────────────────────────────────────
# PLAY COMMAND
# ─────────────────────────────────────────────

@bot.on_message(
    filters.group
    & filters.regex(
        r"^/(?P<cmd>v?play)(?:@\w+)?(?:\s+(?P<q>.+))?$"
    )
)

async def play_handler(_, message: Message):

    chat_id = message.chat.id

    user_id = (
        message.from_user.id
        if message.from_user
        else 0
    )

    _db_track(chat_id, user_id)

    # ─────────────────────────
    # REPLY AUDIO / VIDEO
    # ─────────────────────────

    if (
        message.reply_to_message
        and (
            message.reply_to_message.audio
            or message.reply_to_message.video
        )
    ):

        pm = await message.reply(
            "<b>❍ ᴘʀᴏᴄᴇssɪɴɢ...</b>",
            parse_mode=ParseMode.HTML,
        )

        orig = message.reply_to_message

        fresh = await bot.get_messages(
            orig.chat.id,
            orig.id,
        )

        media = fresh.video or fresh.audio

        try:

            fp = await bot.download_media(media)

        except Exception as e:

            await pm.edit_text(
                f"<b>❍ ᴅᴏᴡɴʟᴏᴀᴅ ғᴀɪʟᴇᴅ</b>\n"
                f"<code>{e}</code>",
                parse_mode=ParseMode.HTML,
            )

            return

        song = {
            "url": fp,
            "title": getattr(
                media,
                "file_name",
                "Audio",
            ),
            "duration": fmt_time(
                media.duration or 0
            ),
            "duration_seconds": (
                media.duration or 0
            ),
            "requester": (
                message.from_user.first_name
                if message.from_user
                else "Unknown"
            ),
            "requester_id": user_id,
            "thumbnail": None,
        }

        pos = add_to_queue(chat_id, song)

        if pos == 1:

            ok = await play_song(
                chat_id,
                pm,
                song,
            )

            if not ok:
                return

        else:

            await pm.edit_text(
                f"<b>❍ ǫᴜᴇᴜᴇᴅ :</b> "
                f"<code>#{pos - 1}</code>",
                parse_mode=ParseMode.HTML,
            )

        return

    # ─────────────────────────
    # QUERY
    # ─────────────────────────

    match = message.matches[0]

    query = (
        match.group("q") or ""
    ).strip()

    cmd = (
        match.group("cmd") or "play"
    ).strip()

    try:
        await message.delete()
    except Exception:
        pass

    if not query:

        await bot.send_message(
            chat_id,
            "<b>❍ ᴜsᴀɢᴇ :</b>\n"
            "<code>/play song name</code>",
            parse_mode=ParseMode.HTML,
        )

        return

    # ─────────────────────────
    # BLOCK WORDS
    # ─────────────────────────

    q = query.lower()

    if any(x in q for x in BLOCKED_WORDS):

        await bot.send_message(
            chat_id,
            "<b>❍ ᴛʜɪs sᴏɴɢ ɪs ʙʟᴏᴄᴋᴇᴅ</b>",
            parse_mode=ParseMode.HTML,
        )

        return

    # ─────────────────────────
    # COOLDOWN
    # ─────────────────────────

    now = time.time()

    if (
        chat_id in _last_cmd
        and (
            now - _last_cmd[chat_id]
        ) < config.COOLDOWN
    ):

        rem = int(
            config.COOLDOWN
            - (
                now
                - _last_cmd[chat_id]
            )
        )

        if chat_id not in _pending:

            rep = await bot.send_message(
                chat_id,
                f"<b>❍ ᴄᴏᴏʟᴅᴏᴡɴ :</b> "
                f"<code>{rem}s</code>",
                parse_mode=ParseMode.HTML,
            )

            _pending[chat_id] = (
                message,
                rep,
            )

            asyncio.create_task(
                _run_pending(
                    chat_id,
                    rem,
                )
            )

        return

    _last_cmd[chat_id] = now

    await _process_play(
        message,
        query,
        video=(cmd == "vplay"),
    )


# ─────────────────────────────────────────────
# PROCESS PLAY
# ─────────────────────────────────────────────

async def _process_play(
    message: Message,
    query: str,
    video: bool = False,
):

    chat_id = message.chat.id

    pm = await message.reply(
        "<b>❍ ᴘʀᴏᴄᴇssɪɴɢ...</b>",
        parse_mode=ParseMode.HTML,
    )

    # ─────────────────────────
    # ASSISTANT CHECK
    # ─────────────────────────

    try:

        from ShizuMusic.__main__ import (
            ASSISTANT_USERNAME
        )

    except Exception:

        ASSISTANT_USERNAME = ""

    if ASSISTANT_USERNAME:

        status = await _is_assistant_in(
            chat_id,
            ASSISTANT_USERNAME,
        )

        if status == "banned":

            await pm.edit_text(
                "<b>❍ ᴀssɪsᴛᴀɴᴛ ʙᴀɴɴᴇᴅ</b>",
                parse_mode=ParseMode.HTML,
            )

            return

        if not status:

            await pm.edit_text(
                "<b>❍ ᴀssɪsᴛᴀɴᴛ ᴊᴏɪɴɪɴɢ...</b>",
                parse_mode=ParseMode.HTML,
            )

            ok = await _try_join_assistant(
                chat_id,
                pm,
            )

            if not ok:
                return

    # ─────────────────────────
    # NORMALISE URL
    # ─────────────────────────

    if "youtu.be" in query:

        m = re.search(
            r"youtu\.be/([^?&]+)",
            query,
        )

        if m:

            query = (
                "https://www.youtube.com/watch?v="
                f"{m.group(1)}"
            )

    # ─────────────────────────
    # SEARCH
    # ─────────────────────────

    try:

        result = await search_yt(query)

    except Exception as e:

        await pm.edit_text(
            f"<b>❍ sᴇᴀʀᴄʜ ғᴀɪʟᴇᴅ</b>\n"
            f"<code>{e}</code>",
            parse_mode=ParseMode.HTML,
        )

        return

    # ─────────────────────────
    # PLAYLIST
    # ─────────────────────────

    if isinstance(result, dict):

        await pm.edit_text(
            "<b>❍ ᴘʟᴀʏʟɪsᴛ ɴᴏᴛ sᴜᴘᴘᴏʀᴛᴇᴅ</b>",
            parse_mode=ParseMode.HTML,
        )

        return

    # ─────────────────────────
    # SINGLE TRACK
    # ─────────────────────────

    url, title, dur_iso, thumb = result

    if not url:

        await pm.edit_text(
            "<b>❍ sᴏɴɢ ɴᴏᴛ ғᴏᴜɴᴅ</b>",
            parse_mode=ParseMode.HTML,
        )

        return

    secs = iso_to_sec(dur_iso)

    if secs > config.MAX_DURATION_SECONDS:

        await pm.edit_text(
            "<b>❍ sᴏɴɢ ᴛᴏᴏ ʟᴏɴɢ</b>",
            parse_mode=ParseMode.HTML,
        )

        return

    req = (
        message.from_user.first_name
        if message.from_user
        else "Unknown"
    )

    req_id = (
        message.from_user.id
        if message.from_user
        else 0
    )

    song = {
        "url": url,
        "title": title,
        "duration": iso_to_human(dur_iso),
        "duration_seconds": secs,
        "requester": req,
        "requester_id": req_id,
        "thumbnail": thumb,
        "video": video,
    }

    pos = add_to_queue(chat_id, song)

    # ─────────────────────────
    # PLAY NOW
    # ─────────────────────────

    if pos == 1:

        ok = await play_song(
            chat_id,
            pm,
            song,
        )

        if not ok:
            return

    # ─────────────────────────
    # ADD TO QUEUE
    # ─────────────────────────

    else:

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⌯ sᴋɪᴩ ⌯",
                        callback_data="skip",
                    ),
                    InlineKeyboardButton(
                        "⌯ ᴄʟᴇᴀʀ ⌯",
                        callback_data="clear",
                    ),
                ]
            ]
        )

        await message.reply(
            f"<b>❍ ᴀᴅᴅᴇᴅ ᴛᴏ ǫᴜᴇᴜᴇ</b>\n"
            f"<b>❍ ᴛɪᴛʟᴇ :</b> "
            f"<code>{short(title)}</code>\n"
            f"<b>❍ ᴅᴜʀ :</b> "
            f"<code>{iso_to_human(dur_iso)}</code>\n"
            f"<b>❍ ᴩᴏs :</b> "
            f"<code>#{pos - 1}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
        )

        await pm.delete()
