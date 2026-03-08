#!/usr/bin/env python3
"""
🎁 GIFT CARD & RECHARGE BOT v11.0.0
Complete Telegram bot for selling gift cards at discounted prices.
Author: Gift Card Bot Team
"""

# ─────────────────────────────────────────────────────────────
# FIX: CREATE LOGS DIRECTORY FIRST - BEFORE ANY IMPORTS
# ─────────────────────────────────────────────────────────────
import os
import sys
from pathlib import Path

# Create logs directory safely
LOG_DIR = Path("logs")
try:
    LOG_DIR.mkdir(exist_ok=True, parents=True)
    print(f"✅ Logs directory created: {LOG_DIR.absolute()}")
except Exception as e:
    print(f"⚠️ Could not create logs directory: {e}")
    LOG_DIR = Path(".")  # Fallback to current directory

# Now safe to import other modules
import re
import csv
import json
import time
import logging
import sqlite3
import asyncio
import hashlib
import datetime
import threading
from io import StringIO
from queue import Queue
from functools import wraps
from datetime import date, timedelta

try:
    import qrcode
    from PIL import Image
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    BotCommand, InputFile, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters, ContextTypes
)
from telegram.constants import ParseMode, ChatAction
from telegram.error import TelegramError

# ─────────────────────────────────────────────────────────────
# LOGGING SETUP - NOW SAFE
# ─────────────────────────────────────────────────────────────
log_file = LOG_DIR / "bot.log"
try:
    file_handler = logging.FileHandler(str(log_file), encoding='utf-8')
    print(f"✅ Log file created: {log_file}")
    handlers = [logging.StreamHandler(), file_handler]
except Exception as e:
    print(f"⚠️ Could not create log file, using console only: {e}")
    handlers = [logging.StreamHandler()]

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=handlers
)
logger = logging.getLogger(__name__)
logger.info("🚀 Logging initialized successfully!")

# ─────────────────────────────────────────────────────────────
# ENVIRONMENT VARIABLES
# ─────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN environment variable not set!")

try:
    ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
    if ADMIN_ID == 0:
        logger.warning("⚠️ ADMIN_ID not set - admin commands disabled")
except ValueError:
    ADMIN_ID = 0
    logger.warning("⚠️ Invalid ADMIN_ID - admin commands disabled")

UPI_ID = os.environ.get("UPI_ID", "your-upi@bank")
MAIN_CHANNEL = os.environ.get("MAIN_CHANNEL", "@gift_card_main")

try:
    ADMIN_CHANNEL_ID = int(os.environ.get("ADMIN_CHANNEL_ID", "0"))
except ValueError:
    ADMIN_CHANNEL_ID = 0
    logger.warning("⚠️ Invalid ADMIN_CHANNEL_ID - admin notifications disabled")

# Database path with directory creation
DATABASE_PATH = os.environ.get("DATABASE_PATH", "bot_database.db")
db_dir = os.path.dirname(DATABASE_PATH)
if db_dir and not os.path.exists(db_dir):
    try:
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"✅ Created database directory: {db_dir}")
    except Exception as e:
        logger.error(f"❌ Cannot create database directory: {e}")

QR_CODE_PATH = os.environ.get("QR_CODE_PATH", "qr.jpg")

# ─────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────
MIN_RECHARGE = 10
MAX_RECHARGE = 10000
FEE_PERCENT = 20
FEE_THRESHOLD = 120
REFERRAL_BONUS = 2
WELCOME_BONUS = 5
POSTS_PER_DAY = 12
POST_INTERVAL = 7200

DAILY_REWARDS = {
    1: 5, 2: 8, 3: 10, 4: 12, 5: 15,
    6: 18, 7: 25, 10: 40, 15: 60, 30: 100
}

COUPONS_CONFIG = {
    "WELCOME10": {"discount": 10, "type": "percentage", "min": 100, "uses": 1},
    "SAVE20":    {"discount": 20, "type": "fixed",      "min": 200, "uses": 1},
    "FIRST50":   {"discount": 50, "type": "fixed",      "min": 500, "uses": 1},
    "DIWALI22":  {"discount": 22, "type": "percentage", "min": 200, "uses": 100},
    "HOLI15":    {"discount": 15, "type": "percentage", "min": 150, "uses": 100},
    "FLASH50":   {"discount": 50, "type": "percentage", "min": 500, "uses": 50},
}

BULK_DISCOUNTS = {1: 0, 3: 3, 5: 5, 10: 10, 25: 15, 50: 20}

AMOUNT_BUTTONS = [
    [10, 20, 30, 50],
    [120, 150, 200, 300],
    [400, 500, 1000, 2000],
    [5000, 10000]
]

GIFT_CARDS = {
    "amazon":     {"name": "AMAZON",     "emoji": "🟦", "full_emoji": "🟦🛒", "popular": True,  "trending": True},
    "flipkart":   {"name": "FLIPKART",   "emoji": "📦", "full_emoji": "📦🛍️", "popular": True,  "trending": True},
    "playstore":  {"name": "PLAY STORE", "emoji": "🟩", "full_emoji": "🟩🎮", "popular": True,  "trending": False},
    "bookmyshow": {"name": "BOOKMYSHOW", "emoji": "🎟️", "full_emoji": "🎟️🎬", "popular": True,  "trending": False},
    "myntra":     {"name": "MYNTRA",     "emoji": "🛍️", "full_emoji": "🛍️👗", "popular": True,  "trending": True},
    "zomato":     {"name": "ZOMATO",     "emoji": "🍕", "full_emoji": "🍕🍔", "popular": True,  "trending": False},
    "bigbasket":  {"name": "BIG BASKET", "emoji": "🛒", "full_emoji": "🛒🥬", "popular": False, "trending": False},
}

PRICES = {500: 100, 1000: 200, 2000: 400, 5000: 1000}
DENOMINATIONS = [500, 1000, 2000, 5000]

LANGUAGES = {
    "en": "🇬🇧 English",
    "hi": "🇮🇳 हिन्दी",
    "ta": "🇮🇳 தமிழ்",
    "te": "🇮🇳 తెలుగు",
    "bn": "🇮🇳 বাংলা",
    "gu": "🇮🇳 ગુજરાતી",
    "mr": "🇮🇳 मराठी",
}

# ─────────────────────────────────────────────────────────────
# CONVERSATION STATES
# ─────────────────────────────────────────────────────────────
(
    STATE_SCREENSHOT,
    STATE_UTR,
    STATE_EMAIL,
    STATE_SUPPORT,
    STATE_COUPON,
    STATE_BULK_COUNT,
    STATE_GIFT_EMAIL,
    STATE_PRICE_ALERT,
    STATE_AMOUNT,
) = range(9)

# ─────────────────────────────────────────────────────────────
# RATE LIMITER
# ─────────────────────────────────────────────────────────────
class RateLimiter:
    def __init__(self, max_requests=30, window=60):
        self.max_requests = max_requests
        self.window = window
        self.requests = {}
        self.lock = threading.Lock()

    def is_allowed(self, user_id):
        with self.lock:
            now = time.time()
            user_requests = self.requests.get(user_id, [])
            user_requests = [r for r in user_requests if now - r < self.window]
            if len(user_requests) >= self.max_requests:
                return False
            user_requests.append(now)
            self.requests[user_id] = user_requests
            return True

rate_limiter = RateLimiter()

