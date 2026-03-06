#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
================================================================================
🎁 GIFT CARD & RECHARGE BOT - PRODUCTION READY 🎁
================================================================================
A fully featured Telegram bot for selling gift cards and managing recharges
with beautiful UI, complete error handling, and professional design.

Version: 7.0.0 (Stable Production Release)
================================================================================
"""

import logging
import sqlite3
import asyncio
import random
import os
import sys
import re
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

# ===========================================================================
# ENVIRONMENT VARIABLES (SET THESE IN RAILWAY)
# ===========================================================================
"""
IMPORTANT: Set these environment variables in Railway:
- BOT_TOKEN: Your bot token from @BotFather
- ADMIN_ID: Your Telegram user ID
- UPI_ID: Your UPI ID for payments
"""

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
UPI_ID = os.environ.get("UPI_ID", "")

# Hardcoded values (change if needed)
MAIN_CHANNEL = "@gift_card_main"
PROOF_CHANNEL = "@gift_card_log"
ADMIN_CHANNEL_ID = -1003607749028
QR_CODE_PATH = "qr.jpg"
DATABASE_PATH = "bot_database.db"

# Payment Configuration
MIN_RECHARGE = 10
MAX_RECHARGE = 10000
FEE_PERCENT = 20
FEE_THRESHOLD = 120
REFERRAL_BONUS = 10
WELCOME_BONUS = 5

# ===========================================================================
# CONVERSATION STATES - FIXED: 6 states not 15
# ===========================================================================
(
    STATE_AMOUNT,
    STATE_SCREENSHOT,
    STATE_UTR,
    STATE_EMAIL,
    STATE_SUPPORT
) = range(5)  # Only 5 states needed

# ===========================================================================
# GIFT CARD DATA
# ===========================================================================

GIFT_CARDS = {
    "amazon": {"name": "AMAZON", "emoji": "🟦", "full_emoji": "🟦🛒", "popular": True},
    "flipkart": {"name": "FLIPKART", "emoji": "📦", "full_emoji": "📦🛍️", "popular": True},
    "playstore": {"name": "PLAY STORE", "emoji": "🟩", "full_emoji": "🟩🎮", "popular": True},
    "bookmyshow": {"name": "BOOKMYSHOW", "emoji": "🎟️", "full_emoji": "🎟️🎬", "popular": True},
    "myntra": {"name": "MYNTRA", "emoji": "🛍️", "full_emoji": "🛍️👗", "popular": True},
    "zomato": {"name": "ZOMATO", "emoji": "🍕", "full_emoji": "🍕🍔", "popular": True},
    "bigbasket": {"name": "BIG BASKET", "emoji": "🛒", "full_emoji": "🛒🥬", "popular": True}
}

PRICES = {500: 100, 1000: 200, 2000: 400, 5000: 1000}
AVAILABLE_DENOMINATIONS = [500, 1000, 2000, 5000]

# ===========================================================================
# SETUP LOGGING - FIXED: No duplicate handlers
# ===========================================================================

def setup_logging():
    """Setup logging system once"""
    logger = logging.getLogger()
    
    # Clear any existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()
    
    logger.setLevel(logging.INFO)
    
    # Console handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)
    
    # File handler (optional)
    try:
        Path("logs").mkdir(exist_ok=True)
        file_handler = logging.FileHandler("logs/bot.log")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except:
        pass
    
    return logger

logger = setup_logging()

# ===========================================================================
# DATABASE MANAGER - FIXED: Thread-safe with proper connection handling
# ===========================================================================

class DatabaseManager:
    """Simple thread-safe database manager"""
    
    def __init__(self):
        self.db_path = DATABASE_PATH
        self._init_database()
    
    def _get_connection(self):
        """Get new connection - each thread gets its own"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        return conn
    
    def _init_database(self):
        """Initialize database tables"""
        conn = self._get_connection()
        c = conn.cursor()
        
        # Users table
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            balance INTEGER DEFAULT 0,
            total_recharged INTEGER DEFAULT 0,
            total_spent INTEGER DEFAULT 0,
            total_purchases INTEGER DEFAULT 0,
            total_referrals INTEGER DEFAULT 0,
            referral_code TEXT UNIQUE,
            referred_by INTEGER,
            join_date TIMESTAMP,
            last_active TIMESTAMP
        )''')
        
        # Transactions table
        c.execute('''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            type TEXT,
            status TEXT,
            utr TEXT UNIQUE,
            timestamp TIMESTAMP
        )''')
        
        # Purchases table
        c.execute('''CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            order_id TEXT UNIQUE,
            card_type TEXT,
            card_value INTEGER,
            price INTEGER,
            email TEXT,
            timestamp TIMESTAMP
        )''')
        
        # Verifications table
        c.execute('''CREATE TABLE IF NOT EXISTS verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            fee INTEGER,
            final_amount INTEGER,
            utr TEXT UNIQUE,
            screenshot TEXT,
            status TEXT DEFAULT 'pending',
            timestamp TIMESTAMP
        )''')
        
        # Support tickets table
        c.execute('''CREATE TABLE IF NOT EXISTS support (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            status TEXT DEFAULT 'open',
            timestamp TIMESTAMP
        )''')
        
        # Referrals table
        c.execute('''CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_id INTEGER UNIQUE,
            bonus_amount INTEGER DEFAULT 10,
            status TEXT DEFAULT 'pending',
            timestamp TIMESTAMP
        )''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Database initialized")
    
    # ===== USER METHODS =====
    
    def get_user(self, user_id):
        conn = self._get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def create_user(self, user_id, username=None, first_name=None, referred_by=None):
        conn = self._get_connection()
        c = conn.cursor()
        
        import hashlib
        referral_code = hashlib.md5(f"{user_id}{datetime.now()}".encode()).hexdigest()[:8]
        now = datetime.now().isoformat()
        
        c.execute('''INSERT OR IGNORE INTO users 
            (user_id, username, first_name, referral_code, referred_by, join_date, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (user_id, username, first_name, referral_code, referred_by, now, now))
        
        conn.commit()
        conn.close()
        return self.get_user(user_id)
    
    def update_last_active(self, user_id):
        conn = self._get_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET last_active = ? WHERE user_id = ?",
                 (datetime.now().isoformat(), user_id))
        conn.commit()
        conn.close()
    
    def get_balance(self, user_id):
        user = self.get_user(user_id)
        return user['balance'] if user else 0
    
    def update_balance(self, user_id, amount, txn_type, utr=None):
        conn = self._get_connection()
        c = conn.cursor()
        
        try:
            # Get current balance
            c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            if not row:
                return False
            
            current = row[0]
            new_balance = current + amount
            
            if new_balance < 0:
                return False
            
            # Update balance
            c.execute("UPDATE users SET balance = ?, last_active = ? WHERE user_id = ?",
                     (new_balance, datetime.now().isoformat(), user_id))
            
            # Record transaction
            c.execute('''INSERT INTO transactions 
                (user_id, amount, type, status, utr, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)''',
                (user_id, abs(amount), txn_type, 'completed', utr, datetime.now().isoformat()))
            
            # Update totals
            if amount > 0:
                c.execute("UPDATE users SET total_recharged = total_recharged + ? WHERE user_id = ?",
                         (amount, user_id))
            else:
                c.execute("UPDATE users SET total_spent = total_spent + ? WHERE user_id = ?",
                         (abs(amount), user_id))
                c.execute("UPDATE users SET total_purchases = total_purchases + 1 WHERE user_id = ?",
                         (user_id,))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Balance update error: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    # ===== VERIFICATION METHODS =====
    
    def create_verification(self, user_id, amount, fee, final, utr, screenshot):
        conn = self._get_connection()
        c = conn.cursor()
        
        c.execute('''INSERT INTO verifications 
            (user_id, amount, fee, final_amount, utr, screenshot, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (user_id, amount, fee, final, utr, screenshot, datetime.now().isoformat()))
        
        vid = c.lastrowid
        conn.commit()
        conn.close()
        return str(vid)
    
    def approve_verification(self, vid):
        conn = self._get_connection()
        c = conn.cursor()
        
        try:
            c.execute("SELECT * FROM verifications WHERE id = ?", (vid,))
            row = c.fetchone()
            if not row:
                return False
            
            v = dict(row)
            
            c.execute("UPDATE verifications SET status = 'approved' WHERE id = ?", (vid,))
            self.update_balance(v['user_id'], v['final_amount'], 'credit', v['utr'])
            
            conn.commit()
            return v
        except:
            return False
        finally:
            conn.close()
    
    def reject_verification(self, vid):
        conn = self._get_connection()
        c = conn.cursor()
        c.execute("UPDATE verifications SET status = 'rejected' WHERE id = ?", (vid,))
        conn.commit()
        conn.close()
        return True
    
    # ===== PURCHASE METHODS =====
    
    def create_purchase(self, user_id, card_type, value, price, email):
        conn = self._get_connection()
        c = conn.cursor()
        
        order_id = f"GC{datetime.now().strftime('%y%m%d%H%M%S')}{random.randint(1000,9999)}"
        
        c.execute('''INSERT INTO purchases 
            (user_id, order_id, card_type, card_value, price, email, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (user_id, order_id, card_type, value, price, email, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        return order_id
    
    # ===== SUPPORT METHODS =====
    
    def create_ticket(self, user_id, message):
        conn = self._get_connection()
        c = conn.cursor()
        c.execute('''INSERT INTO support (user_id, message, timestamp) VALUES (?, ?, ?)''',
                 (user_id, message, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    
    # ===== REFERRAL METHODS =====
    
    def process_referral(self, referrer_id, referred_id):
        conn = self._get_connection()
        c = conn.cursor()
        
        try:
            c.execute("SELECT * FROM referrals WHERE referred_id = ?", (referred_id,))
            if c.fetchone():
                return False
            
            c.execute('''INSERT INTO referrals (referrer_id, referred_id, timestamp) VALUES (?, ?, ?)''',
                     (referrer_id, referred_id, datetime.now().isoformat()))
            
            self.update_balance(referrer_id, REFERRAL_BONUS, 'bonus')
            
            conn.commit()
            return True
        except:
            return False
        finally:
            conn.close()

# ===========================================================================
# INITIALIZE DATABASE
# ===========================================================================

db = DatabaseManager()

# ===========================================================================
# HELPER FUNCTIONS
# ===========================================================================

def format_currency(amount):
    return f"₹{amount:,}"

def validate_email(email):
    return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email) is not None

def validate_utr(utr):
    return 12 <= len(utr) <= 22 and utr.isalnum()

def calculate_fee(amount):
    if amount < FEE_THRESHOLD:
        fee = int(amount * FEE_PERCENT / 100)
        return fee, amount - fee
    return 0, amount

# ===========================================================================
# CHECK MEMBERSHIP
# ===========================================================================

async def is_member(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=MAIN_CHANNEL, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# ===========================================================================
# DECORATORS
# ===========================================================================

def admin_only(func):
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("❌ Unauthorized", parse_mode=ParseMode.MARKDOWN)
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def log_action(func):
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        user = update.effective_user
        logger.info(f"👤 {user.id} ({user.first_name}) → {func.__name__}")
        return await func(update, context, *args, **kwargs)
    return wrapper

# ===========================================================================
# START COMMAND
# ===========================================================================

@log_action
async def start(update, context):
    user = update.effective_user
    
    # Check if bot is configured
    if not BOT_TOKEN or not ADMIN_ID or not UPI_ID:
        await update.message.reply_text(
            "⚠️ *Bot not configured*\n\nPlease set environment variables:\n• BOT_TOKEN\n• ADMIN_ID\n• UPI_ID",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Create user if new
    db_user = db.get_user(user.id)
    if not db_user:
        # Check for referral
        referred_by = None
        if context.args and context.args[0].startswith('ref_'):
            try:
                referred_by = int(context.args[0].replace('ref_', ''))
                if referred_by == user.id:
                    referred_by = None
            except:
                pass
        
        db.create_user(user.id, user.username, user.first_name, referred_by)
        logger.info(f"✅ New user: {user.id}")
        
        # Welcome bonus
        if WELCOME_BONUS > 0:
            db.update_balance(user.id, WELCOME_BONUS, 'bonus')
        
        # Process referral
        if referred_by:
            db.process_referral(referred_by, user.id)
            try:
                await context.bot.send_message(
                    referred_by,
                    f"🎉 *Referral Bonus!*\n\n{user.first_name} joined using your link!\n+₹{REFERRAL_BONUS}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
    
    db.update_last_active(user.id)
    
    # Check channel membership
    if not await is_member(user.id, context):
        keyboard = [[
            InlineKeyboardButton("📢 JOIN CHANNEL", url="https://t.me/gift_card_main"),
            InlineKeyboardButton("✅ VERIFY", callback_data="verify")
        ]]
        await update.message.reply_text(
            f"👋 *Hello {user.first_name}!*\n\nJoin our channel to continue:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Show main menu
    balance = db.get_balance(user.id)
    keyboard = [
        [InlineKeyboardButton("🎁 GIFT CARDS", callback_data="giftcard")],
        [InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")],
        [InlineKeyboardButton("💳 MY WALLET", callback_data="wallet")],
        [InlineKeyboardButton("🆘 SUPPORT", callback_data="support")],
        [InlineKeyboardButton("🎁 REFERRAL", callback_data="referral")]
    ]
    await update.message.reply_text(
        f"🏠 *MAIN MENU*\n\n👤 {user.first_name}\n💰 {format_currency(balance)}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===========================================================================
# BUTTON HANDLER
# ===========================================================================

@log_action
async def button_handler(update, context):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data
    
    db.update_last_active(user.id)
    
    # ===== VERIFY =====
    if data == "verify":
        if await is_member(user.id, context):
            balance = db.get_balance(user.id)
            keyboard = [
                [InlineKeyboardButton("🎁 GIFT CARDS", callback_data="giftcard")],
                [InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")],
                [InlineKeyboardButton("💳 MY WALLET", callback_data="wallet")],
                [InlineKeyboardButton("🆘 SUPPORT", callback_data="support")]
            ]
            await query.edit_message_text(
                f"✅ *Verified!*\n\n👋 Welcome {user.first_name}\n💰 Balance: {format_currency(balance)}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            keyboard = [[
                InlineKeyboardButton("📢 JOIN CHANNEL", url="https://t.me/gift_card_main"),
                InlineKeyboardButton("🔄 VERIFY", callback_data="verify")
            ]]
            await query.edit_message_text(
                "❌ *Not a member!*\n\nJoin @gift_card_main first",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return
    
    # Check membership for other actions
    if not await is_member(user.id, context):
        keyboard = [[
            InlineKeyboardButton("📢 JOIN CHANNEL", url="https://t.me/gift_card_main"),
            InlineKeyboardButton("✅ VERIFY", callback_data="verify")
        ]]
        await query.edit_message_text(
            "⚠️ *Access Denied*\n\nJoin @gift_card_main first",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # ===== MAIN MENU =====
    if data == "main_menu":
        balance = db.get_balance(user.id)
        keyboard = [
            [InlineKeyboardButton("🎁 GIFT CARDS", callback_data="giftcard")],
            [InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")],
            [InlineKeyboardButton("💳 MY WALLET", callback_data="wallet")],
            [InlineKeyboardButton("🆘 SUPPORT", callback_data="support")],
            [InlineKeyboardButton("🎁 REFERRAL", callback_data="referral")]
        ]
        await query.edit_message_text(
            f"🏠 *MAIN MENU*\n\n👤 {user.first_name}\n💰 {format_currency(balance)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== GIFT CARDS =====
    elif data == "giftcard":
        keyboard = []
        for cid, card in GIFT_CARDS.items():
            keyboard.append([InlineKeyboardButton(
                f"{card['full_emoji']} {card['name']}",
                callback_data=f"card_{cid}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 BACK", callback_data="main_menu")])
        await query.edit_message_text(
            "🎁 *GIFT CARDS*\n\nSelect a brand:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== CARD DETAILS =====
    elif data.startswith("card_"):
        cid = data.replace("card_", "")
        card = GIFT_CARDS.get(cid)
        if not card:
            return
        
        keyboard = []
        for denom in AVAILABLE_DENOMINATIONS:
            if denom in PRICES:
                price = PRICES[denom]
                keyboard.append([InlineKeyboardButton(
                    f"₹{denom} → ₹{price}",
                    callback_data=f"buy_{cid}_{denom}"
                )])
        keyboard.append([InlineKeyboardButton("🔙 BACK", callback_data="giftcard")])
        
        await query.edit_message_text(
            f"{card['full_emoji']} *{card['name']}*\n\nSelect amount:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== BUY CARD =====
    elif data.startswith("buy_"):
        parts = data.split("_")
        if len(parts) < 3:
            return
        
        cid = parts[1]
        try:
            value = int(parts[2])
        except:
            return
        
        card = GIFT_CARDS.get(cid)
        if not card or value not in PRICES:
            return
        
        price = PRICES[value]
        balance = db.get_balance(user.id)
        
        if balance < price:
            keyboard = [[InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")]]
            await query.edit_message_text(
                f"❌ *Insufficient Balance*\n\nNeed: {format_currency(price)}\nYou have: {format_currency(balance)}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        context.user_data['purchase'] = {
            'card': card['name'],
            'emoji': card['full_emoji'],
            'value': value,
            'price': price
        }
        
        await query.edit_message_text(
            f"✅ *Balance Sufficient*\n\n{card['full_emoji']} {card['name']} ₹{value}\nPrice: {format_currency(price)}\n\n📧 Enter your email:",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_EMAIL
    
    # ===== TOP UP =====
    elif data == "topup":
        keyboard = [
            [InlineKeyboardButton("📱 UPI", callback_data="upi")],
            [InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            "💰 *ADD MONEY*\n\nSelect payment method:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== UPI =====
    elif data == "upi":
        await query.edit_message_text(
            f"💳 *UPI RECHARGE*\n\nEnter amount ({format_currency(MIN_RECHARGE)}-{format_currency(MAX_RECHARGE)}):\n\n📌 Fee: {FEE_PERCENT}% below ₹{FEE_THRESHOLD}",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_AMOUNT
    
    # ===== WALLET =====
    elif data == "wallet":
        balance = db.get_balance(user.id)
        keyboard = [
            [InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")],
            [InlineKeyboardButton("🎁 BUY CARDS", callback_data="giftcard")],
            [InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            f"💳 *YOUR WALLET*\n\n💰 Balance: {format_currency(balance)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== SUPPORT =====
    elif data == "support":
        keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]]
        await query.edit_message_text(
            "🆘 *SUPPORT*\n\nType your issue below:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return STATE_SUPPORT
    
    # ===== REFERRAL =====
    elif data == "referral":
        bot = await context.bot.get_me()
        link = f"https://t.me/{bot.username}?start=ref_{user.id}"
        await query.edit_message_text(
            f"🎁 *REFERRAL PROGRAM*\n\nEarn ₹{REFERRAL_BONUS} per friend!\n\n🔗 Your link:\n`{link}`",
            parse_mode=ParseMode.MARKDOWN
        )

# ===========================================================================
# AMOUNT HANDLER
# ===========================================================================

async def handle_amount(update, context):
    text = update.message.text.strip()
    
    try:
        amount = int(text)
    except:
        await update.message.reply_text("❌ Invalid number")
        return STATE_AMOUNT
    
    if amount < MIN_RECHARGE or amount > MAX_RECHARGE:
        await update.message.reply_text(f"❌ Amount must be {format_currency(MIN_RECHARGE)}-{format_currency(MAX_RECHARGE)}")
        return STATE_AMOUNT
    
    fee, final = calculate_fee(amount)
    context.user_data['topup'] = {'amount': amount, 'fee': fee, 'final': final}
    
    keyboard = [
        [InlineKeyboardButton("✅ I PAID", callback_data="paid")],
        [InlineKeyboardButton("❌ CANCEL", callback_data="main_menu")]
    ]
    
    # Send QR if exists
    if os.path.exists(QR_CODE_PATH):
        with open(QR_CODE_PATH, 'rb') as qr:
            await update.message.reply_photo(
                photo=qr,
                caption=f"💳 *PAYMENT DETAILS*\n\nUPI ID: `{UPI_ID}`\nAmount: {format_currency(amount)}\nYou get: {format_currency(final)}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    else:
        await update.message.reply_text(
            f"💳 *PAYMENT DETAILS*\n\nUPI ID: `{UPI_ID}`\nAmount: {format_currency(amount)}\nYou get: {format_currency(final)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    return ConversationHandler.END

# ===========================================================================
# PAID HANDLER
# ===========================================================================

async def handle_paid(update, context):
    query = update.callback_query
    await query.answer()
    
    if 'topup' not in context.user_data:
        await query.edit_message_text("❌ Session expired")
        return ConversationHandler.END
    
    await query.edit_message_text(
        "📤 *SEND PROOF*\n\n1️⃣ Send SCREENSHOT\n2️⃣ Send UTR number",
        parse_mode=ParseMode.MARKDOWN
    )
    return STATE_SCREENSHOT

# ===========================================================================
# SCREENSHOT HANDLER
# ===========================================================================

async def handle_screenshot(update, context):
    if not update.message.photo:
        await update.message.reply_text("❌ Please send a photo")
        return STATE_SCREENSHOT
    
    context.user_data['screenshot'] = update.message.photo[-1].file_id
    await update.message.reply_text("✅ Screenshot received\n\nNow send UTR number:")
    return STATE_UTR

# ===========================================================================
# UTR HANDLER
# ===========================================================================

async def handle_utr(update, context):
    user = update.effective_user
    utr = update.message.text.strip()
    
    if not validate_utr(utr):
        await update.message.reply_text("❌ Invalid UTR (12-22 characters)")
        return STATE_UTR
    
    if 'topup' not in context.user_data or 'screenshot' not in context.user_data:
        await update.message.reply_text("❌ Session expired")
        return ConversationHandler.END
    
    data = context.user_data['topup']
    vid = db.create_verification(
        user.id, data['amount'], data['fee'], data['final'], utr, context.user_data['screenshot']
    )
    
    # Notify admin
    await context.bot.send_photo(
        chat_id=ADMIN_CHANNEL_ID,
        photo=context.user_data['screenshot'],
        caption=f"🔔 *NEW PAYMENT*\n\n👤 {user.first_name}\n💰 {format_currency(data['amount'])}\n🔢 {utr}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{vid}"),
            InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{vid}")
        ]])
    )
    
    context.user_data.clear()
    await update.message.reply_text("✅ *Verification submitted!*", parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END

# ===========================================================================
# EMAIL HANDLER
# ===========================================================================

async def handle_email(update, context):
    user = update.effective_user
    email = update.message.text.strip()
    
    if not validate_email(email):
        await update.message.reply_text("❌ Invalid email")
        return STATE_EMAIL
    
    if 'purchase' not in context.user_data:
        await update.message.reply_text("❌ Session expired")
        return ConversationHandler.END
    
    p = context.user_data['purchase']
    balance = db.get_balance(user.id)
    
    if balance < p['price']:
        await update.message.reply_text("❌ Insufficient balance")
        return ConversationHandler.END
    
    # Process purchase
    db.update_balance(user.id, -p['price'], 'debit')
    order_id = db.create_purchase(user.id, p['card'], p['value'], p['price'], email)
    
    context.user_data.clear()
    await update.message.reply_text(
        f"✅ *PURCHASE SUCCESSFUL!*\n\n{p['emoji']} {p['card']} ₹{p['value']}\nOrder ID: `{order_id}`",
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END

# ===========================================================================
# SUPPORT HANDLER
# ===========================================================================

async def handle_support(update, context):
    user = update.effective_user
    msg = update.message.text.strip()
    
    if len(msg) < 10:
        await update.message.reply_text("❌ Message too short (min 10 chars)")
        return STATE_SUPPORT
    
    db.create_ticket(user.id, msg)
    
    # Notify admin
    await context.bot.send_message(
        ADMIN_ID,
        f"🆘 *SUPPORT*\n\n👤 {user.first_name}\n💬 {msg}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    await update.message.reply_text("✅ *Support sent!*\n\nWe'll contact you soon.", parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END

# ===========================================================================
# ADMIN HANDLER
# ===========================================================================

@admin_only
async def admin_handler(update, context):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    parts = data.split("_")
    
    if len(parts) < 2:
        return
    
    action = parts[0]
    vid = parts[1]
    
    if action == "approve":
        v = db.approve_verification(vid)
        if v:
            await query.edit_message_caption("✅ APPROVED")
            await context.bot.send_message(
                v['user_id'],
                f"✅ *Payment Approved!*\n\n{format_currency(v['final_amount'])} added.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif action == "reject":
        db.reject_verification(vid)
        await query.edit_message_caption("❌ REJECTED")

# ===========================================================================
# ADMIN COMMANDS
# ===========================================================================

@admin_only
async def admin_stats(update, context):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM verifications WHERE status='pending'")
    pending = c.fetchone()[0]
    
    c.execute("SELECT SUM(amount) FROM transactions WHERE type='credit'")
    revenue = c.fetchone()[0] or 0
    
    conn.close()
    
    await update.message.reply_text(
        f"📊 *STATS*\n\n👥 Users: {users}\n⏳ Pending: {pending}\n💰 Revenue: {format_currency(revenue)}",
        parse_mode=ParseMode.MARKDOWN
    )

# ===========================================================================
# AUTO PROOFS
# ===========================================================================

async def auto_proofs(context):
    try:
        names = ["👑 Raj", "💫 Arjun", "🌟 Kavya", "⚡ Veer", "🔥 Aryan"]
        cards = ["🟦 AMAZON", "🟩 PLAY STORE", "📦 FLIPKART", "🍕 ZOMATO"]
        amounts = [500, 1000, 2000]
        
        msg = f"⚡ *NEW PURCHASE*\n\n👤 {random.choice(names)}\n🎁 {random.choice(cards)} ₹{random.choice(amounts)}"
        await context.bot.send_message(PROOF_CHANNEL, msg, parse_mode=ParseMode.MARKDOWN)
    except:
        pass

# ===========================================================================
# CANCEL
# ===========================================================================

async def cancel(update, context):
    context.user_data.clear()
    await update.message.reply_text("❌ Cancelled")
    return ConversationHandler.END

# ===========================================================================
# ERROR HANDLER
# ===========================================================================

async def error_handler(update, context):
    logger.error(f"❌ Error: {context.error}")

# ===========================================================================
# POST INIT
# ===========================================================================

async def post_init(app):
    await app.bot.set_my_commands([
        BotCommand("start", "🚀 Start"),
        BotCommand("stats", "📊 Stats (admin)"),
        BotCommand("cancel", "❌ Cancel")
    ])
    logger.info("✅ Bot ready")

# ===========================================================================
# MAIN
# ===========================================================================

def main():
    # Validate config
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN not set")
        sys.exit(1)
    if not ADMIN_ID:
        logger.error("❌ ADMIN_ID not set")
        sys.exit(1)
    if not UPI_ID:
        logger.error("❌ UPI_ID not set")
        sys.exit(1)
    
    # Create app
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("stats", admin_stats))
    
    # Button handler
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Admin handler
    app.add_handler(CallbackQueryHandler(admin_handler, pattern="^(approve_|reject_)"))
    
    # Paid handler
    app.add_handler(CallbackQueryHandler(handle_paid, pattern="^paid$"))
    
    # Amount conversation
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^upi$")],
        states={STATE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    ))
    
    # Payment conversation
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_paid, pattern="^paid$")],
        states={
            STATE_SCREENSHOT: [
                MessageHandler(filters.PHOTO, handle_screenshot),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_screenshot)
            ],
            STATE_UTR: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_utr)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    ))
    
    # Email conversation
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^buy_")],
        states={STATE_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    ))
    
    # Support conversation
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^support$")],
        states={STATE_SUPPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_support)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    ))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    # Auto proofs
    if app.job_queue:
        app.job_queue.run_repeating(auto_proofs, interval=45, first=10)
    
    # Start
    print("\n" + "="*50)
    print("      🎁 GIFT CARD BOT v7.0")
    print("="*50)
    print("✅ Bot running...")
    print("="*50 + "\n")
    
    app.run_polling()

if __name__ == "__main__":
    main()
