"""
OBITO NEXUS — Render-ready Telegram bot (REAL availability checks)
Run locally:  python bot.py
Render: Background Worker, start command `python bot.py`
Required env var: BOT_TOKEN
Optional env vars: OWNER_USER_ID, OWNER_USERNAME, SUPPORT_CHAT, DB_FILE

Public commands: /start /help /single /bulk
Admin commands are hidden from the public list — owner knows what's his.
"""
import html
import json
import logging
import os
import re
import secrets
import string
import tempfile
import time
import uuid
import base64
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

try:
    import httpx
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx", "httpx[http2]"])
    import httpx

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OWNER_USER_ID = int(os.getenv("OWNER_USER_ID", "7828717505"))  # replace with your Telegram user ID
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "f4did").lstrip("@") # replace with your Telegram username
SUPPORT_CHAT = os.getenv("SUPPORT_CHAT", "r3alhero").lstrip("@") # replace with your support chat username
BOT_NAME = "OBITO" # bot name
BULK_BATCH_SIZE = 20 # maximum number of emails to check in bulk
NEW_USER_CREDITS = 20 # initial credits for new users
SINGLE_CHECK_COST = 1 # cost per single email check
BULK_CHECK_COST = 1 # cost per email in bulk check
REFERRER_BONUS = 10 # credits for the user who refers someone
REFERRED_BONUS = 5 # credits for the user who is referred
DB_FILE = Path(os.getenv("DB_FILE", "data/obito_db.json"))

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("obito")


# ──────────────────────────────────────────────────────────────
# REAL AVAILABILITY CHECK ENGINE
# ──────────────────────────────────────────────────────────────

def generate_android_ua():
    devices = [
        {"brand": "samsung", "model": "SM-G973F", "device": "beyond1", "board": "exynos9820"},
        {"brand": "Google", "model": "Pixel 7", "device": "panther", "board": "panther"},
        {"brand": "Xiaomi", "model": "Redmi Note 10", "device": "sweet", "board": "sm6150"},
        {"brand": "OnePlus", "model": "ONEPLUS A6003", "device": "OnePlus6", "board": "sdm845"},
    ]
    device = __import__("random").choice(devices)
    android_version = __import__("random").choice(["12", "13", "14"])
    api_level = {"12": "31", "13": "33", "14": "34"}[android_version]
    dpi = __import__("random").choice(["320", "450", "480"])
    instagram_ver = f"{__import__('random').randint(300, 370)}.0.0.{__import__('random').randint(10, 40)}.{__import__('random').randint(80, 150)}"
    locale = __import__("random").choice(["en_US", "en_IN", "en_GB"])
    return (f"Instagram {instagram_ver} Android ({api_level}/{android_version}; "
            f"{dpi}dpi; 1080x2207; {device['brand']}; {device['model']}; "
            f"{device['device']}; {device['board']}; {locale}; {__import__('random').randint(300000000, 400000000)})")


def solve_recaptcha_hi2():
    try:
        anchor_url = (
            "https://www.google.com/recaptcha/api2/anchor?ar=1&"
            "k=6LfEUPkgAAAAAKTgbMoewQkWBEQhO2VPL4QviKct&"
            "co=aHR0cHM6Ly9oaTIuaW46NDQz&hl=en&"
            "v=XrIDux0s7SoNe6_IHkjGC92W&size=invisible"
        )
        params = anchor_url.split('?')[1]
        r = requests.get(
            f'https://www.google.com/recaptcha/enterprise/anchor?{params}',
            timeout=10,
        )
        recaptcha_token = r.text.split('recaptcha-token" value="')[1].split('"')[0]
        payload = (
            f"v={params.split('v=')[1].split('&')[0]}&reason=q&c={recaptcha_token}"
            f"&k=6LfEUPkgAAAAAKTgbMoewQkWBEQhO2VPL4QviKct"
            f"&co=aHR0cHM6Ly9oaTIuaW46NDQz&hl=en&size=invisible"
        )
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": f"https://www.google.com/recaptcha/enterprise/anchor?{params}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        resp = requests.post(
            'https://www.google.com/recaptcha/enterprise/reload',
            data=payload,
            headers=headers,
            timeout=10,
        )
        token = resp.text.split('resp","')[1].split('"')[0]
        return token
    except Exception as e:
        log.debug("recaptcha solve failed: %s", e)
        return None