# ─────────────────────────────────────────────────────────────
# DATABASE MANAGER
# ─────────────────────────────────────────────────────────────
class DatabaseManager:
    def __init__(self, db_path, pool_size=10):
        self.db_path = db_path
        self.pool = Queue(maxsize=pool_size)
        self.lock = threading.Lock()
        
        # Test database connection first
        try:
            test_conn = sqlite3.connect(db_path, timeout=30)
            test_conn.close()
            logger.info(f"✅ Database connection test passed: {db_path}")
        except Exception as e:
            logger.error(f"❌ Database connection test failed: {e}")
            raise
        
        for _ in range(pool_size):
            try:
                conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA foreign_keys=ON")
                self.pool.put(conn)
            except Exception as e:
                logger.error(f"❌ Failed to create database connection: {e}")
        
        self._init_db()

    def get_conn(self):
        return self.pool.get(timeout=10)

    def return_conn(self, conn):
        self.pool.put(conn)

    def execute(self, query, params=(), fetchone=False, fetchall=False, commit=False):
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute(query, params)
            if commit:
                conn.commit()
                return cur.lastrowid
            if fetchone:
                return cur.fetchone()
            if fetchall:
                return cur.fetchall()
        except Exception as e:
            conn.rollback()
            logger.error(f"DB Error: {e} | Query: {query} | Params: {params}")
            raise
        finally:
            self.return_conn(conn)

    def _init_db(self):
        conn = self.get_conn()
        try:
            c = conn.cursor()
            c.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    balance INTEGER DEFAULT 0,
                    total_purchases INTEGER DEFAULT 0,
                    total_referrals INTEGER DEFAULT 0,
                    referral_code TEXT UNIQUE,
                    referred_by INTEGER,
                    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    language TEXT DEFAULT 'en',
                    streak INTEGER DEFAULT 0,
                    last_claim DATE,
                    FOREIGN KEY (referred_by) REFERENCES users(user_id)
                );

                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    transaction_id TEXT UNIQUE,
                    amount INTEGER,
                    type TEXT,
                    status TEXT DEFAULT 'completed',
                    utr TEXT UNIQUE,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );

                CREATE TABLE IF NOT EXISTS purchases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    order_id TEXT UNIQUE,
                    card_name TEXT,
                    card_value INTEGER,
                    price INTEGER,
                    email TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );

                CREATE TABLE IF NOT EXISTS verifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount INTEGER,
                    fee INTEGER,
                    final_amount INTEGER,
                    utr TEXT UNIQUE,
                    screenshot TEXT,
                    status TEXT DEFAULT 'pending',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );

                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER,
                    referred_id INTEGER UNIQUE,
                    bonus_amount INTEGER DEFAULT 2,
                    status TEXT DEFAULT 'pending',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (referrer_id) REFERENCES users(user_id),
                    FOREIGN KEY (referred_id) REFERENCES users(user_id)
                );

                CREATE TABLE IF NOT EXISTS support (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message TEXT,
                    status TEXT DEFAULT 'open',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );

                CREATE TABLE IF NOT EXISTS daily_rewards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    claim_date DATE,
                    streak INTEGER DEFAULT 1,
                    amount INTEGER,
                    UNIQUE(user_id, claim_date),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );

                CREATE TABLE IF NOT EXISTS coupons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE,
                    user_id INTEGER,
                    discount_type TEXT,
                    discount_value INTEGER,
                    min_amount INTEGER,
                    used INTEGER DEFAULT 0,
                    expires TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );

                CREATE TABLE IF NOT EXISTS price_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    card_name TEXT,
                    target_price INTEGER,
                    current_price INTEGER,
                    active INTEGER DEFAULT 1,
                    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );

                CREATE TABLE IF NOT EXISTS admin_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    action TEXT,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            logger.info("✅ Database ready")
        finally:
            self.return_conn(conn)

    # ── USER METHODS ──────────────────────────────────────────
    def get_user(self, user_id):
        return self.execute("SELECT * FROM users WHERE user_id=?", (user_id,), fetchone=True)

    def create_user(self, user_id, username, first_name, referred_by=None):
        ref_code = hashlib.md5(str(user_id).encode()).hexdigest()[:8].upper()
        self.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name, referral_code, referred_by) VALUES (?,?,?,?,?)",
            (user_id, username, first_name, ref_code, referred_by), commit=True
        )
        if referred_by:
            self.execute(
                "INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?,?)",
                (referred_by, user_id), commit=True
            )

    def update_user(self, user_id, **kwargs):
        for key, val in kwargs.items():
            self.execute(f"UPDATE users SET {key}=?, last_active=CURRENT_TIMESTAMP WHERE user_id=?",
                         (val, user_id), commit=True)

    def get_balance(self, user_id):
        row = self.execute("SELECT balance FROM users WHERE user_id=?", (user_id,), fetchone=True)
        return row["balance"] if row else 0

    def update_balance(self, user_id, amount, tx_type="credit", utr=None):
        sign = 1 if tx_type in ("credit", "bonus", "referral") else -1
        self.execute("UPDATE users SET balance=balance+? WHERE user_id=?",
                     (sign * amount, user_id), commit=True)
        tx_id = hashlib.md5(f"{user_id}{time.time()}".encode()).hexdigest()[:12].upper()
        self.execute(
            "INSERT OR IGNORE INTO transactions (user_id, transaction_id, amount, type, utr) VALUES (?,?,?,?,?)",
            (user_id, tx_id, amount, tx_type, utr), commit=True
        )

    # ── VERIFICATION METHODS ──────────────────────────────────
    def create_verification(self, user_id, amount, fee, final_amount, utr, screenshot):
        self.execute(
            "INSERT INTO verifications (user_id, amount, fee, final_amount, utr, screenshot) VALUES (?,?,?,?,?,?)",
            (user_id, amount, fee, final_amount, utr, screenshot), commit=True
        )

    def get_verification(self, ver_id):
        return self.execute("SELECT * FROM verifications WHERE id=?", (ver_id,), fetchone=True)

    def update_verification_status(self, ver_id, status):
        self.execute("UPDATE verifications SET status=? WHERE id=?", (status, ver_id), commit=True)

    def is_utr_duplicate(self, utr):
        row = self.execute("SELECT id FROM verifications WHERE utr=?", (utr,), fetchone=True)
        return row is not None

    # ── PURCHASE METHODS ──────────────────────────────────────
    def create_purchase(self, user_id, card_name, card_value, price, email):
        order_id = f"ORD{int(time.time())}{user_id}"
        self.execute(
            "INSERT INTO purchases (user_id, order_id, card_name, card_value, price, email) VALUES (?,?,?,?,?,?)",
            (user_id, order_id, card_name, card_value, price, email), commit=True
        )
        self.execute("UPDATE users SET total_purchases=total_purchases+1 WHERE user_id=?",
                     (user_id,), commit=True)
        return order_id

    def get_purchases(self, user_id, limit=10):
        return self.execute(
            "SELECT * FROM purchases WHERE user_id=? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit), fetchall=True
        )

    # ── REFERRAL METHODS ──────────────────────────────────────
    def process_referral(self, referrer_id):
        self.execute("UPDATE users SET total_referrals=total_referrals+1 WHERE user_id=?",
                     (referrer_id,), commit=True)
        self.update_balance(referrer_id, REFERRAL_BONUS, "referral")

    def get_referral_stats(self, user_id):
        total = self.execute("SELECT COUNT(*) as c FROM referrals WHERE referrer_id=?",
                             (user_id,), fetchone=True)
        return total["c"] if total else 0

    # ── SUPPORT METHODS ───────────────────────────────────────
    def create_support_ticket(self, user_id, message):
        return self.execute(
            "INSERT INTO support (user_id, message) VALUES (?,?)",
            (user_id, message), commit=True
        )

    # ── DAILY REWARD METHODS ──────────────────────────────────
    def claim_daily_reward(self, user_id):
        today = date.today()
        user = self.get_user(user_id)
        if not user:
            return None, "User not found"

        last_claim = user["last_claim"]
        streak = user["streak"] or 0

        if last_claim:
            last_date = datetime.datetime.strptime(str(last_claim), "%Y-%m-%d").date()
            if last_date == today:
                return None, "already_claimed"
            elif last_date == today - timedelta(days=1):
                streak += 1
            else:
                streak = 1
        else:
            streak = 1

        # Find reward amount
        reward = 5
        for day in sorted(DAILY_REWARDS.keys(), reverse=True):
            if streak >= day:
                reward = DAILY_REWARDS[day]
                break

        try:
            self.execute(
                "INSERT INTO daily_rewards (user_id, claim_date, streak, amount) VALUES (?,?,?,?)",
                (user_id, today, streak, reward), commit=True
            )
            self.execute("UPDATE users SET streak=?, last_claim=? WHERE user_id=?",
                         (streak, today, user_id), commit=True)
            self.update_balance(user_id, reward, "bonus")
            return reward, streak
        except sqlite3.IntegrityError:
            return None, "already_claimed"

    # ── COUPON METHODS ────────────────────────────────────────
    def validate_coupon(self, code, user_id, amount):
        code = code.upper().strip()
        if code in COUPONS_CONFIG:
            cfg = COUPONS_CONFIG[code]
            if amount < cfg["min"]:
                return None, f"Minimum purchase ₹{cfg['min']} required"
            # Check user usage
            used = self.execute(
                "SELECT COUNT(*) as c FROM coupons WHERE code=? AND user_id=?",
                (code, user_id), fetchone=True
            )
            if used and used["c"] >= cfg.get("uses", 1):
                return None, "Coupon already used"
            return cfg, None
        return None, "Invalid coupon code"

    def use_coupon(self, code, user_id):
        self.execute(
            "INSERT OR IGNORE INTO coupons (code, user_id, discount_type, discount_value, min_amount, used) VALUES (?,?,?,?,?,1)",
            (code, user_id, "used", 0, 0), commit=True
        )

    # ── PRICE ALERT METHODS ───────────────────────────────────
    def add_price_alert(self, user_id, card_name, target_price, current_price):
        self.execute(
            "INSERT INTO price_alerts (user_id, card_name, target_price, current_price) VALUES (?,?,?,?)",
            (user_id, card_name, target_price, current_price), commit=True
        )

    def get_active_alerts(self, user_id):
        return self.execute(
            "SELECT * FROM price_alerts WHERE user_id=? AND active=1",
            (user_id,), fetchall=True
        )

    # ── STATISTICS METHODS ────────────────────────────────────
    def get_statistics(self):
        total_users = self.execute("SELECT COUNT(*) as c FROM users", fetchone=True)["c"]
        total_revenue = self.execute("SELECT SUM(price) as s FROM purchases", fetchone=True)["s"] or 0
        total_purchases = self.execute("SELECT COUNT(*) as c FROM purchases", fetchone=True)["c"]
        pending_verif = self.execute("SELECT COUNT(*) as c FROM verifications WHERE status='pending'", fetchone=True)["c"]
        today_users = self.execute(
            "SELECT COUNT(*) as c FROM users WHERE DATE(join_date)=DATE('now')", fetchone=True
        )["c"]
        return {
            "total_users": total_users,
            "total_revenue": total_revenue,
            "total_purchases": total_purchases,
            "pending_verifications": pending_verif,
            "today_new_users": today_users,
        }

    def log_admin_action(self, admin_id, action, details):
        self.execute(
            "INSERT INTO admin_logs (admin_id, action, details) VALUES (?,?,?)",
            (admin_id, action, details), commit=True
        )

    def export_users_csv(self):
        rows = self.execute("SELECT * FROM users ORDER BY join_date DESC", fetchall=True)
        output = StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))
        return output.getvalue()

    def get_all_user_ids(self):
        rows = self.execute("SELECT user_id FROM users", fetchall=True)
        return [r["user_id"] for r in rows] if rows else []


