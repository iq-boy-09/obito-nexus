"""
OBITO NEXUS — Render-ready Telegram bot
Checker engine taken from the WORKING hi2 bot (real availability checks).

Run locally:  python bot.py
Render: Background Worker, start command `python bot.py`

Required env var : BOT_TOKEN   (falls back to the working token if unset)
Optional env vars: OWNER_USER_ID, OWNER_USERNAME, SUPPORT_CHAT, DB_FILE

Public commands: /start /help /single /bulk
Admin commands stay hidden from the public list.
"""

from flask import Flask 
from threading import Thread
import asyncio
import html
import json
import logging
import os
import random
import re
import secrets
import string
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest, NetworkError, RetryAfter, TimedOut
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, ContextTypes,
    MessageHandler, filters,
)
from telegram.request import HTTPXRequest


app = Flask(__name__)

@app.route("/")
def home():
    return "write whatever u want or create a web page❗️😼", 200

@app.route("/health")
def health():
    return "OK", 200

def run():
    app.run(host="0.0.0.0", port=10000)

def keep_alive():
    server = Thread(target=run, daemon=True)
    server.start()
keep_alive()

# ──────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

OWNER_USER_ID = int(os.getenv("OWNER_USER_ID", "7828717505"))   # your Telegram user ID
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "f4did").lstrip("@")
SUPPORT_CHAT = os.getenv("SUPPORT_CHAT", "r3alhero").lstrip("@")
BOT_NAME = "OBITO"

NEW_USER_CREDITS = 20
SINGLE_CHECK_COST = 1
BULK_CHECK_COST = 1
REFERRER_BONUS = 10
REFERRED_BONUS = 5
DB_FILE = Path(os.getenv("DB_FILE", "data/obito_db.json"))

HISTORY_CAP = 800      # kept check records
LOG_CAP = 400          # kept redeem / premium records
LIST_PAGE = 25         # rows per panel listing

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("obito")

# ── BRAND / SIGNATURE (so nobody claims it) ───────────────────
BRAND = "𝐎𝐁𝐈𝐓𝐎 𝐍𝐄𝐗𝐔𝐒"
SIGN = "ᴘᴏᴡᴇʀᴇᴅ ʙʏ ᴏʙɪᴛᴏ ꜰʀᴀᴍᴇᴡᴏʀᴋ 𖣂"
MARK_STAMP = f"⟡ {BRAND} · 𝐒𝐂𝐀𝐍 𝐂𝐎𝐑𝐄 ⟡"


# ──────────────────────────────────────────────────────────────
# REAL AVAILABILITY CHECK ENGINE  (from the working hi2 bot)
# ──────────────────────────────────────────────────────────────
SUPPORTED_DOMAINS = ["hi2.in", "telegmail.com"]
RECAPTCHA_SITEKEY = "6LfEUPkgAAAAAKTgbMoewQkWBEQhO2VPL4QviKct"
RECAPTCHA_CO = "aHR0cHM6Ly9oaTIuaW46NDQz"
RECAPTCHA_V = "XrIDux0s7SoNe6_IHkjGC92W"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 OPR/108.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",
]

DEFAULT_COOKIES = {
    "__eoi": "ID=84791c9b377760ae:T=1785815548:RT=1792303549:S=AA-AfjbAwxHu8AEDm58GilHT3t8P",
    "__gads": "ID=d35d042016429679:T=1785815548:RT=1792303548:S=ALNI_MZSbvQNM9tUxE_CmZnXbUQWGG3kdQ",
    "__gpi": "UID=0000145fbef21f84:T=1785815548:RT=1792303549:S=ALNI_MY_LJgZNcPDvOPq2U5kNuOWvCQotQ",
    "_ga": "GA1.1.1815008449.1785815546",
    "_ga_02VF9D5F26": "GS2.1.s1792303540$o18$g0$t1792303540$j60$l0$h0",
    "FCCDCF": '[null,null,null,null,null,null,[[32,"[\\"42eb93fe-68c7-4034-96db-c13bb605dd03\\",[1785815556,751000000]]"]]]',
    "FCNEC": '[["AKsRol8RF5LPgmRao6cebT6eoNufsXC40Wwgytn794ql_B5zzX--7wmkvDU6Esk0nXehFzYvJZ2jRdoE9CPO20HK1fSnQ8aIrv0vxQGTzJXI38I3eBti2LaIXRtHZiYACNxOjS3mWLkn0GetUYHYnWDfEOvrLJkhyQ=="]]',
}

# ── ANIMATION BANKS ───────────────────────────────────────────
SPINNER = ["◜", "◠", "◝", "◞", "◡", "◟"]
ORBIT = ["◜", "◝", "◞", "◟"]
GLITCH = ["◈", "◇", "◆", "◇"]
SCAN_PHASES = [
    "ʙᴏᴏᴛɪɴɢ ꜱᴄᴀɴ ᴄᴏʀᴇ",
    "ʀᴇꜱᴏʟᴠɪɴɢ ᴛᴀʀɢᴇᴛ ɴᴏᴅᴇ",
    "ꜱᴏʟᴠɪɴɢ ʜᴀɴᴅꜱʜᴀᴋᴇ",
    "Qᴜᴇʀʏɪɴɢ ʀᴇɢɪꜱᴛʀʏ",
    "ᴄʀᴏꜱꜱ-ᴄʜᴇᴄᴋɪɴɢ ʀᴇᴄᴏʀᴅꜱ",
    "ꜰɪɴᴀʟɪꜱɪɴɢ ᴠᴇʀᴅɪᴄᴛ",
]
VERDICT = {
    "taken":     ("🔴", "𝐓 𝐀 𝐊 𝐄 𝐍",   "ʀᴇɢɪꜱᴛᴇʀᴇᴅ · ᴀʟʀᴇᴀᴅʏ ɪɴ ᴜꜱᴇ"),
    "not_taken": ("🟢", "𝐅 𝐑 𝐄 𝐄",     "ᴜɴʀᴇɢɪꜱᴛᴇʀᴇᴅ · ᴏᴘᴇɴ ᴛᴏ ᴄʟᴀɪᴍ"),
    "unknown":   ("🟡", "𝐔 𝐍 𝐊 𝐍 𝐎 𝐖 𝐍", "ʀᴇɢɪꜱᴛʀʏ ꜱɪʟᴇɴᴛ · ʀᴇᴛʀʏ ᴀᴅᴠɪꜱᴇᴅ"),
}
MARK = {"taken": "🔴", "not_taken": "🟢", "unknown": "🟡"}


def _marquee(i, width=11):
    """Ping-pong radar dot inside a track."""
    span = 2 * (width - 1)
    pos = i % span
    if pos >= width:
        pos = span - pos
    return "·" * pos + "◉" + "·" * (width - pos - 1)


def _bar(done, total, width=14):
    filled = int(width * done / total) if total else 0
    filled = max(0, min(width, filled))
    return "█" * filled + "░" * (width - filled)


def scan_id():
    return secrets.token_hex(3).upper()


def stamp():
    return datetime.now(timezone.utc).strftime("%d %b · %H:%M UTC")


def short_ts():
    return datetime.now(timezone.utc).strftime("%d %b %H:%M")


def build_session(seed_cookies=True):
    s = requests.Session()
    s.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "TE": "trailers",
    })
    if seed_cookies:
        for k, v in DEFAULT_COOKIES.items():
            s.cookies.set(k, v, domain="hi2.in")
    return s