def check_hi2_registration(email):
    if "@" not in email:
        return None
    domain = email.split("@")[1]
    prefix = email.split("@")[0]
    solve = solve_recaptcha_hi2()
    if not solve:
        return None
    data = {'domain': domain, 'prefix': prefix, 'recaptcha': solve}
    headers = {
        'User-Agent': "Mozilla/5.0",
        'Accept': "application/json, text/plain, */*",
        'authorization': "Basic bnVsbA==",
    }
    try:
        response = requests.post(
            "https://hi2.in/api/custom", data=data, headers=headers, timeout=15,
        )
        res = response.json()
        if "already taken" in str(res):
            return True
        return False
    except Exception as e:
        log.debug("hi2 check error: %s", e)
        return None


def check_instagram_registration(email):
    try:
        url = "https://i.instagram.com/api/v1/users/check_email/"
        ua = generate_android_ua()
        response = httpx.Client(http2=True).post(
            url,
            data=f"email={email}",
            headers={
                'User-Agent': ua,
                'content-type': "application/x-www-form-urlencoded; charset=UTF-8",
            },
            timeout=15,
        )
        if 'email_is_taken' in response.text:
            return True
        return False
    except Exception as e:
        log.debug("instagram check error: %s", e)
        return None


def check_bloks_registration(email):
    try:
        url = "https://i.instagram.com/api/v1/bloks/async_action/com.bloks.www.caa.ar.search.async/"
        device = str(uuid.uuid4())
        family = str(uuid.uuid4())
        android = "android-" + secrets.token_hex(8)
        payload = {
            'params': '{"client_input_params":{"aac":"{\\"aac_init_timestamp\\":' + str(int(time.time())) + ',\\"aacjid\\":\\"' + str(uuid.uuid4()) + '\\",\\"aaccs\\":\\"' + secrets.token_urlsafe(32) + '\\"}","flash_call_permissions_status":{"READ_PHONE_STATE":"PERMANENTLY_DENIED","READ_CALL_LOG":"DENIED","ANSWER_PHONE_CALLS":"DENIED"},"was_headers_prefill_available":0,"network_bssid":null,"sfdid":"","fetched_email_token_list":{},"search_query":"' + email + '","auth_secure_device_id":"","ig_oauth_token":[],"cloud_trust_token":null,"was_headers_prefill_used":0,"sso_accounts_auth_data":[],"encrypted_msisdn":"","device_network_info":null,"text_input_id":"akyuf0:61","zero_balance_state":null,"android_build_type":"release","accounts_list":[],"is_oauth_without_permission":0,"ig_android_qe_device_id":"' + device + '","gms_incoming_call_retriever_eligibility":"client_not_supported","search_screen_type":"email_or_username","is_whatsapp_installed":1,"lois_settings":{"lois_token":""},"ig_vetted_device_nonce":null,"headers_infra_flow_id":"","fetched_email_list":[]},"server_params":{"event_request_id":"' + str(uuid.uuid4()) + '","is_from_logged_out":0,"layered_homepage_experiment_group":null,"device_id":"' + android + '","login_surface":"login_home","waterfall_id":"' + str(uuid.uuid4()) + '","INTERNAL__latency_qpl_instance_id":6.3987980400102E13,"is_platform_login":0,"context_data":"","login_entry_point":"logged_out","INTERNAL__latency_qpl_marker_id":36707139,"family_device_id":"' + family + '","offline_experiment_group":"caa_iteration_v3_perf_ig_4","access_flow_version":"pre_mt_behavior","is_from_logged_in_switcher":0,"qe_device_id":"' + device + '"}}',
            'bk_client_context': '{"bloks_version":"5e47baf35c5a270b44c8906c8b99063564b30ef69779f3dee0b828bee2e4ef5b","styles_id":"instagram"}',
            'bloks_versioning_id': "5e47baf35c5a270b44c8906c8b99063564b30ef69779f3dee0b828bee2e4ef5b",
        }
        headers = {
            'User-Agent': "Instagram 370.1.0.43.96 Android (34/14; 450dpi; 1080x2207; samsung; SM-A235F; a23; qcom; en_IN; 704872281)",
            'accept-language': "en-IN, en-US",
            'x-bloks-version-id': "5e47baf35c5a270b44c8906c8b99063564b30ef69779f3dee0b828bee2e4ef5b",
            'x-fb-friendly-name': "IgApi: bloks/async_action/com.bloks.www.caa.ar.search.async/",
            'x-ig-android-id': android,
            'x-ig-app-id': "567067343352427",
            'x-ig-app-locale': "en_IN",
            'x-ig-device-id': device,
            'x-ig-family-device-id': family,
            'x-ig-timezone-offset': str(datetime.now().astimezone().utcoffset().total_seconds()),
            'x-mid': base64.urlsafe_b64encode(secrets.token_bytes(18)).decode().rstrip('='),
            'x-pigeon-rawclienttime': str(time.time()),
            'x-pigeon-session-id': f"UFS-{uuid.uuid4()}-0",
        }
        response = requests.post(url, data=payload, headers=headers, timeout=20)
        if email in response.text:
            return True
        return False
    except Exception as e:
        log.debug("bloks check error: %s", e)
        return None


