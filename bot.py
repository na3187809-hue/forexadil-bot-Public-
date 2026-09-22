import os
import sqlite3
import threading
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN nahi mila. .env file check karein.")

DB_FILE = "bot.db"


# =========================
# KEEP-ALIVE SERVER (for Render free Web Service)
# =========================
# Render's free plan only works for services that listen on a port.
# This tiny server exists only to satisfy that requirement so the
# bot (which itself uses polling, not a web server) can run for free.

def run_keepalive_server():
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running")

        def log_message(self, format, *args):
            pass

    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()


# =========================
# DATABASE
# =========================

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0,
            pending REAL DEFAULT 0,
            referrals INTEGER DEFAULT 0,
            referral_earnings REAL DEFAULT 0,
            ads_viewed INTEGER DEFAULT 0,
            tasks_completed INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


def add_user(user_id, username):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute(
        "SELECT user_id FROM users WHERE user_id = ?",
        (user_id,)
    )

    if cur.fetchone() is None:
        cur.execute("""
            INSERT INTO users
            (user_id, username)
            VALUES (?, ?)
        """, (user_id, username))

    else:
        cur.execute("""
            UPDATE users
            SET username = ?
            WHERE user_id = ?
        """, (username, user_id))

    conn.commit()
    conn.close()