def solve_recaptcha_hi2(session):
    try:
        anchor = (
            "https://www.google.com/recaptcha/api2/anchor?ar=1"
            f"&k={RECAPTCHA_SITEKEY}&co={RECAPTCHA_CO}&hl=en"
            f"&v={RECAPTCHA_V}&size=invisible"
        )
        r = session.get(
            anchor, timeout=12,
            headers={"User-Agent": random.choice(USER_AGENTS), "Referer": "https://hi2.in/"},
        )
        if 'recaptcha-token" value="' not in r.text:
            return None
        token = r.text.split('recaptcha-token" value="')[1].split('"')[0]

        payload = (
            f"v={RECAPTCHA_V}&reason=q&c={token}&k={RECAPTCHA_SITEKEY}"
            f"&co={RECAPTCHA_CO}&hl=en&size=invisible"
        )
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Referer": anchor,
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://www.google.com",
        }
        d = session.post(
            "https://www.google.com/recaptcha/enterprise/reload",
            data=payload, headers=headers, timeout=12,
        )
        if 'resp","' not in d.text:
            return None
        return d.text.split('resp","')[1].split('"')[0]
    except Exception as e:
        log.debug("recaptcha solve failed: %s", e)
        return None


def check_hi2_email(email):
    """Returns 'taken' | 'not_taken' | 'unknown'."""
    if "@" not in email:
        return "unknown"
    prefix, domain = email.split("@", 1)
    domain = domain.lower()

    session = build_session()
    recaptcha = solve_recaptcha_hi2(session)
    if not recaptcha:
        return "unknown"

    headers = {
        "User-Agent": session.headers["User-Agent"],
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Basic bnVsbA==",
        "Origin": "https://hi2.in",
        "Referer": "https://hi2.in/",
    }
    data = {"domain": domain, "prefix": prefix, "recaptcha": recaptcha}

    try:
        r = session.post("https://hi2.in/api/custom", headers=headers, data=data, timeout=15)
        body = r.text.lower()

        if "already taken" in body or ("taken" in body and '"error"' not in body):
            try:
                j = r.json()
                if isinstance(j, dict):
                    if j.get("error") and "taken" in str(j).lower():
                        return "taken"
                    if j.get("available") is False:
                        return "taken"
                    if j.get("available") is True:
                        return "not_taken"
            except Exception:
                pass
            if "already taken" in body:
                return "taken"
            return "not_taken"

        if "available" in body:
            return "not_taken"
        return "not_taken"
    except Exception as e:
        log.debug("hi2 check error: %s", e)
        return "unknown"


# ──────────────────────────────────────────────────────────────
# ANIMATED SCAN ROUTINES
# ──────────────────────────────────────────────────────────────
async def _tick(fut, seconds=1.05):
    """Sleep in small slices while the thread future runs."""
    try:
        await asyncio.wait_for(asyncio.shield(fut), timeout=seconds)
    except asyncio.TimeoutError:
        pass