def check_email_availability(email, domain):
    ig_result = check_instagram_registration(email)
    if ig_result is True:
        return "taken"
    elif ig_result is False:
        if domain == "hi2.in":
            hi2_result = check_hi2_registration(email)
            if hi2_result is True:
                return "taken"
            elif hi2_result is False:
                return "not_taken"
            return "not_taken"
        return "not_taken"
    else:
        bloks_result = check_bloks_registration(email)
        if bloks_result is True:
            return "taken"
        elif bloks_result is False:
            if domain == "hi2.in":
                hi2_result = check_hi2_registration(email)
                if hi2_result is True:
                    return "taken"
                elif hi2_result is False:
                    return "not_taken"
            return "not_taken"
        else:
            if domain == "hi2.in":
                hi2_result = check_hi2_registration(email)
                if hi2_result is True:
                    return "taken"
                elif hi2_result is False:
                    return "not_taken"
            return "unknown"


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
    }


def load_db():
    try:
        if DB_FILE.exists():
            with DB_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
            base = default_db()
            for k, v in base.items():
                data.setdefault(k, v)
            data["settings"] = {**base["settings"], **data.get("settings", {})}
            if not data["settings"].get("qr_file_id") and data["settings"].get("qr_url"):
                data["settings"]["qr_file_id"] = data["settings"].get("qr_url", "")
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


def menu_text(uid, u):
    role = (
        "👑 OWNER" if is_owner(uid)
        else "🛡️ ADMIN" if is_admin(uid)
        else "💎 PREMIUM" if u.get("unlimited")
        else "🆓 FREE"
    )
    display_name = html.escape((u.get("name") or "Farid").strip()[:48])
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


def panel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎟️ Generate code", callback_data="gen_code"),
         InlineKeyboardButton("📜 List codes", callback_data="list_codes")],
        [InlineKeyboardButton("💰 Add credits", callback_data="add_credits"),
         InlineKeyboardButton("♾️ Grant unlimited", callback_data="grant")],
        [InlineKeyboardButton("🚫 Revoke unlimited", callback_data="revoke"),
         InlineKeyboardButton("👤 User info", callback_data="userinfo")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("🏠 𝑴𝒂𝒊𝒏 𝑴𝒆𝒏𝒖", callback_data="home")],
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
    """Public command: arm single-check mode."""
    user = update.effective_user
    u = user_for(user.id, user.first_name, user.username)
    context.user_data["action"] = "single"
    await update.effective_message.reply_text(
        "╭━━〔 ⚡ <b>S I N G L E</b> 〕━━╮\n\n"
        "Send one email address for REAL availability check.\n"
        "✦ ─── ✦ ─── ✦\n"
        "<i>Checks hi2 & telegmail with IG </i>",
        reply_markup=back_keyboard(),
        parse_mode="HTML",
    )