# ─────────────────────────────────────────────────────────────
# INITIALIZE DATABASE
# ─────────────────────────────────────────────────────────────
db = DatabaseManager(DATABASE_PATH)

# ─────────────────────────────────────────────────────────────
# UI / UX COMPONENTS
# ─────────────────────────────────────────────────────────────
class EnhancedUI:
    @staticmethod
    def fancy_header(title, subtitle=None):
        line = "═" * (len(title) + 4)
        header = f"╔{line}╗\n║  {title}  ║\n╚{line}╝"
        if subtitle:
            header += f"\n\n{subtitle}"
        return header

    @staticmethod
    def progress_bar(current, total, length=10):
        filled = int(length * current / total) if total else 0
        bar = "█" * filled + "░" * (length - filled)
        percent = int(100 * current / total) if total else 0
        return f"[{bar}] {percent}%"

    @staticmethod
    def user_badge(total_purchases):
        if total_purchases >= 50:
            return "👑 VIP ELITE"
        elif total_purchases >= 20:
            return "💎 DIAMOND"
        elif total_purchases >= 10:
            return "🥇 GOLD"
        elif total_purchases >= 5:
            return "⭐ SILVER"
        elif total_purchases >= 1:
            return "🥉 BRONZE"
        return "🆕 NEW"

    @staticmethod
    def format_currency(amount):
        return f"₹{amount:,}"

    @staticmethod
    def separator():
        return "─" * 30


ui = EnhancedUI()


# ─────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────
def calculate_fee(amount):
    if amount < FEE_THRESHOLD:
        fee = int(amount * FEE_PERCENT / 100)
        return fee, amount - fee
    return 0, amount


def calculate_bulk_discount(quantity, price):
    if quantity >= 50:   discount = BULK_DISCOUNTS[50]
    elif quantity >= 25: discount = BULK_DISCOUNTS[25]
    elif quantity >= 10: discount = BULK_DISCOUNTS[10]
    elif quantity >= 5:  discount = BULK_DISCOUNTS[5]
    elif quantity >= 3:  discount = BULK_DISCOUNTS[3]
    else:                discount = 0
    total = price * quantity
    discount_amount = int(total * discount / 100)
    return {
        "quantity": quantity, "total": total, "discount": discount,
        "discount_amount": discount_amount, "final": total - discount_amount
    }


def validate_email(email):
    return bool(re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email))


def validate_utr(utr):
    return 12 <= len(utr) <= 22 and utr.isalnum()


def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id != ADMIN_ID:
            await update.message.reply_text("❌ Admin access required.")
            return
        return await func(update, context)
    return wrapper


async def check_membership(bot, user_id):
    try:
        member = await bot.get_chat_member(MAIN_CHANNEL, user_id)
        return member.status not in ("left", "kicked", "banned")
    except Exception:
        return True  # If channel check fails, allow


async def show_loading(update, message="Loading", duration=1.5):
    frames = ["🎁", "🎀", "✨", "⭐", "🌟", "💫", "⚡", "💎"]
    msg = await update.effective_message.reply_text(f"{frames[0]} {message}...")
    for i in range(1, 5):
        await asyncio.sleep(duration / 5)
        try:
            await msg.edit_text(f"{frames[i % len(frames)]} {message}{'.' * (i % 3 + 1)}")
        except Exception:
            pass
    return msg


def generate_qr(upi_id, amount):
    """Generate UPI QR code safely"""
    if not QR_AVAILABLE:
        return None
    try:
        upi_url = f"upi://pay?pa={upi_id}&pn=GiftCardBot&am={amount}&cu=INR"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(upi_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        path = f"/tmp/qr_{amount}.png"
        img.save(path)
        return path
    except Exception as e:
        logger.warning(f"QR generation failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# KEYBOARD BUILDERS
# ─────────────────────────────────────────────────────────────
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 GIFT CARDS", callback_data="giftcard"),
         InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")],
        [InlineKeyboardButton("👛 MY WALLET", callback_data="wallet"),
         InlineKeyboardButton("👥 REFERRAL", callback_data="referral")],
        [InlineKeyboardButton("📅 DAILY REWARD", callback_data="daily"),
         InlineKeyboardButton("🏷️ COUPONS", callback_data="coupon")],
        [InlineKeyboardButton("📦 BULK PURCHASE", callback_data="bulk"),
         InlineKeyboardButton("🎁 SEND GIFT", callback_data="gift")],
        [InlineKeyboardButton("🔔 PRICE ALERT", callback_data="alert"),
         InlineKeyboardButton("🌐 LANGUAGE", callback_data="language")],
        [InlineKeyboardButton("🆘 SUPPORT", callback_data="support")],
    ])