async def scan_single_animated(msg, email):
    """Animated single scan. Returns (result, elapsed_seconds, message)."""
    t0 = time.monotonic()
    fut = asyncio.ensure_future(asyncio.to_thread(check_hi2_email, email))
    target = None
    i = 0
    while not fut.done():
        phase = SCAN_PHASES[min(i // 2, len(SCAN_PHASES) - 1)]
        frame = SPINNER[i % len(SPINNER)]
        glyph = GLITCH[i % len(GLITCH)]
        track = _marquee(i)
        text = (
            "┏━━〔 🩸 " + MARK_STAMP + " 〕━━┓\n"
            f"   {track}\n"
            f"   {frame} <i>{phase}</i>…\n"
            f"   {glyph} <code>{html.escape(email)}</code>\n"
            f"   ⏱ <i>{time.monotonic() - t0:.1f}s</i>\n"
            "┗━━━━━━━━━━━━━━━━━━━━━━━━━┛"
        )
        try:
            if target is None:
                target = await msg.reply_text(text, parse_mode="HTML")
            else:
                await target.edit_text(text, parse_mode="HTML")
        except (BadRequest, NetworkError, TimedOut):
            pass
        i += 1
        await _tick(fut)
    return fut.result(), time.monotonic() - t0, target


async def scan_bulk_animated(msg, emails, status_msg):
    """Animated bulk scan with live progress bar. Returns (lines, elapsed)."""
    t0 = time.monotonic()
    total = len(emails)
    lines = []

    for idx, email in enumerate(emails, 1):
        fut = asyncio.ensure_future(asyncio.to_thread(check_hi2_email, email))
        i = 0
        while not fut.done():
            done = idx - 1
            body = [
                "┏━━〔 🩸 " + MARK_STAMP + " · 𝐁𝐔𝐋𝐊 〕━━┓",
                f"   ⟦{_bar(done, total)}⟧ <b>{int(100 * done / total)}%</b> · {done}/{total}",
                f"   {SPINNER[i % len(SPINNER)]} <i>ꜱᴄᴀɴɴɪɴɢ</i> <code>{html.escape(email)}</code>",
                f"   {_marquee(i)}",
                "┗━━━━━━━━━━━━━━━━━━━━━━━━━┛",
            ]
            if lines:
                body.append("")
                body += lines[-6:]
            try:
                await status_msg.edit_text("\n".join(body), parse_mode="HTML")
            except (BadRequest, NetworkError, TimedOut):
                pass
            i += 1
            await _tick(fut)

        result = fut.result()
        mark, label, _ = VERDICT.get(result, VERDICT["unknown"])
        lines.append(f"{idx:02d}  {mark} <code>{html.escape(email)}</code>  ‣ <b>{label}</b>")
        await asyncio.sleep(0.2)

    return lines, time.monotonic() - t0


def single_report(email, result, elapsed, uid, u):
    mark, label, note = VERDICT.get(result, VERDICT["unknown"])
    node = email.split("@", 1)[1] if "@" in email else "hi2.in"
    return (
        f"╭━━〔 <b>{BRAND}</b> · 𝐕𝐄𝐑𝐃𝐈𝐂𝐓 〕━━╮\n"
        f"   {mark}  <b>{label}</b>\n"
        f"   <i>{note}</i>\n\n"
        f"   ◈ 𝗧𝗮𝗿𝗴𝗲𝘁    ‣ <code>{html.escape(email)}</code>\n"
        f"   ◈ 𝗡𝗼𝗱𝗲      ‣ {html.escape(node)}\n"
        f"   ◈ 𝗟𝗮𝘁𝗲𝗻𝗰𝘆   ‣ {elapsed:.2f}s\n"
        f"   ◈ 𝗦𝗰𝗮𝗻 𝗜𝗗   ‣ #{scan_id()}\n"
        f"   ◈ 𝗦𝘁𝗮𝗺𝗽     ‣ {stamp()}\n\n"
        f"   {SIGN}\n"
        f"⚡ <b>𝐁𝐀𝐋𝐀𝐍𝐂𝐄</b> ‣ {html.escape(credits_label(uid, u))}"
    )


def bulk_report_chunks(lines, valid_count, elapsed):
    """Splits the bulk report so huge batches never break the 4096 limit."""
    free = sum(1 for l in lines if "𝐅 𝐑 𝐄 𝐄" in l)
    taken = sum(1 for l in lines if "𝐓 𝐀 𝐊 𝐄 𝐍" in l)
    unknown = valid_count - free - taken

    header = (
        f"╭━━〔 <b>{BRAND}</b> · 𝐒𝐂𝐀𝐍 𝐑𝐄𝐏𝐎𝐑𝐓 〕━━╮\n"
        f"   ⟨{_bar(valid_count, valid_count)}⟩ <b>100%</b> · {valid_count} ᴛᴀʀɢᴇᴛꜱ\n\n"
    )
    footer = (
        "\n┌─ 𝐒 𝐔 𝐌 𝐌 𝐀 𝐑 𝐘 ─┐\n"
        f"   🟢 𝗙𝗿𝗲𝗲      ‣ <b>{free}</b>\n"
        f"   🔴 𝗧𝗮𝗸𝗲𝗻     ‣ <b>{taken}</b>\n"
        f"   🟡 𝗨𝗻𝗸𝗻𝗼𝘄𝗻   ‣ <b>{unknown}</b>\n"
        f"   📦 𝗧𝗼𝘁𝗮𝗹     ‣ <b>{valid_count}</b>\n"
        f"   ⏱ 𝗧𝗶𝗺𝗲      ‣ {elapsed:.2f}s\n"
        f"   🆔 𝗦𝗰𝗮𝗻 𝗜𝗗   ‣ #{scan_id()}\n"
        f"   📅 𝗦𝘁𝗮𝗺𝗽     ‣ {stamp()}\n"
        "└──────────────────┘\n"
        f"   {SIGN}"
    )

    chunks, size = [], 35
    for start in range(0, len(lines), size):
        part = lines[start:start + size]
        if start == 0:
            text = header + "\n".join(part)
        else:
            text = (
                f"   … ᴄᴏɴᴛɪɴᴜᴇᴅ ({start + 1}–{start + len(part)})\n\n"
                + "\n".join(part)
            )
        chunks.append(text)

    if not chunks:
        return [header.rstrip() + footer]
    chunks[-1] += footer
    return chunks


def skipped_report(invalid):
    return (
        "⚠️ <b>𝐒 𝐊 𝐈 𝐏 𝐏 𝐄 𝐃</b>\n"
        "┌──────────────────────────┐\n"
        + "\n".join(f"   ‣ <code>{html.escape(x)}</code>  ↳ <i>ᴜɴꜱᴜᴘᴘᴏʀᴛᴇᴅ ɴᴏᴅᴇ</i>" for x in invalid)
        + "\n└──────────────────────────┘"
    )


# ──────────────────────────────────────────────────────────────
# DATABASE / HELPERS
# ──────────────────────────────────────────────────────────────
def utc_now():
    return datetime.now(timezone.utc).isoformat()


def default_db():
    return {
        "users": {},
        "admins": [OWNER_USER_ID],
        "redeem_codes": {},
        "settings": {"upi_id": "faridh@fam", "upi_name": "FARID", "price": 100, "qr_file_id": ""},
        "stats": {"total": 0, "single": 0, "bulk": 0, "taken": 0, "not_taken": 0, "unknown": 0},
        "checks": [],
        "redeem_log": [],
        "premium_log": [],
    }


def load_db():
    try:
        if DB_FILE.exists():
            with DB_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
            base = default_db()
            for k, v in base.items():
                data.setdefault(k, v)
            for k, v in base["stats"].items():
                data["stats"].setdefault(k, 0)
            data["settings"] = {**base["settings"], **data.get("settings", {})}
            return data
    except (OSError, json.JSONDecodeError) as exc:
        log.exception("Database load failed: %s", exc)
    return default_db()


DB = load_db()


def save_db():
    try:
        DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=DB_FILE.parent, delete=False) as f:
            json.dump(DB, f, indent=2, ensure_ascii=False)
            tmp = Path(f.name)
        tmp.replace(DB_FILE)
    except OSError:
        log.exception("Database save failed")


def trim(lst, cap):
    if len(lst) > cap:
        del lst[:-cap]


def log_check(uid, u, email, result, mode, save=True):
    """Records a check for the owner's history + stats."""
    DB["stats"]["total"] = DB["stats"].get("total", 0) + 1
    DB["stats"][mode] = DB["stats"].get(mode, 0) + 1
    DB["stats"][result] = DB["stats"].get(result, 0) + 1
    DB["checks"].append({
        "uid": str(uid),
        "name": u.get("name") or "User",
        "username": u.get("username") or "",
        "email": email,
        "result": result,
        "mode": mode,
        "ts": short_ts(),
    })
    trim(DB["checks"], HISTORY_CAP)
    if save:
        save_db()


def user_for(uid, first_name="User", username=None):
    key = str(uid)
    if key not in DB["users"]:
        DB["users"][key] = {
            "credits": NEW_USER_CREDITS, "unlimited": False, "referred_by": None,
            "referred_users": [], "first_time": False, "username": username,
            "name": first_name, "joined": utc_now(),
        }
        save_db()
    u = DB["users"][key]
    u["name"] = first_name or u.get("name") or "User"
    u["username"] = username
    u.setdefault("credits", NEW_USER_CREDITS)
    u.setdefault("unlimited", False)
    u.setdefault("referred_users", [])
    u.setdefault("referred_by", None)
    return u


def is_owner(uid):
    return int(uid) == OWNER_USER_ID


def is_admin(uid):
    return int(uid) in [int(x) for x in DB.get("admins", [])]


def is_staff(uid):
    return is_owner(uid) or is_admin(uid)


def has_unlimited(uid, u=None):
    u = u or DB["users"].get(str(uid), {})
    return is_owner(uid) or bool(u.get("unlimited"))


def credits_label(uid, u):
    return "♾️ UNLIMITED" if has_unlimited(uid, u) else f"⚡ {u.get('credits', 0)} credits"


def who(u, uid=None):
    name = html.escape((u.get("name") or "User")[:32])
    uname = f" @{html.escape(u['username'])}" if u.get("username") else ""
    idpart = f" · <code>{uid}</code>" if uid else ""
    return f"{name}{uname}{idpart}"


async def send_rich(bot, chat_id, text):
    """Sends raw text (HTML if possible, plain otherwise)."""
    try:
        await bot.send_message(int(chat_id), text, parse_mode="HTML")
        return True
    except BadRequest:
        try:
            await bot.send_message(int(chat_id), text)
            return True
        except Exception:
            return False
    except Exception:
        return False


# ──────────────────────────────────────────────────────────────
# KEYBOARDS / TEXTS
# ──────────────────────────────────────────────────────────────
def menu_text(uid, u):
    role = (
        "👑 OWNER" if is_owner(uid)
        else "🛡️ ADMIN" if is_admin(uid)
        else "💎 PREMIUM" if u.get("unlimited")
        else "🆓 FREE"
    )
    display_name = html.escape((u.get("name") or "User").strip()[:48])
    power = html.escape(credits_label(uid, u))
    return (
        "╭━━━〔 🌌 <b>OBITO NEXUS</b> 🌌 〕━━━╮\n"
        "┃\n"
        "┃  🎴 <b>W E L C O M E  A B O A R D</b>\n"
        "┃\n"
        f"┃  👤 <b>USER</b>  ·  {display_name}\n"
        f"┃  💠 <b>PLAN</b>  ·  {role}\n"
        f"┃  ⚡ <b>POWER</b> ·  {power}\n"
        "┃\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n"
        "⟡ <i>Precision  •  Speed  •  Power</i>\n"
        "✦ ─── ✦ ─── ✦ ─── ✦ ─── ✦\n"
        "🚀 <b>Choose Your Path Below</b>\n"
        "✦ ─── ✦ ─── ✦ ─── ✦ ─── ✦"
    )


def main_keyboard(uid):
    rows = [
        [InlineKeyboardButton("⚡ 𝑺𝒊𝒏𝒈𝒍𝒆", callback_data="single"),
         InlineKeyboardButton("🚀 𝑩𝒖𝒍𝒌", callback_data="bulk")],
        [InlineKeyboardButton("📊 𝑴𝒚 𝑺𝒕𝒂𝒕𝒔", callback_data="status"),
         InlineKeyboardButton("🎁 𝑹𝒆𝒅𝒆𝒆𝒎", callback_data="redeem")],
        [InlineKeyboardButton("🔗 𝑹𝒆𝒇𝒆𝒓 & 𝑬𝒂𝒓𝒏", callback_data="refer"),
         InlineKeyboardButton("💎 𝑷𝒓𝒆𝒎𝒊𝒖𝒎", callback_data="premium")],
        [InlineKeyboardButton("💬 𝑺𝒖𝒑𝒑𝒐𝒓𝒕", url=f"https://t.me/{SUPPORT_CHAT}"),
         InlineKeyboardButton("👑 𝑶𝒘𝒏𝒆𝒓", url=f"https://t.me/{OWNER_USERNAME}")],
    ]
    if is_staff(uid):
        rows.append([InlineKeyboardButton("🛡️ Admin panel", callback_data="panel")])
    return InlineKeyboardMarkup(rows)


def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 𝑴𝒂𝒊𝒏 𝑴𝒆𝒏𝒖", callback_data="home")]])


def panel_back():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 𝑷𝒂𝒏𝒆𝒍", callback_data="panel"),
         InlineKeyboardButton("🏠 𝑴𝒂𝒊𝒏 𝑴𝒆𝒏𝒖", callback_data="home")],
    ])


