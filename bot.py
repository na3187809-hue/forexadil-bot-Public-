import os
import sqlite3
import threading
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN nahi mila. .env file check karein.")

DB_FILE = "bot.db"


# =========================
# KEEP-ALIVE SERVER (for Render free Web Service)
# =========================
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
# KEYBOARDS (INLINE)
# =========================
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎯 Tasks / Ads", callback_data="menu_tasks")],
        [InlineKeyboardButton("👥 Refer & Earn", callback_data="menu_referral")],
        [InlineKeyboardButton("💰 My Balance", callback_data="menu_balance")],
        [InlineKeyboardButton("📊 My Stats", callback_data="action_stats")]
    ]
    return InlineKeyboardMarkup(keyboard)


# =========================
# START COMMAND
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username or "")

    await update.message.reply_text(
        "👋 Welcome to Forex Adil Bot!\n\n"
        "Yahan aap tasks complete karke rewards earn kar sakte hain.\n\n"
        "Neeche menu se option select karein.",
        reply_markup=get_main_keyboard()
    )


# =========================
# CALLBACK HANDLER (INLINE BUTTONS)
# =========================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    # --- MAIN MENU NAVIGATION ---
    if data == "main_menu":
        await query.edit_message_text(
            "🏠 Main Menu\n\nNeeche menu se option select karein.",
            reply_markup=get_main_keyboard()
        )

    # --- TASKS / ADS MENU ---
    elif data == "menu_tasks":
        keyboard = [
            [InlineKeyboardButton("📢 Available Ads", callback_data="task_ads")],
            [InlineKeyboardButton("✅ Complete Task", callback_data="task_complete")],
            [InlineKeyboardButton("📋 My Completed Tasks", callback_data="task_my_completed")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            "🎯 Tasks / Ads\n\nAvailable tasks yahan show honge.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "task_ads":
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_tasks")]]
        await query.edit_message_text(
            "📢 Available Ads\n\nThere are currently no ads available.\n\nNew ads will appear here when they are added.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "task_complete":
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_tasks")]]
        await query.edit_message_text(
            "✅ Complete Task\n\nThere is currently no task available.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "task_my_completed":
        user_data = get_user(user_id)
        completed = user_data[5] if user_data else 0
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_tasks")]]
        await query.edit_message_text(
            f"📋 My Completed Tasks\n\nTasks Completed: {completed}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # --- REFERRAL MENU ---
    elif data == "menu_referral":
        keyboard = [
            [InlineKeyboardButton("🔗 Referral Link", callback_data="ref_link")],
            [InlineKeyboardButton("👥 My Referrals", callback_data="ref_count")],
            [InlineKeyboardButton("💵 Referral Earnings", callback_data="ref_earnings")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            "👥 Refer & Earn",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "ref_link":
        bot_username = context.bot.username
        link = f"https://t.me/{bot_username}?start={user_id}"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_referral")]]
        await query.edit_message_text(
            f"🔗 Your Referral Link\n\n{link}\n\nShare this link with your friends.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "ref_count":
        user_data = get_user(user_id)
        referrals = user_data[2] if user_data else 0
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_referral")]]
        await query.edit_message_text(
            f"👥 My Referrals\n\nTotal Referrals: {referrals}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "ref_earnings":
        user_data = get_user(user_id)
        earnings = user_data[3] if user_data else 0
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_referral")]]
        await query.edit_message_text(
            f"💵 Referral Earnings\n\n${earnings:.2f}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # --- BALANCE MENU ---
    elif data == "menu_balance":
        keyboard = [
            [InlineKeyboardButton("💰 Total Earnings", callback_data="bal_total")],
            [InlineKeyboardButton("⏳ Pending", callback_data="bal_pending")],
            [InlineKeyboardButton("💵 Available Balance", callback_data="bal_available")],
            [InlineKeyboardButton("💸 Withdraw", callback_data="bal_withdraw")],
            [InlineKeyboardButton("📜 Withdrawal History", callback_data="bal_history")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            "💰 My Balance",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "bal_total":
        user_data = get_user(user_id)
        balance = user_data[0] if user_data else 0
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_balance")]]
        await query.edit_message_text(
            f"💰 Total Earnings\n\n${balance:.2f}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "bal_pending":
        user_data = get_user(user_id)
        amount = user_data[1] if user_data else 0
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_balance")]]
        await query.edit_message_text(
            f"⏳ Pending\n\n${amount:.2f}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "bal_available":
        user_data = get_user(user_id)
        amount = user_data[0] if user_data else 0
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_balance")]]
        await query.edit_message_text(
            f"💵 Available Balance\n\n${amount:.2f}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "bal_withdraw":
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_balance")]]
        await query.edit_message_text(
            "💸 Withdraw\n\nWithdrawal system will be available soon.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "bal_history":
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_balance")]]
        await query.edit_message_text(
            "📜 Withdrawal History\n\nNo withdrawals yet.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # --- STATS ACTION ---
    elif data == "action_stats":
        user_data = get_user(user_id)
        if user_data:
            balance, pending_amount, referrals, referral_earnings, ads, tasks = user_data
        else:
            balance = referrals = ads = tasks = 0

        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
        await query.edit_message_text(
            f"📊 My Stats\n\n"
            f"Ads Viewed: {ads}\n"
            f"Tasks Completed: {tasks}\n"
            f"Referrals: {referrals}\n"
            f"Earnings: ${balance:.2f}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# =========================
# RUN BOT
# =========================
def main():
    init_db()

    threading.Thread(target=run_keepalive_server, daemon=True).start()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()