def gift_cards_keyboard():
    buttons = []
    row = []
    for card_id, card in GIFT_CARDS.items():
        label = f"{card['emoji']} {card['name']}"
        if card.get("trending"):
            label += " 🔥"
        row.append(InlineKeyboardButton(label, callback_data=f"card_{card_id}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def denominations_keyboard(card_id):
    buttons = []
    row = []
    for denom in DENOMINATIONS:
        price = PRICES[denom]
        original = denom
        discount = int((original - price) / original * 100)
        row.append(InlineKeyboardButton(
            f"₹{denom} @ ₹{price} ({discount}% OFF)",
            callback_data=f"buy_{card_id}_{denom}"
        ))
        if len(row) == 1:
            buttons.append(row)
            row = []
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="giftcard")])
    return InlineKeyboardMarkup(buttons)


def amount_keyboard():
    buttons = []
    for row_amounts in AMOUNT_BUTTONS:
        row = [InlineKeyboardButton(f"₹{a}", callback_data=f"amount_{a}") for a in row_amounts]
        buttons.append(row)
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def language_keyboard():
    buttons = []
    row = []
    for code, name in LANGUAGES.items():
        row.append(InlineKeyboardButton(name, callback_data=f"lang_{code}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


# ─────────────────────────────────────────────────────────────
# CHANNEL VERIFICATION MESSAGE
# ─────────────────────────────────────────────────────────────
async def show_join_channel(update):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{MAIN_CHANNEL.lstrip('@')}")],
        [InlineKeyboardButton("✅ I Joined!", callback_data="verify")],
    ])
    text = (
        f"🔒 *Access Required!*\n\n"
        f"To use this bot, you must join our channel:\n"
        f"📢 {MAIN_CHANNEL}\n\n"
        f"After joining, click *I Joined!* ✅"
    )
    await update.effective_message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)