def panel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Stats", callback_data="p_stats"),
         InlineKeyboardButton("📜 Check log", callback_data="p_history")],
        [InlineKeyboardButton("👥 Users", callback_data="p_users"),
         InlineKeyboardButton("💎 Premium", callback_data="p_premium")],
        [InlineKeyboardButton("🔗 Referrals", callback_data="p_refs"),
         InlineKeyboardButton("🎁 Claims", callback_data="p_claims")],
        [InlineKeyboardButton("🛡️ Admins", callback_data="p_admins"),
         InlineKeyboardButton("📨 DM user", callback_data="dm_uid")],
        [InlineKeyboardButton("🎟️ Gen code", callback_data="gen_code"),
         InlineKeyboardButton("📜 Codes", callback_data="list_codes")],
        [InlineKeyboardButton("💰 Add credits", callback_data="add_credits"),
         InlineKeyboardButton("♾️ Grant premium", callback_data="grant")],
        [InlineKeyboardButton("🚫 Revoke premium", callback_data="revoke"),
         InlineKeyboardButton("👤 User info", callback_data="userinfo")],
        [InlineKeyboardButton("📢 Global broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("🏠 𝑴𝒂𝒊𝒏 𝑴𝒆𝒏𝒖", callback_data="home")],
    ])


SINGLE_TEXT = (
    "╭━━〔 🩸 <b>𝐒 𝐈 𝐍 𝐆 𝐋 𝐄   𝐒 𝐂 𝐀 𝐍</b> 〕━━╮\n"
    "┃\n"
    "┃  ◈ Feed me <b>one</b> email.\n"
    "┃\n"
    "┃  ┌─ 𝐄 𝐗 𝐀 𝐌 𝐏 𝐋 𝐄 ─┐\n"
    "┃  ‣ <code>obito@hi2.in</code>\n"
    "┃  └────────────┘\n"
    "┃\n"
    "┃  ⟡ ᴘᴏᴡᴇʀᴇᴅ ʙʏ ᴏʙɪᴛᴏ ꜰʀᴀᴍᴇᴡᴏʀᴋ\n"
    "╰━━━━━━━━━━━━━━━━╯"
)


def bulk_text():
    return (
        "╭━━〔 🩸 <b>𝐁 𝐔 𝐋 𝐊   𝐒 𝐂 𝐀 𝐍</b> 〕━━╮\n"
        "┃\n"
        "┃  ◈ Feed me <b>unlimited</b> emails.\n"
        "┃  ◈ Spaces, commas or new lines — all fine.\n"
        "┃\n"
        "┃  ┌─ 𝐄 𝐗 𝐀 𝐌 𝐏 𝐋 𝐄 ─┐\n"
        "┃  ‣ <code>obito@hi2.in</code>\n"
        "┃  ‣ <code>uchiha@hi2.in</code>\n"
        "┃  └────────────┘\n"
        "┃\n"
        "┃  ⟡ ᴘᴏᴡᴇʀᴇᴅ ʙʏ ᴏʙɪᴛᴏ ꜰʀᴀᴍᴇᴡᴏʀᴋ\n"
        "╰━━━━━━━━━━━━━━━━╯"
    )


# ── PANEL VIEWS ───────────────────────────────────────────────
def panel_text():
    s = DB["stats"]
    premium = sum(1 for x in DB["users"].values() if x.get("unlimited"))
    refs = sum(len(x.get("referred_users", [])) for x in DB["users"].values())
    return (
        "🛡️ <b>𝐀𝐃𝐌𝐈𝐍 𝐏𝐀𝐍𝐄𝐋</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Users        ‣ <b>{len(DB['users'])}</b>\n"
        f"💎 Premium      ‣ <b>{premium}</b>\n"
        f"🛡️ Admins       ‣ <b>{len(DB['admins'])}</b>\n"
        f"🎟️ Codes        ‣ <b>{len(DB['redeem_codes'])}</b>\n"
        f"🔗 Referrals    ‣ <b>{refs}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🔎 Checks total ‣ <b>{s.get('total', 0)}</b>\n"
        f"   ‣ ⚡ single {s.get('single', 0)} · 🚀 bulk {s.get('bulk', 0)}\n"
        f"   ‣ 🟢 {s.get('not_taken', 0)} · 🔴 {s.get('taken', 0)} · 🟡 {s.get('unknown', 0)}\n"
        f"   ‣ 🎁 claims {len(DB['redeem_log'])}\n"
        f"   ‣ 💠 premium grants {len(DB['premium_log'])}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"   {SIGN}"
    )