def get_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        SELECT balance, pending, referrals,
               referral_earnings, ads_viewed,
               tasks_completed
        FROM users
        WHERE user_id = ?
    """, (user_id,))

    result = cur.fetchone()

    conn.close()

    return result


# =========================
# MAIN MENU
# =========================

MAIN_MENU = [
    ["🎯 Tasks / Ads"],
    ["👥 Refer & Earn"],
    ["💰 My Balance"],
    ["📊 My Stats"]
]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    add_user(
        user.id,
        user.username or ""
    )

    keyboard = ReplyKeyboardMarkup(
        MAIN_MENU,
        resize_keyboard=True
    )

    await update.message.reply_text(
        "👋 Welcome to Forex Adil Bot!\n\n"
        "Yahan aap tasks complete karke rewards earn "
        "kar sakte hain.\n\n"
        "Neeche menu se option select karein.",
        reply_markup=keyboard
    )


# =========================
# TASKS / ADS
# =========================

async def tasks_menu(update, context):

    keyboard = [
        ["📢 Available Ads"],
        ["✅ Complete Task"],
        ["📋 My Completed Tasks"],
        ["🔙 Back"]
    ]

    await update.message.reply_text(
        "🎯 Tasks / Ads\n\n"
        "Available tasks yahan show honge.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )
    )


async def available_ads(update, context):

    await update.message.reply_text(
        "📢 Available Ads\n\n"
        "There are currently no ads available.\n\n"
        "New ads will appear here when they are added."
    )


async def complete_task(update, context):

    await update.message.reply_text(
        "✅ Complete Task\n\n"
        "There is currently no task available."
    )


async def completed_tasks(update, context):

    data = get_user(update.effective_user.id)

    completed = data[5] if data else 0

    await update.message.reply_text(
        f"📋 My Completed Tasks\n\n"
        f"Tasks Completed: {completed}"
    )


# =========================
# REFERRAL
# =========================

async def referral_menu(update, context):

    keyboard = [
        ["🔗 Referral Link"],
        ["👥 My Referrals"],
        ["💵 Referral Earnings"],
        ["🔙 Back"]
    ]

    await update.message.reply_text(
        "👥 Refer & Earn",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )
    )


async def referral_link(update, context):

    bot_username = context.bot.username

    link = (
        f"https://t.me/{bot_username}"
        f"?start={update.effective_user.id}"
    )

    await update.message.reply_text(
        "🔗 Your Referral Link\n\n"
        f"{link}\n\n"
        "Share this link with your friends."
    )


async def my_referrals(update, context):

    data = get_user(update.effective_user.id)

    referrals = data[2] if data else 0

    await update.message.reply_text(
        f"👥 My Referrals\n\n"
        f"Total Referrals: {referrals}"
    )


async def referral_earnings(update, context):

    data = get_user(update.effective_user.id)

    earnings = data[3] if data else 0

    await update.message.reply_text(
        f"💵 Referral Earnings\n\n"
        f"${earnings:.2f}"
    )


# =========================
# BALANCE
# =========================

async def balance_menu(update, context):

    keyboard = [
        ["💰 Total Earnings"],
        ["⏳ Pending"],
        ["💵 Available Balance"],
        ["💸 Withdraw"],
        ["📜 Withdrawal History"],
        ["🔙 Back"]
    ]

    await update.message.reply_text(
        "💰 My Balance",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )
    )


async def total_earnings(update, context):

    data = get_user(update.effective_user.id)

    balance = data[0] if data else 0

    await update.message.reply_text(
        f"💰 Total Earnings\n\n"
        f"${balance:.2f}"
    )


async def pending(update, context):

    data = get_user(update.effective_user.id)

    amount = data[1] if data else 0

    await update.message.reply_text(
        f"⏳ Pending\n\n"
        f"${amount:.2f}"
    )


async def available_balance(update, context):

    data = get_user(update.effective_user.id)

    amount = data[0] if data else 0

    await update.message.reply_text(
        f"💵 Available Balance\n\n"
        f"${amount:.2f}"
    )


async def withdraw(update, context):

    await update.message.reply_text(
        "💸 Withdraw\n\n"
        "Withdrawal system will be available soon."
    )


async def withdrawal_history(update, context):

    await update.message.reply_text(
        "📜 Withdrawal History\n\n"
        "No withdrawals yet."
    )


# =========================
# STATS
# =========================

async def stats(update, context):

    data = get_user(update.effective_user.id)

    if data:
        balance, pending_amount, referrals, referral_earnings, ads, tasks = data
    else:
        balance = 0
        referrals = 0
        ads = 0
        tasks = 0

    await update.message.reply_text(
        "📊 My Stats\n\n"
        f"Ads Viewed: {ads}\n"
        f"Tasks Completed: {tasks}\n"
        f"Referrals: {referrals}\n"
        f"Earnings: ${balance:.2f}"
    )


# =========================
# MESSAGE HANDLER
# =========================

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if text == "🎯 Tasks / Ads":
        await tasks_menu(update, context)

    elif text == "📢 Available Ads":
        await available_ads(update, context)

    elif text == "✅ Complete Task":
        await complete_task(update, context)

    elif text == "📋 My Completed Tasks":
        await completed_tasks(update, context)

    elif text == "👥 Refer & Earn":
        await referral_menu(update, context)

    elif text == "🔗 Referral Link":
        await referral_link(update, context)

    elif text == "👥 My Referrals":
        await my_referrals(update, context)

    elif text == "💵 Referral Earnings":
        await referral_earnings(update, context)

    elif text == "💰 My Balance":
        await balance_menu(update, context)

    elif text == "💰 Total Earnings":
        await total_earnings(update, context)

    elif text == "⏳ Pending":
        await pending(update, context)

    elif text == "💵 Available Balance":
        await available_balance(update, context)

    elif text == "💸 Withdraw":
        await withdraw(update, context)

    elif text == "📜 Withdrawal History":
        await withdrawal_history(update, context)

    elif text == "📊 My Stats":
        await stats(update, context)

    elif text == "🔙 Back":

        keyboard = ReplyKeyboardMarkup(
            MAIN_MENU,
            resize_keyboard=True
        )

        await update.message.reply_text(
            "🏠 Main Menu",
            reply_markup=keyboard
        )

    else:

        await update.message.reply_text(
            "Please menu se koi option select karein."
        )


# =========================
# RUN BOT
# =========================

def main():

    init_db()

    threading.Thread(target=run_keepalive_server, daemon=True).start()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            message_handler
        )
    )

    print("Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()