# ─────────────────────────────────────────────────────────────
# /START COMMAND
# ─────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    if not rate_limiter.is_allowed(user.id):
        await update.message.reply_text("⏳ Please slow down! Try again in a minute.")
        return

    # React with wave
    try:
        await update.message.set_reaction("👋")
    except Exception:
        pass

    # Parse referral code
    referred_by = None
    if context.args:
        ref_code = context.args[0]
        ref_user = db.execute("SELECT user_id FROM users WHERE referral_code=?", (ref_code,), fetchone=True)
        if ref_user and ref_user["user_id"] != user.id:
            referred_by = ref_user["user_id"]

    # Create or get user
    existing = db.get_user(user.id)
    is_new = existing is None

    db.create_user(user.id, user.username or "", user.first_name or "User", referred_by)

    if is_new:
        db.update_balance(user.id, WELCOME_BONUS, "bonus")
        if referred_by:
            db.process_referral(referred_by)
            try:
                await context.bot.send_message(
                    chat_id=referred_by,
                    text=f"🎉 *Referral Bonus!*\n\nSomeone joined using your link!\nYou earned ₹{REFERRAL_BONUS}! 💰",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception:
                pass

    # Check channel membership
    is_member = await check_membership(context.bot, user.id)
    if not is_member:
        await show_join_channel(update)
        return

    db_user = db.get_user(user.id)
    balance = db_user["balance"] if db_user else 0
    purchases = db_user["total_purchases"] if db_user else 0
    badge = ui.user_badge(purchases)
    ref_count = db.get_referral_stats(user.id)

    loading_msg = await show_loading(update, "Loading your dashboard")

    welcome_text = (
        f"🎁 *GIFT CARD & RECHARGE BOT*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{'🆕 Welcome! You got ₹' + str(WELCOME_BONUS) + ' bonus!' if is_new else '👋 Welcome back!'}\n\n"
        f"👤 *{user.first_name}* | {badge}\n"
        f"💰 Balance: *₹{balance:,}*\n"
        f"🛒 Purchases: *{purchases}*\n"
        f"👥 Referrals: *{ref_count}*\n\n"
        f"🔥 Get gift cards at up to *80% OFF!*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Choose an option below 👇"
    )

    try:
        await loading_msg.edit_text(welcome_text, reply_markup=main_menu_keyboard(), parse_mode=ParseMode.MARKDOWN)
    except Exception:
        await update.message.reply_text(welcome_text, reply_markup=main_menu_keyboard(), parse_mode=ParseMode.MARKDOWN)


# ─────────────────────────────────────────────────────────────
# CANCEL COMMAND
# ─────────────────────────────────────────────────────────────
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "❌ *Action cancelled.*\n\nUse /start to return to main menu.",
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────
# BUTTON HANDLER (main dispatcher)
# ─────────────────────────────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = update.effective_user

    if not rate_limiter.is_allowed(user.id):
        await query.answer("⏳ Too many requests! Wait a moment.", show_alert=True)
        return

    # Channel check for most actions (skip for verify, main_menu)
    if data not in ("verify", "main_menu"):
        is_member = await check_membership(context.bot, user.id)
        if not is_member:
            await show_join_channel(update)
            return

    db.update_user(user.id, last_active=datetime.datetime.now())
    db_user = db.get_user(user.id)

    # ── VERIFY ──────────────────────────────────────────────
    if data == "verify":
        is_member = await check_membership(context.bot, user.id)
        if is_member:
            await query.edit_message_text(
                "✅ *Verified!* Welcome to Gift Card Bot!\n\nUse /start to continue.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.answer("❌ You haven't joined the channel yet!", show_alert=True)

    # ── MAIN MENU ────────────────────────────────────────────
    elif data == "main_menu":
        balance = db_user["balance"] if db_user else 0
        purchases = db_user["total_purchases"] if db_user else 0
        badge = ui.user_badge(purchases)
        text = (
            f"🎁 *GIFT CARD & RECHARGE BOT*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *{user.first_name}* | {badge}\n"
            f"💰 Balance: *₹{balance:,}*\n\n"
            f"🔥 Get gift cards at up to *80% OFF!*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Choose an option below 👇"
        )
        await query.edit_message_text(text, reply_markup=main_menu_keyboard(), parse_mode=ParseMode.MARKDOWN)

    # ── GIFT CARDS ───────────────────────────────────────────
    elif data == "giftcard":
        text = (
            "🎁 *GIFT CARDS*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔥 = Trending | Up to *80% OFF*!\n\n"
            "Select a brand to view deals:"
        )
        await query.edit_message_text(text, reply_markup=gift_cards_keyboard(), parse_mode=ParseMode.MARKDOWN)

    # ── SPECIFIC CARD ─────────────────────────────────────────
    elif data.startswith("card_"):
        card_id = data[5:]
        card = GIFT_CARDS.get(card_id)
        if not card:
            await query.answer("❌ Card not found", show_alert=True)
            return
        trending = "🔥 TRENDING" if card.get("trending") else ""
        popular = "⭐ POPULAR" if card.get("popular") else ""
        tags = " | ".join(filter(None, [trending, popular]))
        text = (
            f"{card['full_emoji']} *{card['name']} GIFT CARD*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{'🏷️ ' + tags if tags else ''}\n\n"
            f"💰 *Available Denominations:*\n"
        )
        for denom in DENOMINATIONS:
            price = PRICES[denom]
            disc = int((denom - price) / denom * 100)
            text += f"  • ₹{denom:,} card → *₹{price}* ({disc}% OFF)\n"
        text += f"\n⚡ Instant delivery to your email!\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        await query.edit_message_text(text, reply_markup=denominations_keyboard(card_id), parse_mode=ParseMode.MARKDOWN)

    # ── BUY CARD → triggers email conv ────────────────────────
    elif data.startswith("buy_"):
        parts = data.split("_")
        card_id = parts[1]
        denom = int(parts[2])
        price = PRICES.get(denom, 0)
        balance = db_user["balance"] if db_user else 0

        context.user_data["purchase"] = {
            "card_id": card_id,
            "card_name": GIFT_CARDS[card_id]["name"],
            "denom": denom,
            "price": price,
        }

        if balance < price:
            shortfall = price - balance
            await query.edit_message_text(
                f"❌ *Insufficient Balance!*\n\n"
                f"Card Price: ₹{price:,}\n"
                f"Your Balance: ₹{balance:,}\n"
                f"Shortfall: ₹{shortfall:,}\n\n"
                f"Please add money first! 💰",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💰 Add Money", callback_data="topup")],
                    [InlineKeyboardButton("🔙 Back", callback_data=f"card_{card_id}")],
                ]),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        await query.edit_message_text(
            f"✅ *Confirm Purchase*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎁 Card: *{GIFT_CARDS[card_id]['name']}* ₹{denom:,}\n"
            f"💰 Price: *₹{price}*\n"
            f"👛 Balance After: *₹{balance - price:,}*\n\n"
            f"📧 Please enter your *email address* to receive the card:",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_EMAIL

    # ── ADD MONEY / TOPUP ─────────────────────────────────────
    elif data == "topup":
        text = (
            "💰 *ADD MONEY TO WALLET*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "ℹ️ *Fee Policy:*\n"
            f"  • Below ₹{FEE_THRESHOLD}: {FEE_PERCENT}% processing fee\n"
            f"  • ₹{FEE_THRESHOLD}+: *Zero fee!* 🎉\n\n"
            "💡 *Tip:* Recharge ₹120+ to save on fees!\n\n"
            "Select amount or type custom:"
        )
        await query.edit_message_text(text, reply_markup=amount_keyboard(), parse_mode=ParseMode.MARKDOWN)

    # ── AMOUNT SELECTED ───────────────────────────────────────
    elif data.startswith("amount_"):
        amount = int(data[7:])
        fee, final = calculate_fee(amount)
        qr_path = generate_qr(UPI_ID, amount)

        context.user_data["recharge"] = {
            "amount": amount, "fee": fee, "final": final
        }

        payment_text = (
            f"💳 *PAYMENT DETAILS*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Amount: *₹{amount:,}*\n"
            f"💸 Fee: *₹{fee}*\n"
            f"✅ You'll receive: *₹{final}*\n\n"
            f"🏦 *UPI ID:* `{UPI_ID}`\n\n"
            f"📸 After payment:\n"
            f"1️⃣ Click *I HAVE PAID*\n"
            f"2️⃣ Upload payment screenshot\n"
            f"3️⃣ Enter UTR/Reference number\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ I HAVE PAID", callback_data="paid")],
            [InlineKeyboardButton("🔙 Back", callback_data="topup")],
        ])

        if qr_path:
            try:
                with open(qr_path, "rb") as qr_file:
                    await context.bot.send_photo(
                        chat_id=user.id,
                        photo=qr_file,
                        caption=payment_text,
                        reply_markup=keyboard,
                        parse_mode=ParseMode.MARKDOWN
                    )
                await query.message.delete()
            except Exception:
                await query.edit_message_text(payment_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        else:
            await query.edit_message_text(payment_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    # ── WALLET ────────────────────────────────────────────────
    elif data == "wallet":
        balance = db_user["balance"] if db_user else 0
        purchases = db_user["total_purchases"] if db_user else 0
        badge = ui.user_badge(purchases)
        recent = db.get_purchases(user.id, 5)

        text = (
            f"👛 *MY WALLET*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 {user.first_name} | {badge}\n"
            f"💰 Balance: *₹{balance:,}*\n"
            f"🛒 Total Purchases: *{purchases}*\n\n"
        )

        if recent:
            text += "📋 *Recent Orders:*\n"
            for p in recent:
                text += f"  • {p['card_name']} ₹{p['card_value']} → ₹{p['price']} | {str(p['timestamp'])[:10]}\n"

        text += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Add Money", callback_data="topup")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")],
        ])
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    # ── REFERRAL ──────────────────────────────────────────────
    elif data == "referral":
        ref_code = db_user["referral_code"] if db_user else ""
        ref_count = db.get_referral_stats(user.id)
        earnings = ref_count * REFERRAL_BONUS
        bot_info = await context.bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={ref_code}"

        text = (
            f"👥 *REFERRAL PROGRAM*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Earn *₹{REFERRAL_BONUS}* per referral!\n"
            f"🎁 Friends get ₹{WELCOME_BONUS} welcome bonus!\n\n"
            f"📊 *Your Stats:*\n"
            f"  • Total Referrals: *{ref_count}*\n"
            f"  • Total Earned: *₹{earnings}*\n\n"
            f"🔗 *Your Referral Link:*\n"
            f"`{ref_link}`\n\n"
            f"📋 *Your Code:* `{ref_code}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Share your link and earn for every friend who joins!"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Share Link", url=f"https://t.me/share/url?url={ref_link}&text=Join Gift Card Bot and get ₹5 FREE!")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")],
        ])
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    # ── DAILY REWARD ──────────────────────────────────────────
    elif data == "daily":
        await daily_reward(update, context)

    # ── COUPONS ───────────────────────────────────────────────
    elif data == "coupon":
        text = (
            "🏷️ *COUPON CODES*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎉 Available Coupons:\n\n"
        )
        for code, cfg in COUPONS_CONFIG.items():
            if cfg["type"] == "percentage":
                text += f"  🏷️ `{code}` - {cfg['discount']}% OFF (min ₹{cfg['min']})\n"
            else:
                text += f"  🏷️ `{code}` - ₹{cfg['discount']} OFF (min ₹{cfg['min']})\n"
        text += "\n📝 Enter a coupon code below:"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]), parse_mode=ParseMode.MARKDOWN)
        return STATE_COUPON

    # ── BULK PURCHASE ─────────────────────────────────────────
    elif data == "bulk":
        text = (
            "📦 *BULK PURCHASE*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎯 *Volume Discounts:*\n"
            f"  • 3+ cards: *3% OFF*\n"
            f"  • 5+ cards: *5% OFF*\n"
            f"  • 10+ cards: *10% OFF*\n"
            f"  • 25+ cards: *15% OFF*\n"
            f"  • 50+ cards: *20% OFF*\n\n"
            "First, select a gift card brand:"
        )
        context.user_data["bulk_mode"] = True
        await query.edit_message_text(text, reply_markup=gift_cards_keyboard(), parse_mode=ParseMode.MARKDOWN)

    # ── SEND GIFT ─────────────────────────────────────────────
    elif data == "gift":
        text = (
            "🎁 *SEND A GIFT CARD*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💝 Surprise your friends & family!\n\n"
            "Select a card to gift:\n"
        )
        context.user_data["gift_mode"] = True
        await query.edit_message_text(text, reply_markup=gift_cards_keyboard(), parse_mode=ParseMode.MARKDOWN)

    # ── PRICE ALERT ───────────────────────────────────────────
    elif data == "alert":
        alerts = db.get_active_alerts(user.id)
        text = (
            "🔔 *PRICE ALERTS*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Get notified when prices drop!\n\n"
        )
        if alerts:
            text += "📋 *Your Active Alerts:*\n"
            for alert in alerts:
                text += f"  • {alert['card_name']}: target ₹{alert['target_price']}\n"
        else:
            text += "You have no active price alerts.\n"
        text += "\nSelect a card to set an alert:"
        context.user_data["alert_mode"] = True
        await query.edit_message_text(text, reply_markup=gift_cards_keyboard(), parse_mode=ParseMode.MARKDOWN)

    # ── LANGUAGE ──────────────────────────────────────────────
    elif data == "language":
        current = db_user["language"] if db_user else "en"
        text = (
            f"🌐 *LANGUAGE SETTINGS*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Current: *{LANGUAGES.get(current, 'English')}*\n\n"
            f"Select your language:"
        )
        await query.edit_message_text(text, reply_markup=language_keyboard(), parse_mode=ParseMode.MARKDOWN)

    elif data.startswith("lang_"):
        lang_code = data[5:]
        if lang_code in LANGUAGES:
            db.update_user(user.id, language=lang_code)
            lang_name = LANGUAGES[lang_code]
            await query.edit_message_text(
                f"✅ Language changed to *{lang_name}*!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]),
                parse_mode=ParseMode.MARKDOWN
            )

    # ── SUPPORT ───────────────────────────────────────────────
    elif data == "support":
        text = (
            "🆘 *SUPPORT*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📝 Describe your issue and we'll help!\n\n"
            "Common issues:\n"
            "  • Payment not credited\n"
            "  • Gift card not received\n"
            "  • Technical problems\n\n"
            "Please type your message:"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Cancel", callback_data="main_menu")]
        ]), parse_mode=ParseMode.MARKDOWN)
        return STATE_SUPPORT

    else:
        await query.answer("Unknown action.", show_alert=True)