def history_text():
    rows = DB["checks"][-LIST_PAGE:]
    if not rows:
        return "📜 <b>𝐂𝐇𝐄𝐂𝐊 𝐋𝐎𝐆</b>\n\nNo checks recorded yet."
    out = [
        "📜 <b>𝐂𝐇𝐄𝐂𝐊 𝐋𝐎𝐆</b>",
        f"<i>last {len(rows)} of {len(DB['checks'])}</i>",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    for r in reversed(rows):
        out.append(
            f"{MARK.get(r['result'], '❔')} <code>{html.escape(r['email'])}</code>\n"
            f"   👤 {who(r, r['uid'])} · {r.get('ts', '')} · {r.get('mode', '')}"
        )
    return "\n".join(out)


def users_text():
    users = sorted(DB["users"].items(), key=lambda kv: kv[1].get("joined", ""), reverse=True)
    if not users:
        return "👥 <b>𝐔𝐒𝐄𝐑𝐒</b>\n\nNo users yet."
    out = ["👥 <b>𝐔𝐒𝐄𝐑𝐒</b>", f"<i>last {min(len(users), LIST_PAGE)} of {len(users)}</i>", "━━━━━━━━━━━━━━━━━━━━"]
    for uid, u in users[:LIST_PAGE]:
        tag = "♾️" if u.get("unlimited") else f"⚡{u.get('credits', 0)}"
        out.append(f"{tag} {who(u, uid)}")
    return "\n".join(out)


def premium_text():
    rows = [(uid, u) for uid, u in DB["users"].items() if u.get("unlimited")]
    out = ["💎 <b>𝐏𝐑𝐄𝐌𝐈𝐔𝐌 𝐔𝐒𝐄𝐑𝐒</b>", f"<i>{len(rows)} active</i>", "━━━━━━━━━━━━━━━━━━━━"]
    if not rows:
        out.append("No premium users yet.")
    for uid, u in rows[-LIST_PAGE:]:
        out.append(f"♾️ {who(u, uid)}")
    if DB["premium_log"]:
        out.append("\n<b>ʀᴇᴄᴇɴᴛ ᴍᴏᴠᴇᴍᴇɴᴛꜱ</b>")
        for r in reversed(DB["premium_log"][-8:]):
            icon = "✅" if r["action"] == "grant" else "🚫"
            out.append(f"{icon} <code>{r['uid']}</code> · {r['action']} · {r['ts']}")
    return "\n".join(out)


def refs_text():
    rows = [(uid, u) for uid, u in DB["users"].items() if u.get("referred_users")]
    total = sum(len(u.get("referred_users", [])) for _, u in rows)
    out = ["🔗 <b>𝐑𝐄𝐅𝐄𝐑𝐑𝐀𝐋𝐒</b>", f"<i>{total} total invites</i>", "━━━━━━━━━━━━━━━━━━━━"]
    if not rows:
        out.append("No referrals yet.")
    for uid, u in sorted(rows, key=lambda kv: len(kv[1]["referred_users"]), reverse=True)[:LIST_PAGE]:
        kids = u["referred_users"]
        out.append(f"👤 {who(u, uid)} ‣ <b>{len(kids)}</b> invited")
        for k in kids[:4]:
            ku = DB["users"].get(k, {})
            out.append(f"   ↳ {who(ku, k)}")
    return "\n".join(out)


def claims_text():
    out = ["🎁 <b>𝐂𝐑𝐄𝐃𝐈𝐓 𝐂𝐋𝐀𝐈𝐌𝐒</b>", f"<i>{len(DB['redeem_log'])} claims</i>", "━━━━━━━━━━━━━━━━━━━━"]
    if not DB["redeem_log"]:
        out.append("No claims yet.")
    for r in reversed(DB["redeem_log"][-LIST_PAGE:]):
        out.append(f"⚡ +{r['credits']} · <code>{r['uid']}</code> · {html.escape(r['code'])} · {r['ts']}")
    return "\n".join(out)


def admins_text():
    out = ["🛡️ <b>𝐀𝐃𝐌𝐈𝐍𝐒</b>", "━━━━━━━━━━━━━━━━━━━━"]
    for a in DB["admins"]:
        u = DB["users"].get(str(a), {})
        tag = "👑 owner" if int(a) == OWNER_USER_ID else "🛡️ admin"
        out.append(f"{tag} {who(u, a)}")
    out.append("\n<i>➕ Add admin / ➖ Remove admin — owner only</i>")
    return "\n".join(out)


def admins_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add admin", callback_data="add_admin"),
         InlineKeyboardButton("➖ Remove admin", callback_data="remove_admin")],
        [InlineKeyboardButton("🔙 𝑷𝒂𝒏𝒆𝒍", callback_data="panel"),
         InlineKeyboardButton("🏠 𝑴𝒂𝒊𝒏 𝑴𝒆𝒏𝒖", callback_data="home")],
    ])


def users_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 Check log", callback_data="p_history"),
         InlineKeyboardButton("🎁 Claims", callback_data="p_claims")],
        [InlineKeyboardButton("🔙 𝑷𝒂𝒏𝒆𝒍", callback_data="panel"),
         InlineKeyboardButton("🏠 𝑴𝒂𝒊𝒏 𝑴𝒆𝒏𝒖", callback_data="home")],
    ])