async def bulk_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Public command: arm bulk-check mode."""
    user = update.effective_user
    u = user_for(user.id, user.first_name, user.username)
    context.user_data["action"] = "bulk"
    await update.effective_message.reply_text(
        f"╭━━〔 🚀 <b>B U L K</b> 〕━━╮\n\n"
        f"Send up to <b>{BULK_BATCH_SIZE}</b> email addresses, one per line.\n"
        "✦ ─── ✦ ─── ✦\n"
        "<i>Real availability checks • Be patient</i>",
        reply_markup=back_keyboard(),
        parse_mode="HTML",
    )


async def status_text(uid, u):
    refs = len(u.get("referred_users", []))
    role = "OWNER" if is_owner(uid) else ("ADMIN" if is_admin(uid) else "USER")
    return (
        "📊 <b>YOUR PROFILE</b>\n━━━━━━━━━━━━━━━━━━\n"
        f"👤 Name: {html.escape(u.get('name', 'User'))}\n"
        f"🆔 ID: <code>{uid}</code>\n"
        f"🔗 Username: @{html.escape(u.get('username') or 'not set')}\n"
        f"🛡️ Role: {role}\n💠 Plan: {'UNLIMITED' if has_unlimited(uid, u) else 'FREE'}\n"
        f"⚡ Credits: {credits_label(uid, u)}\n👥 Referrals: {refs}"
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
        await safe_edit(
            q,
            "╭━━〔 ⚡ <b>S I N G L E</b> 〕━━╮\n\n"
            "Send one email address for REAL availability check.\n"
            "✦ ─── ✦ ─── ✦\n"
            "<i>Checks hi2 & telegmail with IG </i>",
            back_keyboard(),
        )
    elif data == "bulk":
        context.user_data["action"] = "bulk"
        await safe_edit(
            q,
            f"╭━━〔 🚀 <b>B U L K</b> 〕━━╮\n\n"
            f"Send up to <b>{BULK_BATCH_SIZE}</b> email addresses, one per line.\n"
            "✦ ─── ✦ ─── ✦\n"
            "<i>Real availability checks • Be patient</i>",
            back_keyboard(),
        )
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
            "Scan the QR and pay, then send screenshot to @obtalkbot for verification."
        )
        await safe_edit(q, payment_text, back_keyboard())
        qr_file_id = s.get("qr_file_id")
        if qr_file_id:
            try:
                await q.message.reply_photo(photo=qr_file_id, caption="💳 <b>FARID · UPI QR</b>", parse_mode="HTML")
            except (NetworkError, TimedOut, BadRequest) as exc:
                log.warning("Could not send payment QR: %s", exc)
    elif data == "panel":
        if not is_staff(uid):
            await safe_edit(q, "⛔ Not authorized.", back_keyboard())
            return
        await safe_edit(
            q,
            f"🛡️ <b>ADMIN PANEL</b>\n\nUsers: {len(DB['users'])}\nRedeem codes: {len(DB['redeem_codes'])}\nAdmins: {len(DB['admins'])}",
            panel_keyboard(),
        )
    elif data in {"gen_code", "add_credits", "grant", "revoke", "userinfo", "broadcast"}:
        if not is_staff(uid):
            await safe_edit(q, "⛔ Not authorized.", back_keyboard())
            return
        context.user_data["action"] = data
        prompts = {
            "gen_code": "Send: <code>CREDITS MAX_CLAIMS</code>",
            "add_credits": "Send: <code>USER_ID AMOUNT</code>",
            "grant": "Send the user ID to grant unlimited access.",
            "revoke": "Send the user ID to revoke unlimited access.",
            "userinfo": "Send a user ID.",
            "broadcast": "Send the broadcast message.",
        }
        await safe_edit(q, f"🛠️ <b>ADMIN ACTION</b>\n\n{prompts[data]}", back_keyboard())
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
        await safe_edit(q, text, back_keyboard())


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    uid = user.id
    u = user_for(uid, user.first_name, user.username)
    text = (msg.text or "").strip()
    action = context.user_data.get("action")

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
            save_db()
            await msg.reply_text(f"✅ Code redeemed! +{item['credits']} credits.\nBalance: {u['credits']}")
        context.user_data.pop("action", None)
        return

    if action in {"single", "bulk"}:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if action == "single":
            lines = lines[:1]
        if len(lines) > BULK_BATCH_SIZE:
            await msg.reply_text(f"⚠️ Limit is {BULK_BATCH_SIZE} entries. Please send a smaller batch.")
            return
        cost = len(lines) * (SINGLE_CHECK_COST if action == "single" else BULK_CHECK_COST)
        if not has_unlimited(uid, u) and u.get("credits", 0) < cost:
            await msg.reply_text(f"❌ Not enough credits. Required: {cost}; balance: {u.get('credits', 0)}.")
            context.user_data.pop("action", None)
            return

        if not has_unlimited(uid, u):
            u["credits"] -= cost
            save_db()

        await msg.reply_text(
            f"🔎 <b>Starting REAL availability check</b>\n"
            f"Entries: {len(lines)}\n"
            f"Please wait — checking hi2.in & telegmail with IG\n",
            parse_mode="HTML",
        )

        results = []
        for entry in lines:
            entry = entry.strip().lower()
            if "@" not in entry:
                results.append(f"〔 × 〕 <code>{html.escape(entry)}</code> → 𝐈𝐍𝐕𝐀𝐋𝐈𝐃 𝐅𝐎𝐑𝐌𝐀𝐓")
                continue
            domain = entry.split("@")[1]
            if domain not in ("hi2.in", "telegmail.com"):
                results.append(f"〔 × 〕 <code>{html.escape(entry)}</code> → 𝐔𝐍𝐒𝐔𝐏𝐏𝐎𝐑𝐓𝐄𝐃 𝐃𝐎𝐌𝐀𝐈𝐍")
                continue

            availability = check_email_availability(entry, domain)

            if availability == "taken":
                results.append(f"〔 ✗ 〕 <code>{html.escape(entry)}</code> → 𝐓𝐀𝐊𝐄𝐍")
            elif availability == "not_taken":
                results.append(f"〔 ✓ 〕 <code>{html.escape(entry)}</code> → 𝐍𝐎𝐓 𝐓𝐀𝐊𝐄𝐍")
            elif availability == "unknown":
                results.append(f"〔 ! 〕 <code>{html.escape(entry)}</code> → 𝐔𝐍𝐊𝐍𝐎𝐖𝐍")
            else:
                results.append(f"〔 × 〕 <code>{html.escape(entry)}</code> → 𝐄𝐑𝐑𝐎𝐑")

            import asyncio
            await asyncio.sleep(1)

        out = ["🧪 <b>REAL AVAILABILITY REPORT</b>", "━━━━━━━━━━━━━━━━━━"]
        out += results
        out += [
            "━━━━━━━━━━━━━━━━━━",
            f"Balance: {credits_label(uid, u)}",
            "",
            "<i>hi2.in & Telegmail with IG registration checked.</i>",
        ]
        await msg.reply_text("\n".join(out), parse_mode="HTML")
        context.user_data.pop("action", None)
        return

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
            elif action in {"grant", "revoke"}:
                target = str(int(text))
                tu = DB["users"].setdefault(
                    target,
                    {"credits": 0, "unlimited": False, "referred_users": [], "name": "User", "joined": utc_now()},
                )
                tu["unlimited"] = action == "grant"
                save_db()
                await msg.reply_text(
                    f"✅ Unlimited access {'granted' if action == 'grant' else 'revoked'} for <code>{target}</code>.",
                    parse_mode="HTML",
                )
            elif action == "userinfo":
                target = str(int(text))
                tu = DB["users"].get(target)
                if not tu:
                    await msg.reply_text("User not found in the database.")
                else:
                    await msg.reply_text(
                        f"👤 <b>User info</b>\nID: <code>{target}</code>\nName: {html.escape(tu.get('name', 'User'))}\n"
                        f"Credits: {tu.get('credits', 0)}\nUnlimited: {bool(tu.get('unlimited'))}",
                        parse_mode="HTML",
                    )
            elif action == "broadcast":
                sent = failed = 0
                await msg.reply_text(f"📢 Broadcasting to {len(DB['users'])} users…")
                for target in list(DB["users"]):
                    try:
                        await context.bot.send_message(
                            int(target),
                            "📢 <b>OBITO ANNOUNCEMENT</b>\n\n" + html.escape(text),
                            parse_mode="HTML",
                        )
                        sent += 1
                    except RetryAfter as exc:
                        import asyncio
                        await asyncio.sleep(float(exc.retry_after) + 0.5)
                        try:
                            await context.bot.send_message(
                                int(target),
                                "📢 <b>OBITO ANNOUNCEMENT</b>\n\n" + html.escape(text),
                                parse_mode="HTML",
                            )
                            sent += 1
                        except Exception:
                            failed += 1
                    except Exception:
                        failed += 1
                await msg.reply_text(f"✅ Broadcast finished.\nSent: {sent}\nFailed: {failed}")
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
    await msg.reply_text("✅ Payment QR saved! Premium users will now see this QR.\nUPI: faridh@fam\nName: FARID")


async def panel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_staff(update.effective_user.id):
        await update.effective_message.reply_text("⛔ Not authorized.")
        return
    await update.effective_message.reply_text("🛡️ <b>ADMIN PANEL</b>", reply_markup=panel_keyboard(), parse_mode="HTML")


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
        # ONLY public commands in the menu — admin commands stay hidden
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
    normal_request = HTTPXRequest(
        connection_pool_size=16,
        connect_timeout=30,
        read_timeout=40,
        write_timeout=30,
        pool_timeout=30,
    )
    polling_request = HTTPXRequest(
        connection_pool_size=4,
        connect_timeout=30,
        read_timeout=50,
        write_timeout=30,
        pool_timeout=30,
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

    # Hidden admin commands — not registered in set_my_commands, but still functional
    app.add_handler(CommandHandler("panel", panel_cmd))
    app.add_handler(CommandHandler("addcredits", addcredits_cmd))
    app.add_handler(CommandHandler("setqr", setqr_cmd))

    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    log.info("Starting long-polling worker")
    app.run_polling(drop_pending_updates=False, allowed_updates=Update.ALL_TYPES, timeout=30)


if __name__ == "__main__":
    main()