# ─────────────────────────────────────────────────────────────
# DAILY REWARD HANDLER
# ─────────────────────────────────────────────────────────────
async def daily_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    reward, result = db.claim_daily_reward(user.id)

    if result == "already_claimed":
        await query.edit_message_text(
            "⏰ *Already Claimed!*\n\nYou already claimed your daily reward today.\nCome back tomorrow! 🌅",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]),
            parse_mode=ParseMode.MARKDOWN
        )
    elif reward:
        streak = result
        next_streak = streak + 1
        next_reward = DAILY_REWARDS.get(next_streak, reward)
        for day in sorted(DAILY_REWARDS.keys()):
            if day > streak:
                next_reward = DAILY_REWARDS[day]
                break
        text = (
            f"🎉 *DAILY REWARD CLAIMED!*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 You earned: *₹{reward}*\n"
            f"🔥 Streak: *Day {streak}*\n"
            f"📈 Tomorrow's reward: *₹{next_reward}*\n\n"
            f"Keep your streak going for bigger rewards!\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 *Streak Milestones:*\n"
            f"  Day 7: ₹25 | Day 15: ₹60 | Day 30: ₹100"
        )
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await query.edit_message_text(
            "❌ Error claiming reward. Please try again.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]),
            parse_mode=ParseMode.MARKDOWN
        )


# ─────────────────────────────────────────────────────────────
# FIXED PAYMENT FLOW HANDLERS - COMPLETELY REWRITTEN
# ─────────────────────────────────────────────────────────────
async def handle_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'I HAVE PAID' button click"""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    
    logger.info(f"💰 Paid button clicked by user {user.id}")

    # Check if recharge data exists
    recharge = context.user_data.get("recharge")
    if not recharge:
        logger.warning(f"⚠️ No recharge data for user {user.id}")
        await query.message.reply_text(
            "⏰ Session expired. Please start again.",
            reply_markup=main_menu_keyboard()
        )
        return ConversationHandler.END

    # Move to screenshot state
    await query.message.reply_text(
        f"📸 *SEND PAYMENT SCREENSHOT*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Amount: *₹{recharge['amount']:,}*\n"
        f"You'll get: *₹{recharge['final']:,}*\n\n"
        f"Please send a clear screenshot of your payment.\n\n"
        f"_(Send the photo now)_",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return STATE_SCREENSHOT


async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle screenshot upload"""
    user = update.effective_user
    logger.info(f"📸 Screenshot received from user {user.id}")
    
    if not update.message.photo:
        await update.message.reply_text(
            "❌ Please send a photo (screenshot of your payment)."
        )
        return STATE_SCREENSHOT

    # Store screenshot
    photo = update.message.photo[-1]
    context.user_data["screenshot"] = photo.file_id
    logger.info(f"✅ Screenshot saved for user {user.id}")

    await update.message.reply_text(
        f"✅ Screenshot received!\n\n"
        f"🔢 Now please enter your UTR number:\n"
        f"_(12-22 digits/letters)_\n\n"
        f"Example: SBIN1234567890"
    )
    return STATE_UTR