# ──────────────────────────────────────────────────────────────
# TELEGRAM HANDLERS
# ──────────────────────────────────────────────────────────────
async def safe_edit(query, text, markup=None):
    try:
        await query.edit_message_text(text, reply_markup=markup, parse_mode="HTML")
    except BadRequest as exc:
        if "Message is not modified" not in str(exc):
            log.info("Edit failed: %s", exc)
            try:
                await query.message.reply_text(text, reply_markup=markup, parse_mode="HTML")
            except Exception:
                log.exception("Fallback message failed")
    except (NetworkError, TimedOut):
        log.warning("Network issue editing message")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = user_for(user.id, user.first_name, user.username)
    if u.pop("first_time", False):
        u["credits"] = NEW_USER_CREDITS
    payload = context.args[0] if context.args else ""
    if payload.startswith("ref_") and not u.get("referred_by"):
        ref_id = payload[4:]
        if ref_id.isdigit() and ref_id != str(user.id) and ref_id in DB["users"]:
            ref = DB["users"][ref_id]
            refs = ref.setdefault("referred_users", [])
            if str(user.id) not in refs:
                refs.append(str(user.id))
                ref["credits"] = ref.get("credits", 0) + REFERRER_BONUS
                u["credits"] = u.get("credits", NEW_USER_CREDITS) + REFERRED_BONUS
                u["referred_by"] = ref_id
    save_db()
    await update.effective_message.reply_text(
        menu_text(user.id, u),
        reply_markup=main_keyboard(user.id),
        parse_mode="HTML",
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def single_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_for(user.id, user.first_name, user.username)
    context.user_data["action"] = "single"
    await update.effective_message.reply_text(
        SINGLE_TEXT, reply_markup=back_keyboard(), parse_mode="HTML"
    )


async def bulk_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_for(user.id, user.first_name, user.username)
    context.user_data["action"] = "bulk"
    await update.effective_message.reply_text(
        bulk_text(), reply_markup=back_keyboard(), parse_mode="HTML"
    )


async def status_text(uid, u):
    refs = len(u.get("referred_users", []))
    role = "OWNER" if is_owner(uid) else ("ADMIN" if is_admin(uid) else "USER")
    mine = [r for r in DB["checks"] if r["uid"] == str(uid)]
    return (
        "📊 <b>YOUR PROFILE</b>\n━━━━━━━━━━━━━━━━━━\n"
        f"👤 Name: {html.escape(u.get('name', 'User'))}\n"
        f"🆔 ID: <code>{uid}</code>\n"
        f"🔗 Username: @{html.escape(u.get('username') or 'not set')}\n"
        f"🛡️ Role: {role}\n💠 Plan: {'UNLIMITED' if has_unlimited(uid, u) else 'FREE'}\n"
        f"⚡ Credits: {credits_label(uid, u)}\n👥 Referrals: {refs}\n"
        f"🔎 Your checks: {len(mine)}"
    )


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try:
        await q.answer()
    except (BadRequest, NetworkError, TimedOut) as exc:
        log.debug("Callback acknowledgement skipped: %s", exc)

    user = q.from_user
    uid = user.id
    u = user_for(uid, user.first_name, user.username)
    data = q.data or ""

    if data == "home":
        context.user_data.pop("action", None)
        await safe_edit(q, menu_text(uid, u), main_keyboard(uid))
    elif data == "single":
        context.user_data["action"] = "single"
        await safe_edit(q, SINGLE_TEXT, back_keyboard())
    elif data == "bulk":
        context.user_data["action"] = "bulk"
        await safe_edit(q, bulk_text(), back_keyboard())
    elif data == "status":
        await safe_edit(q, await status_text(uid, u), back_keyboard())
    elif data == "redeem":
        context.user_data["action"] = "redeem"
        await safe_edit(q, "🎁 <b>REDEEM CODE</b>\n\nSend your code (example: <code>OBITO-ABC123</code>).", back_keyboard())
    elif data == "refer":
        bot_username = context.bot_data.get("bot_username")
        if not bot_username:
            bot = await context.bot.get_me()
            bot_username = bot.username
            context.bot_data["bot_username"] = bot_username
        link = f"https://t.me/{bot_username}?start=ref_{uid}"
        await safe_edit(
            q,
            "🔗 <b>ＲＥＦＥＲ & ＥＡＲＮ</b>\n"
            "✦ ─── ✦ ─── ✦ ─── ✦\n\n"
            f"Invite your friends with this link:\n<code>{link}</code>\n\n"
            f"🎁 You earn <b>+{REFERRER_BONUS} credits</b>\n"
            f"🌷 Your friend gets <b>+{REFERRED_BONUS} credits</b>",
            back_keyboard(),
        )
    elif data == "premium":
        s = DB["settings"]
        payment_text = (
            f"💎 <b>PREMIUM PLAN</b>\n\nPrice: ₹{s.get('price', 100)}\n"
            f"UPI: <code>{html.escape(str(s.get('upi_id', 'faridh@fam')))}</code>\n"
            f"Name: {html.escape(str(s.get('upi_name', 'FARID')))}\n\n"
            "Scan the QR and pay, then send the screenshot for verification."
        )
        await safe_edit(q, payment_text, back_keyboard())
        qr_file_id = s.get("qr_file_id")
        if qr_file_id:
            try:
                await q.message.reply_photo(photo=qr_file_id, caption="💳 <b>UPI QR</b>", parse_mode="HTML")
            except (NetworkError, TimedOut, BadRequest) as exc:
                log.warning("Could not send payment QR: %s", exc)

    # ── panel ────────────────────────────────────────────────
    elif data == "panel":
        if not is_staff(uid):
            await safe_edit(q, "⛔ Not authorized.", back_keyboard())
            return
        await safe_edit(q, panel_text(), panel_keyboard())
    elif data == "p_stats":
        if not is_staff(uid):
            await safe_edit(q, "⛔ Not authorized.", back_keyboard())
            return
        await safe_edit(q, panel_text(), panel_keyboard())
    elif data == "p_history":
        if not is_staff(uid):
            await safe_edit(q, "⛔ Not authorized.", back_keyboard())
            return
        await safe_edit(q, history_text(), users_keyboard())
    elif data == "p_users":
        if not is_staff(uid):
            await safe_edit(q, "⛔ Not authorized.", back_keyboard())
            return
        await safe_edit(q, users_text(), users_keyboard())
    elif data == "p_premium":
        if not is_staff(uid):
            await safe_edit(q, "⛔ Not authorized.", back_keyboard())
            return
        await safe_edit(q, premium_text(), panel_back())
    elif data == "p_refs":
        if not is_staff(uid):
            await safe_edit(q, "⛔ Not authorized.", back_keyboard())
            return
        await safe_edit(q, refs_text(), panel_back())
    elif data == "p_claims":
        if not is_staff(uid):
            await safe_edit(q, "⛔ Not authorized.", back_keyboard())
            return
        await safe_edit(q, claims_text(), panel_back())
    elif data == "p_admins":
        if not is_staff(uid):
            await safe_edit(q, "⛔ Not authorized.", back_keyboard())
            return
        await safe_edit(q, admins_text(), admins_keyboard())

    # ── panel actions ────────────────────────────────────────
    elif data in {"gen_code", "add_credits", "grant", "revoke", "userinfo", "broadcast",
                  "dm_uid", "add_admin", "remove_admin"}:
        if not is_staff(uid):
            await safe_edit(q, "⛔ Not authorized.", back_keyboard())
            return
        if data in {"add_admin", "remove_admin"} and not is_owner(uid):
            await safe_edit(q, "⛔ Owner only.", panel_back())
            return
        context.user_data["action"] = data
        prompts = {
            "gen_code": "Send: <code>CREDITS MAX_CLAIMS</code>",
            "add_credits": "Send: <code>USER_ID AMOUNT</code>",
            "grant": "Send the user ID to grant premium.",
            "revoke": "Send the user ID to revoke premium.",
            "userinfo": "Send a user ID.",
            "broadcast": "Send the broadcast message (sent to everyone, exactly as typed).",
            "dm_uid": "Send the target user ID.",
            "add_admin": "Send the user ID to promote to admin.",
            "remove_admin": "Send the admin user ID to demote.",
        }
        await safe_edit(q, f"🛠️ <b>ADMIN ACTION</b>\n\n{prompts[data]}", panel_back())
    elif data == "list_codes":
        if not is_staff(uid):
            await safe_edit(q, "⛔ Not authorized.", back_keyboard())
            return
        if not DB["redeem_codes"]:
            text = "📭 No redeem codes yet."
        else:
            text = "📜 <b>REDEEM CODES</b>\n\n" + "\n".join(
                f"<code>{html.escape(c)}</code> · {d['credits']} credits · {len(d.get('claimed_by', []))}/{d['max_claims']}"
                for c, d in list(DB["redeem_codes"].items())[-30:]
            )
        await safe_edit(q, text, panel_back())


# ── CHECK FLOW ────────────────────────────────────────────────
def parse_entries(text, single_mode):
    if single_mode:
        parts = [text.splitlines()[0].strip()] if text.splitlines() else []
    else:
        parts = [t for t in re.split(r"[\s,]+", text) if t]

    seen, items = set(), []
    for it in parts:
        it = it.strip().lower()
        if not it or it in seen:
            continue
        seen.add(it)
        items.append(it)

    valid, invalid = [], []
    for it in items:
        if "@" in it:
            prefix, dom = it.split("@", 1)
            if dom not in SUPPORTED_DOMAINS:
                invalid.append(it)
                continue
            valid.append(f"{prefix}@{dom}")
        else:
            valid.append(f"{it}@hi2.in")
    return valid, invalid


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    uid = user.id
    u = user_for(uid, user.first_name, user.username)
    text = (msg.text or "").strip()
    action = context.user_data.get("action")

    # ── redeem ───────────────────────────────────────────────
    if action == "redeem":
        code = text.upper()
        item = DB["redeem_codes"].get(code)
        if not item:
            await msg.reply_text("❌ Invalid code.")
        elif str(uid) in item.get("claimed_by", []):
            await msg.reply_text("ℹ️ You have already claimed this code.")
        elif len(item.get("claimed_by", [])) >= int(item.get("max_claims", 0)):
            await msg.reply_text("⚠️ This code has reached its claim limit.")
        else:
            item.setdefault("claimed_by", []).append(str(uid))
            u["credits"] = u.get("credits", 0) + int(item["credits"])
            DB["redeem_log"].append({
                "uid": str(uid), "code": code, "credits": int(item["credits"]), "ts": short_ts(),
            })
            trim(DB["redeem_log"], LOG_CAP)
            save_db()
            await msg.reply_text(f"✅ Code redeemed! +{item['credits']} credits.\nBalance: {u['credits']}")
        context.user_data.pop("action", None)
        return

    # ── personal DM (two steps) ──────────────────────────────
    if action == "dm_uid":
        target = text.strip()
        if not target.isdigit():
            await msg.reply_text("⚠️ Send a numeric user ID.")
            return
        context.user_data["dm_target"] = target
        context.user_data["action"] = "dm_text"
        await msg.reply_text(f"✍️ Now send the message for <code>{target}</code>.", parse_mode="HTML")
        return

    if action == "dm_text":
        target = context.user_data.pop("dm_target", None)
        context.user_data.pop("action", None)
        if not target:
            await msg.reply_text("⚠️ Target lost, try again.")
            return
        ok = await send_rich(context.bot, target, text)
        await msg.reply_text("✅ Delivered." if ok else "❌ Delivery failed.")
        return

    # ── single / bulk checks ─────────────────────────────────
    if action in {"single", "bulk"}:
        single_mode = action == "single"
        valid, invalid = parse_entries(text, single_mode)

        if not valid:
            await msg.reply_text(
                "❌ <b>𝐍𝐎 𝐕𝐀𝐋𝐈𝐃 𝐓𝐀𝐑𝐆𝐄𝐓 𝐅𝐎𝐔𝐍𝐃</b>\n"
                "┌──────────────────────────┐\n"
                "   ‣ <code>user@hi2.in</code>\n"
                "   ‣ <code>user2</code>\n"
                "└──────────────────────────┘",
                parse_mode="HTML",
            )
            return

        cost = len(valid) * (SINGLE_CHECK_COST if single_mode else BULK_CHECK_COST)
        if not has_unlimited(uid, u) and u.get("credits", 0) < cost:
            await msg.reply_text(
                f"❌ Not enough credits. Required: {cost}; balance: {u.get('credits', 0)}."
            )
            context.user_data.pop("action", None)
            return

        if not has_unlimited(uid, u):
            u["credits"] -= cost
            save_db()

        # ── SINGLE ───────────────────────────────────────────
        if single_mode:
            email = valid[0]
            result, elapsed, status_msg = await scan_single_animated(msg, email)
            log_check(uid, u, email, result, "single")
            report = single_report(email, result, elapsed, uid, u)

            if status_msg is None:
                await msg.reply_text(report, parse_mode="HTML")
            else:
                try:
                    await status_msg.edit_text(report, parse_mode="HTML")
                except BadRequest:
                    await msg.reply_text(report, parse_mode="HTML")

            if invalid:
                await msg.reply_text(skipped_report(invalid), parse_mode="HTML")
            context.user_data.pop("action", None)
            return

        # ── BULK (no limit) ──────────────────────────────────
        status_msg = await msg.reply_text(
            "┏━━〔 🩸 " + MARK_STAMP + " · 𝐁𝐔𝐋𝐊 〕━━┓\n"
            f"   ⟦{_bar(0, len(valid))}⟧ <b>0%</b>\n"
            "   ◜ <i>ᴡᴀʀᴍɪɴɢ ᴜᴘ ꜱᴄᴀɴ ᴄᴏʀᴇ</i>…\n"
            "┗━━━━━━━━━━━━━━━━━━━━━━━━━┛",
            parse_mode="HTML",
        )
        lines, elapsed = await scan_bulk_animated(msg, valid, status_msg)

        for email, line in zip(valid, lines):
            res = "taken" if "𝐓 𝐀 𝐊 𝐄 𝐍" in line else ("not_taken" if "𝐅 𝐑 𝐄 𝐄" in line else "unknown")
            log_check(uid, u, email, res, "bulk", save=False)
        save_db()

        chunks = bulk_report_chunks(lines, len(valid), elapsed)
        try:
            await status_msg.edit_text(chunks[0], parse_mode="HTML")
        except BadRequest:
            await msg.reply_text(chunks[0], parse_mode="HTML")
        for chunk in chunks[1:]:
            await msg.reply_text(chunk, parse_mode="HTML")

        if invalid:
            await msg.reply_text(skipped_report(invalid), parse_mode="HTML")
        context.user_data.pop("action", None)
        return

    # ── admin actions ────────────────────────────────────────
    if action and is_staff(uid):
        parts = text.split()
        try:
            if action == "gen_code":
                if len(parts) != 2:
                    raise ValueError
                credits, max_claims = int(parts[0]), int(parts[1])
                if credits < 1 or max_claims < 1:
                    raise ValueError
                code = "OBITO-" + "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
                DB["redeem_codes"][code] = {"credits": credits, "max_claims": max_claims, "claimed_by": []}
                save_db()
                await msg.reply_text(
                    f"✅ Code created: <code>{code}</code>\nCredits: {credits} · Claims: {max_claims}",
                    parse_mode="HTML",
                )
            elif action == "add_credits":
                if len(parts) != 2:
                    raise ValueError
                target, amount = str(int(parts[0])), int(parts[1])
                if amount < 1:
                    raise ValueError
                tu = DB["users"].setdefault(
                    target,
                    {"credits": 0, "unlimited": False, "referred_users": [], "name": "User", "joined": utc_now()},
                )
                tu["credits"] = tu.get("credits", 0) + amount
                save_db()
                await msg.reply_text(f"✅ Added {amount} credits to <code>{target}</code>.", parse_mode="HTML")
                await send_rich(
                    context.bot, target,
                    "⚡ <b>𝐂𝐑𝐄𝐃𝐈𝐓𝐒 𝐀𝐃𝐃𝐄𝐃</b>\n"
                    f"   ‣ +{amount} credits\n"
                    f"   ‣ Balance: <b>{tu['credits']}</b>\n"
                    f"   {SIGN}",
                )
            elif action in {"grant", "revoke"}:
                target = str(int(text))
                tu = DB["users"].setdefault(
                    target,
                    {"credits": 0, "unlimited": False, "referred_users": [], "name": "User", "joined": utc_now()},
                )
                tu["unlimited"] = action == "grant"
                DB["premium_log"].append({"uid": target, "action": action, "ts": short_ts()})
                trim(DB["premium_log"], LOG_CAP)
                save_db()
                await msg.reply_text(
                    f"✅ Premium {'granted' if action == 'grant' else 'revoked'} for <code>{target}</code>.",
                    parse_mode="HTML",
                )
                if action == "grant":
                    await send_rich(
                        context.bot, target,
                        "💎 <b>𝐏𝐑𝐄𝐌𝐈𝐔𝐌 𝐀𝐂𝐓𝐈𝐕𝐀𝐓𝐄𝐃</b>\n"
                        "   ‣ Plan: ♾️ UNLIMITED\n"
                        "   ‣ All scans are now free.\n"
                        f"   {SIGN}",
                    )
                else:
                    await send_rich(
                        context.bot, target,
                        "🚫 <b>𝐏𝐑𝐄𝐌𝐈𝐔𝐌 𝐄𝐗𝐏𝐈𝐑𝐄𝐃</b>\n"
                        "   ‣ Plan: 🆓 FREE\n"
                        f"   ‣ Credits: <b>{tu.get('credits', 0)}</b>\n"
                        f"   {SIGN}",
                    )
            elif action == "userinfo":
                target = str(int(text))
                tu = DB["users"].get(target)
                if not tu:
                    await msg.reply_text("User not found in the database.")
                else:
                    checks = [r for r in DB["checks"] if r["uid"] == target]
                    await msg.reply_text(
                        f"👤 <b>User info</b>\nID: <code>{target}</code>\nName: {html.escape(tu.get('name', 'User'))}\n"
                        f"Username: @{html.escape(tu.get('username') or 'not set')}\n"
                        f"Credits: {tu.get('credits', 0)}\nPremium: {bool(tu.get('unlimited'))}\n"
                        f"Referrals: {len(tu.get('referred_users', []))}\n"
                        f"Checks done: {len(checks)}\nJoined: {tu.get('joined', '')[:16]}",
                        parse_mode="HTML",
                    )
            elif action == "broadcast":
                sent = failed = 0
                await msg.reply_text(f"📢 Broadcasting to {len(DB['users'])} users…")
                for target in list(DB["users"]):
                    if await send_rich(context.bot, target, text):
                        sent += 1
                    else:
                        failed += 1
                    await asyncio.sleep(0.05)
                await msg.reply_text(f"✅ Broadcast finished.\nSent: {sent}\nFailed: {failed}")
            elif action in {"add_admin", "remove_admin"}:
                if not is_owner(uid):
                    raise PermissionError
                target = str(int(text))
                if action == "add_admin":
                    if int(target) not in [int(x) for x in DB["admins"]]:
                        DB["admins"].append(int(target))
                        save_db()
                        await send_rich(
                            context.bot, target,
                            "🛡️ <b>𝐀𝐃𝐌𝐈𝐍 𝐀𝐂𝐂𝐄𝐒𝐒 𝐆𝐑𝐀𝐍𝐓𝐄𝐃</b>\n"
                            "   ‣ Panel unlocked.\n"
                            f"   {SIGN}",
                        )
                    await msg.reply_text(f"✅ <code>{target}</code> is now an admin.", parse_mode="HTML")
                else:
                    if int(target) == OWNER_USER_ID:
                        await msg.reply_text("👑 Owner can't be demoted.")
                    else:
                        DB["admins"] = [x for x in DB["admins"] if int(x) != int(target)]
                        save_db()
                        await send_rich(
                            context.bot, target,
                            "🚫 <b>𝐀𝐃𝐌𝐈𝐍 𝐀𝐂𝐂𝐄𝐒𝐒 𝐑𝐄𝐕𝐎𝐊𝐄𝐃</b>\n"
                            f"   {SIGN}",
                        )
                        await msg.reply_text(f"✅ <code>{target}</code> demoted.", parse_mode="HTML")
        except (ValueError, TypeError):
            await msg.reply_text("⚠️ Invalid format. Please check the requested format and try again.")
        context.user_data.pop("action", None)
        return

    if text.startswith("/"):
        return
    await msg.reply_text(menu_text(uid, u), reply_markup=main_keyboard(uid), parse_mode="HTML")


# ──────────────────────────────────────────────────────────────
# HIDDEN ADMIN COMMANDS (not in public list)
# ──────────────────────────────────────────────────────────────
async def setqr_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    if not user or not is_owner(user.id):
        await msg.reply_text("⛔ Only the bot owner can set the payment QR.")
        return
    replied = msg.reply_to_message
    if not replied:
        await msg.reply_text("Reply to an image with /setqr to save it as the payment QR.")
        return
    file_id = None
    if replied.photo:
        file_id = replied.photo[-1].file_id
    elif replied.document and (replied.document.mime_type or "").startswith("image/"):
        file_id = replied.document.file_id
    if not file_id:
        await msg.reply_text("⚠️ The replied message must contain an image/photo.")
        return
    DB["settings"]["qr_file_id"] = file_id
    DB["settings"]["upi_id"] = "faridh@fam"
    DB["settings"]["upi_name"] = "FARID"
    save_db()
    await msg.reply_text("✅ Payment QR saved! Premium users will now see this QR.")


async def panel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_staff(update.effective_user.id):
        await update.effective_message.reply_text("⛔ Not authorized.")
        return
    await update.effective_message.reply_text(panel_text(), reply_markup=panel_keyboard(), parse_mode="HTML")


async def addcredits_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid):
        await update.effective_message.reply_text("⛔ Not authorized.")
        return
    if len(context.args) != 2:
        await update.effective_message.reply_text("Usage: /addcredits USER_ID AMOUNT")
        return
    try:
        target, amount = str(int(context.args[0])), int(context.args[1])
        if amount < 1:
            raise ValueError
    except ValueError:
        await update.effective_message.reply_text("Invalid user ID or amount.")
        return
    tu = DB["users"].setdefault(
        target,
        {"credits": 0, "unlimited": False, "referred_users": [], "name": "User", "joined": utc_now()},
    )
    tu["credits"] = tu.get("credits", 0) + amount
    save_db()
    await update.effective_message.reply_text(f"✅ Added {amount} credits to {target}.")
    await send_rich(
        context.bot, target,
        "⚡ <b>𝐂𝐑𝐄𝐃𝐈𝐓𝐒 𝐀𝐃𝐃𝐄𝐃</b>\n"
        f"   ‣ +{amount} credits\n"
        f"   ‣ Balance: <b>{tu['credits']}</b>\n"
        f"   {SIGN}",
    )


