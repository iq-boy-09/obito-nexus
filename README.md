<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f172a,50:312e81,100:06b6d4&height=190&section=header&text=OBITO%20NEXUS&fontSize=52&fontColor=ffffff&fontAlignY=38&desc=Precision%20%E2%80%A2%20Speed%20%E2%80%A2%20Power&descAlignY=62&descSize=18" alt="OBITO NEXUS animated header" width="100%" />

<img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=700&size=20&duration=2800&pause=900&color=22D3EE&center=true&vCenter=true&width=720&lines=REAL+AVAILABILITY+CHECKS;SINGLE+%E2%9A%A1+BULK+%F0%9F%9A%80+WORKFLOWS;CREDITS+%E2%80%A2+REFERRALS+%E2%80%A2+PREMIUM;RENDER-READY+TELEGRAM+WORKER" alt="Animated project description" />

<br />

<a href="https://t.me/f4did"><img src="https://img.shields.io/badge/OWNER-%40f4did-7c3aed?style=for-the-badge&logo=telegram&logoColor=white" alt="Owner @f4did" /></a>
<img src="https://img.shields.io/badge/PLATFORM-TELEGRAM-0ea5e9?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram" />
<img src="https://img.shields.io/badge/DEPLOY-RENDER-46e3b7?style=for-the-badge&logo=render&logoColor=111827" alt="Render" />
<img src="https://img.shields.io/badge/PYTHON-3.10%2B-facc15?style=for-the-badge&logo=python&logoColor=111827" alt="Python 3.10+" />

<br /><br />

<strong>⚡ A neon-styled Telegram automation bot for fast, credit-based email availability checks.</strong>

</div>

<br />

> [!IMPORTANT]
> **Full credit and ownership:** This project is created, owned, and maintained by **[@f4did](https://t.me/f4did)**. If you use, fork, modify, deploy, or redistribute this project, keep this credit visible and link back to `@f4did`.

## ✦ What it does

OBITO NEXUS checks supported email addresses for registration availability and wraps the workflow in a Telegram UI with credits, referrals, redeem codes, premium access, and owner/admin controls.

<div align="center">

| ⚡ Single | 🚀 Bulk | 🎁 Rewards | 🛡️ Control |
|:---:|:---:|:---:|:---:|
| One address per check | Up to 20 addresses | Credits, referrals, codes | Owner/admin panel |

</div>

### Core features

- `/start` and `/help` — launch the main menu
- `/single` — check one address
- `/bulk` — check up to 20 addresses
- Supported domains: `hi2.in` and `telegmail.com`
- Credits, referral bonuses, redeem codes, and premium/unlimited access
- Owner/admin actions for credits, codes, user lookup, QR payments, and broadcasts
- JSON persistence locally or on a Render persistent disk
- Telegram long polling — no public web server or webhook is required

## ◈ Quick start

### Requirements

- Python 3.10+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- Network access to Telegram and the external availability-check services

### Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item env.example .env
```

Set `BOT_TOKEN` in your shell or IDE. PowerShell example:

```powershell
$env:BOT_TOKEN = "replace_with_telegram_bot_token"
$env:OWNER_USER_ID = "123456789"
python bot.py
```

## ◉ Deploy on Render

The included [`render.yaml`](render.yaml) defines a Render **Background Worker** with a 1 GB persistent disk.

1. Push this repository to GitHub.
2. In Render, choose **New → Blueprint**.
3. Connect GitHub and select this repository.
4. Confirm the `obito-nexus` Background Worker.
5. Enter your new BotFather token as the secret `BOT_TOKEN`.
6. Click **Deploy Blueprint**.
7. Open the Render logs and confirm:

   ```text
   OBITO NEXUS online as @your_bot_username
   ```

The production database is stored at `/var/data/obito_db.json` through `DB_FILE`. A persistent disk may require a paid Render service plan; without it, the worker can run but local database state may be lost after a restart.

## ◇ Configuration

| Variable | Required | Purpose |
| --- |:---:| --- |
| `BOT_TOKEN` | **Yes** | Telegram token from BotFather |
| `OWNER_USER_ID` | No | Numeric Telegram ID of the owner |
| `OWNER_USERNAME` | No | Owner username, with or without `@` |
| `SUPPORT_CHAT` | No | Support username, with or without `@` |
| `DB_FILE` | No | JSON database path; defaults to `data/obito_db.json` |
| `LOG_LEVEL` | No | Logging level such as `INFO` or `DEBUG` |

## 🛡️ Owner & admin controls

These commands remain hidden from Telegram's public command menu:

```text
/panel                         Open the admin panel
/addcredits USER_ID AMOUNT     Add credits to a user
/setqr                         Reply to an image to save the premium QR
```

The inline admin panel also supports redeem-code generation, user lookup, unlimited access, broadcasts, and credit management.

## 🔐 Security & responsible use

- Never commit `.env`, a real bot token, or production database contents.
- The local database may contain Telegram user information; use a clean database for a new deployment when appropriate.
- If a real token was ever exposed, revoke it in BotFather and generate a new one before deploying.
- Availability checks call third-party services and may stop working if their APIs change or rate-limit requests.
- Keep the **[@f4did](https://t.me/f4did)** credit intact in every public fork or deployment.

## 🧰 Troubleshooting

| Symptom | Fix |
| --- | --- |
| `Missing BOT_TOKEN environment variable.` | Set `BOT_TOKEN` locally or in Render Environment Variables. |
| Telegram network errors | Check Render logs and confirm the token is valid. |
| Data resets after restart | Confirm the persistent disk and `DB_FILE=/var/data/obito_db.json`. |
| `ModuleNotFoundError` | Run `python -m pip install -r requirements.txt`. |

## ✨ Credits

<div align="center">

### Built with vision by [@f4did](https://t.me/f4did)

<a href="https://t.me/f4did"><img src="https://img.shields.io/badge/ALL%20CREDITS-%40f4did-8b5cf6?style=for-the-badge&logo=telegram&logoColor=white" alt="All credits @f4did" /></a>

**Please preserve this attribution when using or sharing OBITO NEXUS.**

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:06b6d4,50:312e81,100:0f172a&height=110&section=footer" alt="Animated footer" width="100%" />

</div>