async def handle_utr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle UTR input"""
    user = update.effective_user
    utr = update.message.text.strip().upper()
    
    logger.info(f"🔤 UTR received from user {user.id}: {utr[:10]}...")

    # Validate UTR
    if not (12 <= len(utr) <= 22 and utr.isalnum()):
        await update.message.reply_text(
            "❌ Invalid UTR! Must be 12-22 alphanumeric characters.\n"
            "Please try again:"
        )
        return STATE_UTR

    # Check session data
    recharge = context.user_data.get("recharge")
    screenshot = context.user_data.get("screenshot")
    
    if not recharge or not screenshot:
        await update.message.reply_text(
            "⏰ Session expired. Please start again with /start"
        )
        return ConversationHandler.END

    # Check for duplicate UTR
    if db.is_utr_duplicate(utr):
        await update.message.reply_text(
            "❌ This UTR has already been submitted.\n"
            "Please check and try again with a different UTR."
        )
        return STATE_UTR

    # Save to database
    try:
        # Ensure user exists in users table
        db.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
            (user.id,),
            commit=True
        )

        db.create_verification(
            user.id,
            recharge["amount"],
            recharge["fee"],
            recharge["final"],
            utr,
            screenshot
        )

        logger.info(f"✅ Verification saved for user {user.id}")

    except Exception as e:
        logger.error(f"Database error: {e}")
        await update.message.reply_text(
            "❌ Database error. Please try again later."
        )
        return ConversationHandler.END

    # Get verification ID
    ver = db.execute(
        "SELECT id FROM verifications WHERE utr=?",
        (utr,),
        fetchone=True
    )
    ver_id = ver["id"] if ver else 0

    # Send to admin channel
    try:
        caption = (
            f"💳 *NEW PAYMENT VERIFICATION*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 User: {user.first_name}\n"
            f"🆔 ID: {user.id}\n"
            f"💰 Amount: ₹{recharge['amount']}\n"
            f"✅ Credit: ₹{recharge['final']}\n"
            f"🔢 UTR: {utr}"
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{ver_id}"),
            InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{ver_id}")
        ]])
        
        await context.bot.send_photo(
            chat_id=ADMIN_CHANNEL_ID,
            photo=screenshot,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        logger.info("✅ Admin notification sent")
    except Exception as e:
        logger.error(f"Admin notification error: {e}")
        # Still continue - user doesn't need to know

    # Clear session data
    context.user_data.pop("recharge", None)
    context.user_data.pop("screenshot", None)

    # SUCCESS MESSAGE
    await update.message.reply_text(
        f"✅ *PAYMENT SUBMITTED SUCCESSFULLY!*\n\n"
        f"Amount: ₹{recharge['amount']}\n"
        f"UTR: {utr}\n\n"
        f"Your payment is under review. You'll be notified once approved.\n\n"
        f"Thank you for using Gift Card Bot! 🎁"
    )

    logger.info(f"✅ Payment flow completed for user {user.id}")
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────
# EMAIL HANDLER (for purchases)
# ─────────────────────────────────────────────────────────────
async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip() if update.message.text else ""
    user = update.effective_user

    if not validate_email(email):
        await update.message.reply_text(
            "❌ Invalid email address. Please enter a valid email:\n_(e.g. yourname@gmail.com)_",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_EMAIL

    purchase = context.user_data.get("purchase")
    if not purchase:
        await update.message.reply_text("❌ Session expired. Please start again.")
        return ConversationHandler.END

    balance = db.get_balance(user.id)
    price = purchase["price"]

    if balance < price:
        await update.message.reply_text(
            f"❌ Insufficient balance!\nYour balance: ₹{balance}\nRequired: ₹{price}\n\nPlease add money first."
        )
        context.user_data.clear()
        return ConversationHandler.END

    # Deduct balance and create order
    db.update_balance(user.id, price, "debit")
    order_id = db.create_purchase(user.id, purchase["card_name"], purchase["denom"], price, email)

    # Notify admin
    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHANNEL_ID,
            text=(
                f"🛒 *NEW PURCHASE ORDER*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 User: {user.first_name} (ID: {user.id})\n"
                f"🎁 Card: {purchase['card_name']} ₹{purchase['denom']:,}\n"
                f"💰 Price Paid: ₹{price}\n"
                f"📧 Email: {email}\n"
                f"📋 Order ID: {order_id}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Admin notification error: {e}")

    context.user_data.clear()
    await update.message.reply_text(
        f"✅ ORDER PLACED SUCCESSFULLY!\n\n"
        f"Order ID: {order_id}\n"
        f"Card: {purchase['card_name']} ₹{purchase['denom']:,}\n"
        f"Email: {email}\n\n"
        f"Your gift card will be delivered to your email within 30 minutes.\n"
        f"Use /start to return to the main menu."
    )
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────
# SUPPORT HANDLER
# ─────────────────────────────────────────────────────────────
async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text.strip() if update.message.text else ""
    user = update.effective_user

    if len(message) < 10:
        await update.message.reply_text("Please describe your issue in at least 10 characters.")
        return STATE_SUPPORT

    ticket_id = db.create_support_ticket(user.id, message)

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"🆘 *SUPPORT TICKET #{ticket_id}*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 From: {user.first_name} (@{user.username or 'N/A'})\n"
                f"🆔 ID: {user.id}\n"
                f"📝 Message:\n{message}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Support notification error: {e}")

    await update.message.reply_text(
        f"✅ Support ticket #{ticket_id} submitted!\n\n"
        f"Our team will respond within 24 hours.\n"
        f"Use /start to return to the main menu."
    )
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────
# COUPON HANDLER
# ─────────────────────────────────────────────────────────────
async def handle_coupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip().upper() if update.message.text else ""
    user = update.effective_user

    cfg, error = db.validate_coupon(code, user.id, 1000)  # Demo: check against ₹1000 purchase
    if error:
        await update.message.reply_text(
            f"❌ {error}\n\nTry another code or /start to go back."
        )
        return ConversationHandler.END

    db.use_coupon(code, user.id)
    if cfg["type"] == "percentage":
        discount_text = f"{cfg['discount']}% OFF"
    else:
        discount_text = f"₹{cfg['discount']} OFF"

    await update.message.reply_text(
        f"✅ Coupon *{code}* applied!\n"
        f"Discount: *{discount_text}*\n\n"
        f"Use this during your next purchase!\n"
        f"Use /start to shop.",
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────
# BULK COUNT HANDLER
# ─────────────────────────────────────────────────────────────
async def handle_bulk_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip() if update.message.text else ""
    user = update.effective_user

    if not text.isdigit() or int(text) < 1:
        await update.message.reply_text("❌ Please enter a valid quantity (minimum 1):")
        return STATE_BULK_COUNT

    quantity = int(text)
    purchase = context.user_data.get("purchase", {})
    price = purchase.get("price", 0)
    card_name = purchase.get("card_name", "Unknown")
    denom = purchase.get("denom", 0)

    result = calculate_bulk_discount(quantity, price)
    balance = db.get_balance(user.id)

    text_out = (
        f"📦 *BULK ORDER SUMMARY*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎁 Card: {card_name} ₹{denom:,}\n"
        f"📊 Quantity: {quantity}\n"
        f"💰 Unit Price: ₹{price}\n"
        f"📉 Discount: {result['discount']}%  (-₹{result['discount_amount']})\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Total: *₹{result['final']:,}*\n"
        f"👛 Your Balance: ₹{balance:,}\n\n"
    )

    if balance < result["final"]:
        text_out += f"❌ Insufficient balance! Shortfall: ₹{result['final'] - balance:,}"
        await update.message.reply_text(text_out, parse_mode=ParseMode.MARKDOWN)
    else:
        text_out += "Please enter your email to receive all cards:"
        context.user_data["bulk_order"] = result
        await update.message.reply_text(text_out, parse_mode=ParseMode.MARKDOWN)

    context.user_data.clear()
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────
# GIFT EMAIL HANDLER
# ─────────────────────────────────────────────────────────────
async def handle_gift_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip() if update.message.text else ""
    user = update.effective_user

    if not validate_email(email):
        await update.message.reply_text("❌ Invalid email. Please enter a valid email address:")
        return STATE_GIFT_EMAIL

    purchase = context.user_data.get("purchase", {})
    await update.message.reply_text(
        f"🎁 Gift card will be sent to: *{email}*\n\n"
        f"Processing your gift order...\n"
        f"Use /start to return to the main menu.",
        parse_mode=ParseMode.MARKDOWN
    )
    context.user_data.clear()
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────
# PRICE ALERT HANDLER
# ─────────────────────────────────────────────────────────────
async def handle_alert_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip() if update.message.text else ""
    user = update.effective_user

    if not text.isdigit():
        await update.message.reply_text("❌ Please enter a valid price amount:")
        return STATE_PRICE_ALERT

    target_price = int(text)
    alert_card = context.user_data.get("alert_card", "Unknown")
    current_price = PRICES.get(500, 100)  # Example current price

    db.add_price_alert(user.id, alert_card, target_price, current_price)

    await update.message.reply_text(
        f"✅ Price Alert Set!\n\n"
        f"Card: {alert_card}\n"
        f"Target Price: ₹{target_price}\n\n"
        f"You'll be notified when the price drops to your target!\n"
        f"Use /start to return to the main menu."
    )
    context.user_data.clear()
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────
# ADMIN HANDLERS
# ─────────────────────────────────────────────────────────────
async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle approve/reject callbacks from admin channel"""
    query = update.callback_query
    await query.answer()
    admin_user = update.effective_user

    if admin_user.id != ADMIN_ID:
        await query.answer("❌ Admin only!", show_alert=True)
        return

    data = query.data
    parts = data.split("_")
    action = parts[0]
    ver_id = int(parts[1]) if len(parts) > 1 else 0

    ver = db.get_verification(ver_id)
    if not ver:
        await query.edit_message_caption("❌ Verification not found.")
        return

    if ver["status"] != "pending":
        await query.edit_message_caption(
            f"ℹ️ Already {ver['status']}.\n\n" + (query.message.caption or "")
        )
        return

    if action == "approve":
        db.update_verification_status(ver_id, "approved")
        db.update_balance(ver["user_id"], ver["final_amount"], "credit", ver["utr"])
        db.log_admin_action(admin_user.id, "approve", f"ver_id={ver_id}, user={ver['user_id']}, amount={ver['final_amount']}")

        # Notify user
        try:
            await context.bot.send_message(
                chat_id=ver["user_id"],
                text=(
                    f"✅ *PAYMENT APPROVED!*\n\n"
                    f"Amount: ₹{ver['final_amount']} has been added to your wallet!\n"
                    f"UTR: {ver['utr']}\n\n"
                    f"Happy shopping! Use /start to continue. 🎁"
                )
            )
        except Exception as e:
            logger.error(f"User notification error: {e}")

        await query.edit_message_caption(
            f"✅ APPROVED by {admin_user.first_name}\n"
            f"User {ver['user_id']} credited ₹{ver['final_amount']}\n\n"
            + (query.message.caption or "")
        )

    elif action == "reject":
        db.update_verification_status(ver_id, "rejected")
        db.log_admin_action(admin_user.id, "reject", f"ver_id={ver_id}, user={ver['user_id']}")

        try:
            await context.bot.send_message(
                chat_id=ver["user_id"],
                text=(
                    f"❌ *PAYMENT REJECTED*\n\n"
                    f"Your payment of ₹{ver['amount']} was rejected.\n"
                    f"UTR: {ver['utr']}\n\n"
                    f"If you believe this is an error, please contact support."
                )
            )
        except Exception as e:
            logger.error(f"User notification error: {e}")

        await query.edit_message_caption(
            f"❌ REJECTED by {admin_user.first_name}\n\n"
            + (query.message.caption or "")
        )