async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid):
        await update.effective_message.reply_text("⛔ Owner only.")
        return
    if len(context.args) != 1:
        await update.effective_message.reply_text("Usage: /addadmin USER_ID")
        return
    try:
        target = str(int(context.args[0]))
    except ValueError:
        await update.effective_message.reply_text("Invalid user ID.")
        return
    if int(target) not in [int(x) for x in DB["admins"]]:
        DB["admins"].append(int(target))
        save_db()
        await send_rich(
            context.bot, target,
            "🛡️ <b>𝐀𝐃𝐌𝐈𝐍 𝐀𝐂𝐂𝐄𝐒𝐒 𝐆𝐑𝐀𝐍𝐓𝐄𝐃</b>\n   ‣ Panel unlocked.\n"
            f"   {SIGN}",
        )
    await update.effective_message.reply_text(f"✅ {target} is now an admin.")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    err = context.error
    if isinstance(err, (TimedOut, NetworkError)):
        log.warning("Temporary Telegram network failure: %s", err)
        return
    if isinstance(err, RetryAfter):
        log.warning("Telegram rate limit reached; retry after %s seconds", err.retry_after)
        return
    log.error("Unhandled update error", exc_info=(type(err), err, err.__traceback__))


async def post_init(app: Application):
    me = await app.bot.get_me()
    app.bot_data["bot_username"] = me.username
    log.info("OBITO NEXUS online as @%s", me.username)
    try:
        await app.bot.set_my_commands([
            ("start", "Open the main menu"),
            ("help", "Show the main menu"),
            ("single", "Check one email address"),
            ("bulk", "Check multiple email addresses"),
        ])
    except Exception:
        log.exception("Could not set bot commands")


def main():
    if not BOT_TOKEN:
        raise SystemExit("Missing BOT_TOKEN environment variable.")

    print("""
    ╭─────────────────────────────╮
    │      OBITO NEXUS            │
    │      scan core · v3         │
    ╰─────────────────────────────╯
    ◈ System initialised
    ◈ Waiting for incoming updates
    """)

    normal_request = HTTPXRequest(
        connection_pool_size=16, connect_timeout=30, read_timeout=40,
        write_timeout=30, pool_timeout=30,
    )
    polling_request = HTTPXRequest(
        connection_pool_size=4, connect_timeout=30, read_timeout=50,
        write_timeout=30, pool_timeout=30,
    )
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(normal_request)
        .get_updates_request(polling_request)
        .post_init(post_init)
        .build()
    )
    app.add_error_handler(error_handler)

    # Public commands
    app.add_handler(CommandHandler(["start", "help"], start))
    app.add_handler(CommandHandler("single", single_cmd))
    app.add_handler(CommandHandler("bulk", bulk_cmd))

    # Hidden admin commands
    app.add_handler(CommandHandler("panel", panel_cmd))
    app.add_handler(CommandHandler("addcredits", addcredits_cmd))
    app.add_handler(CommandHandler("addadmin", admin_cmd))
    app.add_handler(CommandHandler("setqr", setqr_cmd))

    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    log.info("Starting long-polling worker")
    app.run_polling(drop_pending_updates=False, allowed_updates=Update.ALL_TYPES, timeout=30)


if __name__ == "__main__":
    main()