@admin_only
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = db.get_statistics()
    text = (
        f"📊 *BOT STATISTICS*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Total Users: *{stats['total_users']:,}*\n"
        f"🆕 Today New: *{stats['today_new_users']}*\n"
        f"🛒 Total Purchases: *{stats['total_purchases']:,}*\n"
        f"💰 Total Revenue: *₹{stats['total_revenue']:,}*\n"
        f"⏳ Pending Verifications: *{stats['pending_verifications']}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 Export Users CSV", callback_data="export_users")],
        [InlineKeyboardButton("📢 Force Promotion", callback_data="force_promo")],
    ])
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)


@admin_only
async def admin_force_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_promotion(context)
    await update.message.reply_text("✅ Promotion sent!")


# ─────────────────────────────────────────────────────────────
# AUTO PROMOTIONS
# ─────────────────────────────────────────────────────────────
PROMO_TEMPLATES = [
    (
        "🎁 *MEGA GIFT CARD SALE!*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💰 Amazon ₹500 → Only *₹100* (80% OFF!)\n"
        "💰 Flipkart ₹1000 → Only *₹200* (80% OFF!)\n"
        "💰 Play Store ₹500 → Only *₹100* (80% OFF!)\n\n"
        "⚡ Limited time offer!\n"
        "👥 Refer friends: Earn ₹2 per referral!\n"
        "🎁 New users get ₹5 FREE welcome bonus!\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🛒 Shop Now!"
    ),
    (
        "🔥 *FLASH SALE ALERT!*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🛍️ Myntra ₹2000 → *₹400* (80% OFF!)\n"
        "🍕 Zomato ₹500 → *₹100* (80% OFF!)\n"
        "🎬 BookMyShow ₹1000 → *₹200* (80% OFF!)\n\n"
        "📦 Bulk Buy & Save More:\n"
        "  3 cards = 3% extra OFF\n"
        "  10 cards = 10% extra OFF\n\n"
        "📅 Daily login rewards up to ₹100/day!\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🛒 Shop Now!"
    ),
    (
        "💎 *EXCLUSIVE DEALS TODAY!*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🛒 Big Basket ₹5000 → *₹1000* (80% OFF!)\n"
        "🟦 Amazon ₹2000 → *₹400* (80% OFF!)\n\n"
        "🏷️ Use coupon *SAVE20* → Extra ₹20 OFF!\n"
        "🎁 Gift cards to friends & family!\n"
        "🔔 Set price alerts for your favorite cards!\n\n"
        "🌐 Available in 7 Indian languages!\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🛒 Shop Now!"
    ),
]

import random

async def send_promotion(context: ContextTypes.DEFAULT_TYPE):
    try:
        bot_info = await context.bot.get_me()
        promo = random.choice(PROMO_TEMPLATES)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 SHOP NOW", url=f"https://t.me/{bot_info.username}")]
        ])
        await context.bot.send_message(
            chat_id=MAIN_CHANNEL,
            text=promo,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Promotion error: {e}")


# ─────────────────────────────────────────────────────────────
# ERROR HANDLER
# ─────────────────────────────────────────────────────────────
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update caused error: {context.error}", exc_info=True)
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again or use /start."
            )
    except Exception:
        pass
    try:
        if isinstance(context.error, (sqlite3.Error,)):
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"⚠️ Critical Error:\n{str(context.error)[:500]}"
            )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# POST INIT
# ─────────────────────────────────────────────────────────────
async def post_init(app):
    await app.bot.set_my_commands([
        BotCommand("start", "🚀 Start the bot"),
        BotCommand("cancel", "❌ Cancel current action"),
        BotCommand("stats", "📊 Statistics (Admin only)"),
        BotCommand("forcepromo", "📢 Force Promotion (Admin only)"),
    ])

    try:
        chat = await app.bot.get_chat(ADMIN_CHANNEL_ID)
        await app.bot.send_message(
            chat_id=ADMIN_CHANNEL_ID,
            text="✅ *Gift Card Bot Started Successfully!*\n\nAll systems operational. 🚀",
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info("✅ Admin channel verified")
    except Exception as e:
        logger.warning(f"Admin channel warning: {e}")

    logger.info("✅ Bot ready!")


# ─────────────────────────────────────────────────────────────
# MAIN APPLICATION
# ─────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # ── Payment Conversation ─────────────────────────────────
    payment_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_paid, pattern="^paid$")],
        states={
            STATE_SCREENSHOT: [MessageHandler(filters.PHOTO, handle_screenshot)],
            STATE_UTR: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_utr)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
        per_user=True,
        per_chat=True,
    )

    # ── Email Conversation (for purchases) ───────────────────
    email_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^buy_")],
        states={
            STATE_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
        per_user=True,
    )

    # ── Support Conversation ─────────────────────────────────
    support_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^support$")],
        states={
            STATE_SUPPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_support)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
        per_user=True,
    )

    # ── Coupon Conversation ───────────────────────────────────
    coupon_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^coupon$")],
        states={
            STATE_COUPON: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_coupon)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
        per_user=True,
    )

    # ── Bulk Conversation ────────────────────────────────────
    bulk_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^bulk$")],
        states={
            STATE_BULK_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bulk_count)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
        per_user=True,
    )

    # ── Gift Conversation ────────────────────────────────────
    gift_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^gift$")],
        states={
            STATE_GIFT_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gift_email)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
        per_user=True,
    )

    # ── Alert Conversation ────────────────────────────────────
    alert_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^alert$")],
        states={
            STATE_PRICE_ALERT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_alert_price)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
        per_user=True,
    )

    # ── 1. Command Handlers ──────────────────────────────────
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("forcepromo", admin_force_promo))

    # ── 2. Conversation Handlers (highest priority) ──────────
    app.add_handler(payment_conv)
    app.add_handler(email_conv)
    app.add_handler(support_conv)
    app.add_handler(coupon_conv)
    app.add_handler(bulk_conv)
    app.add_handler(gift_conv)
    app.add_handler(alert_conv)

    # ── 3. Specific Pattern Handlers ─────────────────────────
    app.add_handler(CallbackQueryHandler(admin_handler, pattern="^(approve|reject)_"))

    # ── 4. Generic Button Handler (LAST) ─────────────────────
    app.add_handler(CallbackQueryHandler(button_handler))

    # ── 5. Error Handler ─────────────────────────────────────
    app.add_error_handler(error_handler)

    # ── Job Queue: Auto Promotions ───────────────────────────
    app.job_queue.run_repeating(send_promotion, interval=POST_INTERVAL, first=60)

    logger.info("🚀 Starting Gift Card Bot...")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
