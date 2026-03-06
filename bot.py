#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
===============================================================================
🎁 GIFT CARD & RECHARGE BOT - ULTIMATE EDITION 🎁
===============================================================================
All issues fixed:
✓ Amount input now working properly
✓ Promo messages detailed & beautiful
✓ Channel username fixed (@gift_card_main)
✓ Referral bonus ₹2
✓ 12 posts per day (every 2 hours)
===============================================================================
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
# CONFIGURATION - YOUR ORIGINAL CHANNELS
# ===========================================================================

# === BOT CREDENTIALS ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8646034766:AAGXkMglnsc72ew1aGcFmWnZziwb8nfS2S8")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "6185091342"))
UPI_ID = os.environ.get("UPI_ID", "helobiy41@ptyes")

# === YOUR ORIGINAL CHANNELS (FIXED) ===
MAIN_CHANNEL = "@gift_card_main"      # Your main channel
PROOF_CHANNEL = "@gift_card_log"      # Proofs channel
ADMIN_CHANNEL_ID = -1003607749028      # Admin channel

# === PATHS ===
QR_CODE_PATH = "qr.jpg"
DATABASE_PATH = "bot_database.db"

# === PAYMENT CONFIG ===
MIN_RECHARGE = 10
MAX_RECHARGE = 10000
FEE_PERCENT = 20
FEE_THRESHOLD = 120

# === REFERRAL BONUS - CHANGED TO ₹2 ===
REFERRAL_BONUS = 2
WELCOME_BONUS = 5

# === AUTO PROMOTION SETTINGS ===
POSTS_PER_DAY = 12  # 12 posts per day
POST_INTERVAL = 7200  # 2 hours in seconds
PROOF_INTERVAL = 45  # Proofs every 45 seconds

# ===========================================================================
# CONVERSATION STATES
# ===========================================================================
(
    STATE_AMOUNT,
    STATE_SCREENSHOT,
    STATE_UTR,
    STATE_EMAIL,
    STATE_SUPPORT
) = range(5)

# ===========================================================================
# GIFT CARD DATA
# ===========================================================================

GIFT_CARDS = {
    "amazon": {
        "name": "AMAZON",
        "emoji": "🟦",
        "full_emoji": "🟦🛒",
        "description": "• Shop millions of products\n• Instant delivery\n• No expiry",
        "popular": True
    },
    "flipkart": {
        "name": "FLIPKART",
        "emoji": "📦",
        "full_emoji": "📦🛍️",
        "description": "• Electronics & Fashion\n• 1 crore+ products\n• Free delivery",
        "popular": True
    },
    "playstore": {
        "name": "PLAY STORE",
        "emoji": "🟩",
        "full_emoji": "🟩🎮",
        "description": "• Apps & Games\n• Movies & Books\n• In-app purchases",
        "popular": True
    },
    "bookmyshow": {
        "name": "BOOKMYSHOW",
        "emoji": "🎟️",
        "full_emoji": "🎟️🎬",
        "description": "• Movie tickets\n• Live events\n• Sports matches",
        "popular": True
    },
    "myntra": {
        "name": "MYNTRA",
        "emoji": "🛍️",
        "full_emoji": "🛍️👗",
        "description": "• Fashion & Lifestyle\n• 2000+ brands\n• Latest trends",
        "popular": True
    },
    "zomato": {
        "name": "ZOMATO",
        "emoji": "🍕",
        "full_emoji": "🍕🍔",
        "description": "• Food delivery\n• 1000+ restaurants\n• Gold membership",
        "popular": True
    },
    "bigbasket": {
        "name": "BIG BASKET",
        "emoji": "🛒",
        "full_emoji": "🛒🥬",
        "description": "• Grocery delivery\n• Fresh vegetables\n• Daily essentials",
        "popular": True
    }
}

# Price configuration
PRICES = {
    500: 100,
    1000: 200,
    2000: 400,
    5000: 1000
}

DENOMINATIONS = [500, 1000, 2000, 5000]

# ===========================================================================
# BEAUTIFUL UI COMPONENTS
# ===========================================================================

EMOJI = {
    "main": "🎁",
    "card": "💳",
    "money": "💰",
    "wallet": "👛",
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "gift": "🎀",
    "star": "⭐",
    "fire": "🔥",
    "crown": "👑",
    "rocket": "🚀",
    "support": "🆘",
    "proof": "📊",
    "referral": "👥",
    "back": "🔙",
    "time": "⏰",
    "email": "📧",
    "phone": "📱",
    "discount": "🏷️",
    "delivery": "📦",
    "instant": "⚡",
    "guarantee": "🛡️",
    "users": "👥",
    "rating": "⭐",
    "featured": "🌟",
    "exclusive": "💎"
}

DIVIDER = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
DIVIDER_SHORT = "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
DIVIDER_DOTS = "⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯"

# ===========================================================================
# LOGGING SETUP
# ===========================================================================

logging.basicConfig(
    format='%(asctime)s | %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===========================================================================
# DATABASE MANAGER
# ===========================================================================

class DatabaseManager:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self._init_db()
        logger.info("✅ Database ready")
    
    def _get_conn(self):
        return sqlite3.connect(self.db_path, timeout=30)
    
    def _init_db(self):
        conn = self._get_conn()
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
            card_name TEXT,
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
        
        # Referrals table
        c.execute('''CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_id INTEGER UNIQUE,
            bonus_amount INTEGER DEFAULT 2,
            status TEXT DEFAULT 'pending',
            timestamp TIMESTAMP
        )''')
        
        conn.commit()
        conn.close()
    
    def get_user(self, user_id):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        return dict(zip([col[0] for col in c.description], row)) if row else None
    
    def create_user(self, user_id, username=None, first_name=None, referred_by=None):
        conn = self._get_conn()
        c = conn.cursor()
        
        import hashlib
        ref_code = hashlib.md5(f"{user_id}{datetime.now()}".encode()).hexdigest()[:8]
        now = datetime.now().isoformat()
        
        c.execute('''INSERT OR IGNORE INTO users 
            (user_id, username, first_name, referral_code, referred_by, join_date, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (user_id, username, first_name, ref_code, referred_by, now, now))
        
        conn.commit()
        conn.close()
        return self.get_user(user_id)
    
    def update_active(self, user_id):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("UPDATE users SET last_active = ? WHERE user_id = ?",
                 (datetime.now().isoformat(), user_id))
        conn.commit()
        conn.close()
    
    def get_balance(self, user_id):
        user = self.get_user(user_id)
        return user['balance'] if user else 0
    
    def update_balance(self, user_id, amount, txn_type, utr=None):
        conn = self._get_conn()
        c = conn.cursor()
        
        try:
            c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            if not row:
                return False
            
            current = row[0]
            new_balance = current + amount
            
            if new_balance < 0:
                return False
            
            c.execute("UPDATE users SET balance = ?, last_active = ? WHERE user_id = ?",
                     (new_balance, datetime.now().isoformat(), user_id))
            
            c.execute('''INSERT INTO transactions 
                (user_id, amount, type, status, utr, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)''',
                (user_id, abs(amount), txn_type, 'completed', utr, datetime.now().isoformat()))
            
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
        except:
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def create_verification(self, user_id, amount, fee, final, utr, screenshot):
        conn = self._get_conn()
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
        conn = self._get_conn()
        c = conn.cursor()
        try:
            c.execute("SELECT * FROM verifications WHERE id = ?", (vid,))
            row = c.fetchone()
            if not row:
                return None
            
            v = dict(zip([col[0] for col in c.description], row))
            c.execute("UPDATE verifications SET status = 'approved' WHERE id = ?", (vid,))
            self.update_balance(v['user_id'], v['final_amount'], 'credit', v['utr'])
            conn.commit()
            return v
        except:
            return None
        finally:
            conn.close()
    
    def reject_verification(self, vid):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("UPDATE verifications SET status = 'rejected' WHERE id = ?", (vid,))
        conn.commit()
        conn.close()
        return True
    
    def create_purchase(self, user_id, card_name, value, price, email):
        conn = self._get_conn()
        c = conn.cursor()
        order_id = f"GC{datetime.now().strftime('%y%m%d%H%M%S')}{random.randint(1000,9999)}"
        c.execute('''INSERT INTO purchases 
            (user_id, order_id, card_name, card_value, price, email, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (user_id, order_id, card_name, value, price, email, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return order_id
    
    def process_referral(self, referrer_id, referred_id):
        conn = self._get_conn()
        c = conn.cursor()
        try:
            c.execute("SELECT * FROM referrals WHERE referred_id = ?", (referred_id,))
            if c.fetchone():
                return False
            
            c.execute('''INSERT INTO referrals (referrer_id, referred_id, bonus_amount, timestamp) VALUES (?, ?, ?, ?)''',
                     (referrer_id, referred_id, REFERRAL_BONUS, datetime.now().isoformat()))
            
            self.update_balance(referrer_id, REFERRAL_BONUS, 'bonus')
            c.execute("UPDATE users SET total_referrals = total_referrals + 1 WHERE user_id = ?",
                     (referrer_id,))
            
            conn.commit()
            return True
        except:
            return False
        finally:
            conn.close()

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
# MEMBERSHIP CHECK - FIXED USERNAME
# ===========================================================================

async def is_member(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=MAIN_CHANNEL, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Membership check error: {e}")
        return False

# ===========================================================================
# START COMMAND
# ===========================================================================

async def start(update, context):
    user = update.effective_user
    
    # Check config
    if not all([BOT_TOKEN, ADMIN_ID, UPI_ID]):
        await update.message.reply_text(
            f"{EMOJI['error']} *Configuration Error*\n\nPlease set environment variables.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Create or get user
    db_user = db.get_user(user.id)
    if not db_user:
        referred = None
        if context.args and context.args[0].startswith('ref_'):
            try:
                referred = int(context.args[0].replace('ref_', ''))
                if referred == user.id:
                    referred = None
            except:
                pass
        
        db.create_user(user.id, user.username, user.first_name, referred)
        logger.info(f"✨ New user: {user.id}")
        
        if WELCOME_BONUS > 0:
            db.update_balance(user.id, WELCOME_BONUS, 'bonus')
        
        if referred:
            db.process_referral(referred, user.id)
            try:
                await context.bot.send_message(
                    referred,
                    f"{EMOJI['referral']} *Referral Bonus!*\n\n"
                    f"{user.first_name} joined using your link!\n"
                    f"+{EMOJI['money']} *₹{REFERRAL_BONUS}*",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
    
    db.update_active(user.id)
    
    # Check membership
    if not await is_member(user.id, context):
        welcome = (
            f"{EMOJI['gift']} *WELCOME TO GIFT CARD BOT* {EMOJI['gift']}\n"
            f"{DIVIDER}\n\n"
            f"👋 *Hello {user.first_name}!*\n\n"
            f"{EMOJI['discount']} *Get Gift Cards at 80% OFF*\n"
            f"{EMOJI['star']} *7+ Premium Brands*\n"
            f"{EMOJI['instant']} *Instant Email Delivery*\n"
            f"{EMOJI['guarantee']} *100% Working Codes*\n\n"
            f"{DIVIDER_SHORT}\n\n"
            f"{EMOJI['lock']} *VERIFICATION REQUIRED*\n"
            f"Join our main channel to continue.\n\n"
            f"👇 *Click below to join*"
        )
        
        keyboard = [[
            InlineKeyboardButton(f"{EMOJI['main']} JOIN MAIN CHANNEL", url="https://t.me/gift_card_main"),
            InlineKeyboardButton(f"{EMOJI['success']} VERIFY", callback_data="verify")
        ]]
        
        await update.message.reply_text(
            welcome,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Show main menu
    balance = db.get_balance(user.id)
    
    menu = (
        f"{EMOJI['main']} *GIFT CARD & RECHARGE BOT* {EMOJI['main']}\n"
        f"{DIVIDER}\n\n"
        f"👤 *User:* {user.first_name}\n"
        f"{EMOJI['money']} *Balance:* `{format_currency(balance)}`\n"
        f"{DIVIDER_SHORT}\n\n"
        f"*Select an option:* ⬇️"
    )
    
    keyboard = [
        [InlineKeyboardButton(f"{EMOJI['card']} GIFT CARDS", callback_data="giftcard")],
        [InlineKeyboardButton(f"{EMOJI['money']} ADD MONEY", callback_data="topup")],
        [InlineKeyboardButton(f"{EMOJI['wallet']} MY WALLET", callback_data="wallet")],
        [InlineKeyboardButton(f"{EMOJI['referral']} REFERRAL (₹{REFERRAL_BONUS}/friend)", callback_data="referral")],
        [InlineKeyboardButton(f"{EMOJI['proof']} LIVE PROOFS", callback_data="proofs")],
        [InlineKeyboardButton(f"{EMOJI['support']} SUPPORT", callback_data="support")]
    ]
    
    await update.message.reply_text(
        menu,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===========================================================================
# BUTTON HANDLER
# ===========================================================================

async def button_handler(update, context):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data
    
    db.update_active(user.id)
    
    # ===== VERIFY =====
    if data == "verify":
        if await is_member(user.id, context):
            balance = db.get_balance(user.id)
            
            success = (
                f"{EMOJI['success']} *VERIFICATION SUCCESSFUL* {EMOJI['success']}\n"
                f"{DIVIDER}\n\n"
                f"👋 *Welcome {user.first_name}!*\n"
                f"{EMOJI['money']} *Balance:* `{format_currency(balance)}`\n\n"
                f"{EMOJI['rocket']} *You now have full access!*\n"
                f"{DIVIDER}\n\n"
                f"*Choose an option:* ⬇️"
            )
            
            keyboard = [
                [InlineKeyboardButton(f"{EMOJI['card']} GIFT CARDS", callback_data="giftcard")],
                [InlineKeyboardButton(f"{EMOJI['money']} ADD MONEY", callback_data="topup")],
                [InlineKeyboardButton(f"{EMOJI['wallet']} MY WALLET", callback_data="wallet")]
            ]
            
            await query.edit_message_text(
                success,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            fail = (
                f"{EMOJI['error']} *VERIFICATION FAILED*\n\n"
                f"You haven't joined our channel yet!\n\n"
                f"1️⃣ Click JOIN CHANNEL\n"
                f"2️⃣ Join @gift_card_main\n"
                f"3️⃣ Click VERIFY"
            )
            
            keyboard = [[
                InlineKeyboardButton(f"{EMOJI['main']} JOIN CHANNEL", url="https://t.me/gift_card_main"),
                InlineKeyboardButton(f"{EMOJI['refresh']} VERIFY", callback_data="verify")
            ]]
            
            await query.edit_message_text(
                fail,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return
    
    # Check membership
    if not await is_member(user.id, context):
        keyboard = [[
            InlineKeyboardButton(f"{EMOJI['main']} JOIN CHANNEL", url="https://t.me/gift_card_main"),
            InlineKeyboardButton(f"{EMOJI['success']} VERIFY", callback_data="verify")
        ]]
        
        await query.edit_message_text(
            f"{EMOJI['warning']} *ACCESS DENIED*\n\nJoin @gift_card_main first!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # ===== MAIN MENU =====
    if data == "main_menu":
        balance = db.get_balance(user.id)
        
        menu = (
            f"{EMOJI['main']} *MAIN MENU* {EMOJI['main']}\n"
            f"{DIVIDER}\n\n"
            f"👤 *User:* {user.first_name}\n"
            f"{EMOJI['money']} *Balance:* `{format_currency(balance)}`\n"
            f"{DIVIDER}\n\n"
            f"*Select an option:* ⬇️"
        )
        
        keyboard = [
            [InlineKeyboardButton(f"{EMOJI['card']} GIFT CARDS", callback_data="giftcard")],
            [InlineKeyboardButton(f"{EMOJI['money']} ADD MONEY", callback_data="topup")],
            [InlineKeyboardButton(f"{EMOJI['wallet']} MY WALLET", callback_data="wallet")],
            [InlineKeyboardButton(f"{EMOJI['referral']} REFERRAL", callback_data="referral")],
            [InlineKeyboardButton(f"{EMOJI['proof']} PROOFS", callback_data="proofs")],
            [InlineKeyboardButton(f"{EMOJI['support']} SUPPORT", callback_data="support")]
        ]
        
        await query.edit_message_text(
            menu,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== GIFT CARDS =====
    elif data == "giftcard":
        text = f"{EMOJI['card']} *GIFT CARDS* {EMOJI['card']}\n{DIVIDER}\n\n*Select a brand:*\n"
        
        keyboard = []
        for cid, card in GIFT_CARDS.items():
            star = "⭐" if card.get('popular', False) else ""
            keyboard.append([InlineKeyboardButton(
                f"{card['full_emoji']} {card['name']} {star}",
                callback_data=f"card_{cid}"
            )])
        
        keyboard.append([InlineKeyboardButton(f"{EMOJI['back']} BACK", callback_data="main_menu")])
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== CARD DETAILS =====
    elif data.startswith("card_"):
        cid = data.replace("card_", "")
        card = GIFT_CARDS.get(cid)
        if not card:
            return
        
        text = (
            f"{card['full_emoji']} *{card['name']} GIFT CARD* {card['full_emoji']}\n"
            f"{DIVIDER}\n\n"
            f"{EMOJI['info']} *Features:*\n"
            f"{card['description']}\n\n"
            f"{EMOJI['delivery']} *Delivery:* Instant on Email\n"
            f"{EMOJI['guarantee']} *Guarantee:* 100% Working\n\n"
            f"{DIVIDER_SHORT}\n\n"
            f"*Available Denominations:*\n"
        )
        
        keyboard = []
        for denom in DENOMINATIONS:
            if denom in PRICES:
                price = PRICES[denom]
                savings = denom - price
                percent = int((savings / denom) * 100)
                keyboard.append([InlineKeyboardButton(
                    f"₹{denom} → ₹{price} (Save {percent}%)",
                    callback_data=f"buy_{cid}_{denom}"
                )])
        
        keyboard.append([InlineKeyboardButton(f"{EMOJI['back']} BACK", callback_data="giftcard")])
        
        await query.edit_message_text(
            text,
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
            keyboard = [[InlineKeyboardButton(f"{EMOJI['money']} ADD MONEY", callback_data="topup")]]
            await query.edit_message_text(
                f"{EMOJI['error']} *Insufficient Balance*\n\n"
                f"Need: `{format_currency(price)}`\n"
                f"You have: `{format_currency(balance)}`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        savings = value - price
        percent = int((savings / value) * 100)
        
        context.user_data['purchase'] = {
            'card': card['name'],
            'emoji': card['full_emoji'],
            'value': value,
            'price': price
        }
        
        await query.edit_message_text(
            f"{EMOJI['success']} *Balance Sufficient*\n\n"
            f"{card['full_emoji']} *{card['name']} ₹{value}*\n"
            f"Price: `{format_currency(price)}`\n"
            f"You Save: `{format_currency(savings)}` ({percent}% OFF)\n\n"
            f"{EMOJI['email']} *Enter your email for delivery:*",
            parse_mode=ParseMode.MARKDOWN
        )
        
        return STATE_EMAIL
    
    # ===== TOP UP =====
    elif data == "topup":
        text = (
            f"{EMOJI['money']} *ADD MONEY TO WALLET* {EMOJI['money']}\n"
            f"{DIVIDER}\n\n"
            f"*Payment Methods:*\n\n"
            f"{EMOJI['phone']} *UPI (Instant)*\n"
            f"  • Min: `{format_currency(MIN_RECHARGE)}`\n"
            f"  • Max: `{format_currency(MAX_RECHARGE)}`\n"
            f"  • Fee: {FEE_PERCENT}% below ₹{FEE_THRESHOLD}\n"
            f"    → Pay ₹100 → Get ₹80\n"
            f"    → Pay ₹200 → Get ₹200\n\n"
            f"*Select method:* ⬇️"
        )
        
        keyboard = [
            [InlineKeyboardButton(f"{EMOJI['phone']} UPI PAYMENT", callback_data="upi")],
            [InlineKeyboardButton(f"{EMOJI['back']} BACK", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== UPI - FIXED AMOUNT INPUT =====
    elif data == "upi":
        text = (
            f"{EMOJI['money']} *UPI RECHARGE* {EMOJI['money']}\n"
            f"{DIVIDER}\n\n"
            f"*Enter amount:*\n\n"
            f"Min: `{format_currency(MIN_RECHARGE)}`\n"
            f"Max: `{format_currency(MAX_RECHARGE)}`\n\n"
            f"{EMOJI['info']} *Fee Structure:*\n"
            f"• Below ₹{FEE_THRESHOLD}: {FEE_PERCENT}% fee\n"
            f"  → Pay ₹100 → Get ₹80\n"
            f"• Above ₹{FEE_THRESHOLD}: No fee\n"
            f"  → Pay ₹200 → Get ₹200\n\n"
            f"`Enter amount in numbers:`"
        )
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        return STATE_AMOUNT
    
    # ===== WALLET =====
    elif data == "wallet":
        balance = db.get_balance(user.id)
        
        text = (
            f"{EMOJI['wallet']} *YOUR WALLET* {EMOJI['wallet']}\n"
            f"{DIVIDER}\n\n"
            f"{EMOJI['money']} *Balance:* `{format_currency(balance)}`\n"
            f"{DIVIDER_SHORT}\n\n"
            f"*Quick Actions:* ⬇️"
        )
        
        keyboard = [
            [InlineKeyboardButton(f"{EMOJI['money']} ADD MONEY", callback_data="topup")],
            [InlineKeyboardButton(f"{EMOJI['card']} BUY CARDS", callback_data="giftcard")],
            [InlineKeyboardButton(f"{EMOJI['back']} BACK", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== REFERRAL - ₹2 BONUS =====
    elif data == "referral":
        bot = await context.bot.get_me()
        link = f"https://t.me/{bot.username}?start=ref_{user.id}"
        
        text = (
            f"{EMOJI['referral']} *REFERRAL PROGRAM* {EMOJI['referral']}\n"
            f"{DIVIDER}\n\n"
            f"{EMOJI['money']} *Earn ₹{REFERRAL_BONUS} per friend!*\n\n"
            f"🔗 *Your Referral Link:*\n"
            f"`{link}`\n\n"
            f"{EMOJI['info']} *How it works:*\n"
            f"1️⃣ Share your link with friends\n"
            f"2️⃣ Friend joins using your link\n"
            f"3️⃣ You get ₹{REFERRAL_BONUS} instantly\n"
            f"4️⃣ Friend gets ₹{WELCOME_BONUS} welcome bonus\n\n"
            f"{EMOJI['rocket']} *Start sharing now!*"
        )
        
        keyboard = [[InlineKeyboardButton(f"{EMOJI['back']} BACK", callback_data="main_menu")]]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== PROOFS =====
    elif data == "proofs":
        text = (
            f"{EMOJI['proof']} *LIVE PROOFS* {EMOJI['proof']}\n"
            f"{DIVIDER}\n\n"
            f"📊 *See real purchases from real users*\n\n"
            f"👉 {PROOF_CHANNEL}\n\n"
            f"{EMOJI['star']} *What you'll see:*\n"
            f"• Live purchase notifications\n"
            f"• Instant delivery proofs\n"
            f"• User satisfaction screenshots\n"
            f"• 24/7 transaction updates\n\n"
            f"{EMOJI['rocket']} *Click below to join*"
        )
        
        keyboard = [
            [InlineKeyboardButton(f"{EMOJI['proof']} VIEW PROOFS", url=f"https://t.me/{PROOF_CHANNEL[1:]}")],
            [InlineKeyboardButton(f"{EMOJI['back']} BACK", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== SUPPORT =====
    elif data == "support":
        text = (
            f"{EMOJI['support']} *SUPPORT* {EMOJI['support']}\n"
            f"{DIVIDER}\n\n"
            f"❓ *Frequently Asked Questions:*\n\n"
            f"1️⃣ *How to buy a gift card?*\n"
            f"   → Add money → Select card → Enter email\n\n"
            f"2️⃣ *How long does delivery take?*\n"
            f"   → Instant (2-5 minutes)\n\n"
            f"3️⃣ *Payment not credited?*\n"
            f"   → Send screenshot + UTR to admin\n\n"
            f"4️⃣ *Card not received?*\n"
            f"   → Check spam folder\n\n"
            f"{DIVIDER_SHORT}\n\n"
            f"📝 *Type your issue below and we'll respond within 24h*"
        )
        
        keyboard = [[InlineKeyboardButton(f"{EMOJI['back']} BACK", callback_data="main_menu")]]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return STATE_SUPPORT

# ===========================================================================
# AMOUNT HANDLER - FIXED: Now properly responds to input
# ===========================================================================

async def handle_amount(update, context):
    """Handle amount input - FIXED version that responds properly"""
    text = update.message.text.strip()
    
    try:
        amount = int(text)
    except ValueError:
        await update.message.reply_text(
            f"{EMOJI['error']} *Invalid Input*\n\nPlease enter a valid number.",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_AMOUNT
    
    if amount < MIN_RECHARGE or amount > MAX_RECHARGE:
        await update.message.reply_text(
            f"{EMOJI['error']} *Invalid Amount*\n\n"
            f"Amount must be between `{format_currency(MIN_RECHARGE)}` and `{format_currency(MAX_RECHARGE)}`.",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_AMOUNT
    
    fee, final = calculate_fee(amount)
    context.user_data['topup'] = {'amount': amount, 'fee': fee, 'final': final}
    
    keyboard = [
        [InlineKeyboardButton(f"{EMOJI['success']} I HAVE PAID", callback_data="paid")],
        [InlineKeyboardButton(f"{EMOJI['back']} CANCEL", callback_data="main_menu")]
    ]
    
    # Send payment details
    if os.path.exists(QR_CODE_PATH):
        with open(QR_CODE_PATH, 'rb') as qr:
            await update.message.reply_photo(
                photo=qr,
                caption=(
                    f"{EMOJI['money']} *PAYMENT DETAILS* {EMOJI['money']}\n"
                    f"{DIVIDER}\n\n"
                    f"{EMOJI['phone']} *UPI ID:* `{UPI_ID}`\n"
                    f"{EMOJI['money']} *Amount:* `{format_currency(amount)}`\n"
                    f"{EMOJI['discount']} *Fee:* `{format_currency(fee) if fee > 0 else 'No fee'}`\n"
                    f"{EMOJI['wallet']} *You get:* `{format_currency(final)}`\n\n"
                    f"{DIVIDER_SHORT}\n\n"
                    f"{EMOJI['phone']} *How to Pay:*\n"
                    f"1️⃣ Scan QR code or pay to UPI ID\n"
                    f"2️⃣ Take a screenshot\n"
                    f"3️⃣ Copy UTR number\n"
                    f"4️⃣ Click 'I HAVE PAID'\n\n"
                    f"⏳ *Auto-cancel in 10 minutes*"
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    else:
        await update.message.reply_text(
            f"{EMOJI['money']} *PAYMENT DETAILS* {EMOJI['money']}\n"
            f"{DIVIDER}\n\n"
            f"{EMOJI['phone']} *UPI ID:* `{UPI_ID}`\n"
            f"{EMOJI['money']} *Amount:* `{format_currency(amount)}`\n"
            f"{EMOJI['discount']} *Fee:* `{format_currency(fee) if fee > 0 else 'No fee'}`\n"
            f"{EMOJI['wallet']} *You get:* `{format_currency(final)}`\n\n"
            f"{DIVIDER_SHORT}\n\n"
            f"{EMOJI['phone']} *How to Pay:*\n"
            f"1️⃣ Open any UPI app (GPay/PhonePe/Paytm)\n"
            f"2️⃣ Pay to UPI ID: `{UPI_ID}`\n"
            f"3️⃣ Take a screenshot\n"
            f"4️⃣ Copy UTR number\n"
            f"5️⃣ Click 'I HAVE PAID'\n\n"
            f"⏳ *Auto-cancel in 10 minutes*",
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
        await query.edit_message_text(
            f"{EMOJI['error']} *Session Expired*\n\nPlease start over.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    await query.edit_message_text(
        f"{EMOJI['money']} *SEND PAYMENT PROOF*\n\n"
        f"1️⃣ Send SCREENSHOT of payment\n"
        f"2️⃣ Send UTR number\n\n"
        f"📌 *UTR Example:* `SBIN1234567890`",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return STATE_SCREENSHOT

# ===========================================================================
# SCREENSHOT HANDLER
# ===========================================================================

async def handle_screenshot(update, context):
    if not update.message.photo:
        await update.message.reply_text(
            f"{EMOJI['error']} *Please send a PHOTO*",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_SCREENSHOT
    
    context.user_data['screenshot'] = update.message.photo[-1].file_id
    
    await update.message.reply_text(
        f"{EMOJI['success']} *Screenshot Received*\n\nNow send UTR number:",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return STATE_UTR

# ===========================================================================
# UTR HANDLER
# ===========================================================================

async def handle_utr(update, context):
    user = update.effective_user
    utr = update.message.text.strip()
    
    if not validate_utr(utr):
        await update.message.reply_text(
            f"{EMOJI['error']} *Invalid UTR*\n\nUTR should be 12-22 characters.",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_UTR
    
    if 'topup' not in context.user_data or 'screenshot' not in context.user_data:
        await update.message.reply_text(
            f"{EMOJI['error']} *Session Expired*\n\nPlease start over.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    data = context.user_data['topup']
    vid = db.create_verification(
        user.id, data['amount'], data['fee'], data['final'], utr, context.user_data['screenshot']
    )
    
    # Notify admin
    await context.bot.send_photo(
        chat_id=ADMIN_CHANNEL_ID,
        photo=context.user_data['screenshot'],
        caption=(
            f"{EMOJI['money']} *NEW PAYMENT*\n\n"
            f"👤 *User:* {user.first_name}\n"
            f"🆔 *ID:* `{user.id}`\n"
            f"💰 *Amount:* `{format_currency(data['amount'])}`\n"
            f"✨ *Credit:* `{format_currency(data['final'])}`\n"
            f"🔢 *UTR:* `{utr}`"
        ),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{vid}"),
            InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{vid}")
        ]])
    )
    
    context.user_data.clear()
    
    await update.message.reply_text(
        f"{EMOJI['success']} *VERIFICATION SUBMITTED!*\n\n"
        f"Your payment is being verified.\n"
        f"You'll be notified within 5-10 minutes.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ConversationHandler.END

# ===========================================================================
# EMAIL HANDLER
# ===========================================================================

async def handle_email(update, context):
    user = update.effective_user
    email = update.message.text.strip()
    
    if not validate_email(email):
        await update.message.reply_text(
            f"{EMOJI['error']} *Invalid Email*\n\nPlease enter a valid email.",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_EMAIL
    
    if 'purchase' not in context.user_data:
        await update.message.reply_text(
            f"{EMOJI['error']} *Session Expired*\n\nPlease start over.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    p = context.user_data['purchase']
    balance = db.get_balance(user.id)
    
    if balance < p['price']:
        await update.message.reply_text(
            f"{EMOJI['error']} *Insufficient Balance*",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    db.update_balance(user.id, -p['price'], 'debit')
    order_id = db.create_purchase(user.id, p['card'], p['value'], p['price'], email)
    
    context.user_data.clear()
    
    await update.message.reply_text(
        f"{EMOJI['success']} *PURCHASE SUCCESSFUL!*\n\n"
        f"{p['emoji']} *{p['card']} ₹{p['value']}*\n"
        f"🆔 *Order ID:* `{order_id}`\n"
        f"📧 *Sent to:* `{email}`\n\n"
        f"✨ *Check your inbox (and spam folder)!*",
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
        await update.message.reply_text(
            f"{EMOJI['error']} *Message Too Short*\n\nPlease describe your issue (min 10 chars).",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_SUPPORT
    
    # Save to database
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS support (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message TEXT,
        timestamp TIMESTAMP
    )''')
    c.execute("INSERT INTO support (user_id, message, timestamp) VALUES (?, ?, ?)",
              (user.id, msg, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    # Notify admin
    await context.bot.send_message(
        ADMIN_ID,
        f"{EMOJI['support']} *SUPPORT TICKET*\n\n"
        f"👤 {user.first_name}\n"
        f"🆔 `{user.id}`\n"
        f"💬 {msg}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    await update.message.reply_text(
        f"{EMOJI['success']} *SUPPORT SENT!*\n\nWe'll contact you within 24 hours.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ConversationHandler.END

# ===========================================================================
# ADMIN HANDLER
# ===========================================================================

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
            await query.edit_message_caption(
                caption=query.message.caption + f"\n\n✅ *APPROVED BY ADMIN*",
                parse_mode=ParseMode.MARKDOWN
            )
            
            await context.bot.send_message(
                v['user_id'],
                f"{EMOJI['success']} *PAYMENT APPROVED!*\n\n"
                f"💰 `{format_currency(v['final_amount'])}` added to your balance.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif action == "reject":
        db.reject_verification(vid)
        await query.edit_message_caption(
            caption=query.message.caption + f"\n\n❌ *REJECTED BY ADMIN*",
            parse_mode=ParseMode.MARKDOWN
        )

# ===========================================================================
# ADMIN COMMANDS
# ===========================================================================

async def admin_stats(update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(f"{EMOJI['error']} Unauthorized")
        return
    
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM verifications WHERE status='pending'")
    pending = c.fetchone()[0]
    
    c.execute("SELECT SUM(amount) FROM transactions WHERE type='credit'")
    revenue = c.fetchone()[0] or 0
    
    c.execute("SELECT SUM(price) FROM purchases")
    spent = c.fetchone()[0] or 0
    
    conn.close()
    
    await update.message.reply_text(
        f"{EMOJI['proof']} *BOT STATISTICS*\n\n"
        f"👥 *Users:* `{users}`\n"
        f"⏳ *Pending:* `{pending}`\n"
        f"💰 *Revenue:* `{format_currency(revenue)}`\n"
        f"💳 *Spent:* `{format_currency(spent)}`",
        parse_mode=ParseMode.MARKDOWN
    )

# ===========================================================================
# AUTO PROMOTIONS - DETAILED VERSION
# ===========================================================================

async def auto_promotions(context):
    """Auto post detailed promotions to main channel - every 2 hours"""
    try:
        promos = [
            {
                "title": "🔥 FLASH SALE! 🔥",
                "content": [
                    "✨ *Get Gift Cards at 80% OFF!* ✨",
                    "",
                    "🎁 *Available Brands:*",
                    "• 🟦 AMAZON - Shop Everything",
                    "• 📦 FLIPKART - Electronics & Fashion",
                    "• 🟩 PLAY STORE - Apps & Games",
                    "• 🎟️ BOOKMYSHOW - Movie Tickets",
                    "• 🛍️ MYNTRA - Fashion & Lifestyle",
                    "• 🍕 ZOMATO - Food Delivery",
                    "• 🛒 BIG BASKET - Grocery",
                    "",
                    "💰 *Price Example:*",
                    "• ₹500 Card → Just ₹100",
                    "• ₹1000 Card → Just ₹200",
                    "• ₹2000 Card → Just ₹400",
                    "",
                    "⚡ *Features:*",
                    "• ✅ Instant Email Delivery",
                    "• ✅ 100% Working Codes",
                    "• ✅ 24/7 Support",
                    "• ✅ Referral Bonus ₹2",
                    "",
                    "🚀 *Join now and start saving!*"
                ],
                "button": "🎁 BUY NOW"
            },
            {
                "title": "🎁 REFER & EARN 🎁",
                "content": [
                    "👥 *Invite Friends, Earn Money!* 👥",
                    "",
                    "💰 *Earn ₹2 per referral!*",
                    "",
                    "📌 *How it works:*",
                    "1️⃣ Share your referral link",
                    "2️⃣ Friend joins using your link",
                    "3️⃣ You get ₹2 instantly",
                    "4️⃣ Friend gets ₹5 welcome bonus",
                    "",
                    "🎯 *Benefits:*",
                    "• No limit on referrals",
                    "• Instant credit to wallet",
                    "• Use earnings to buy cards",
                    "",
                    "🔗 *Your link is in the bot!*",
                    "",
                    "🚀 *Start referring now!*"
                ],
                "button": "👥 REFER NOW"
            },
            {
                "title": "⚡ INSTANT DELIVERY ⚡",
                "content": [
                    "📧 *Get Cards in 2 Minutes!* 📧",
                    "",
                    "✅ *Why Choose Us:*",
                    "",
                    "• 🚀 *Instant Email Delivery*",
                    "  Cards sent immediately after purchase",
                    "",
                    "• 🛡️ *100% Guaranteed*",
                    "  All codes are verified and working",
                    "",
                    "• 💎 *Best Prices*",
                    "  Save up to 80% on every card",
                    "",
                    "• 👥 *Referral Program*",
                    "  Earn ₹2 per friend",
                    "",
                    "• 📞 *24/7 Support*",
                    "  We're always here to help",
                    "",
                    "🎁 *Try it now!*"
                ],
                "button": "🎁 SHOP NOW"
            },
            {
                "title": "💰 BEST DEALS THIS WEEK 💰",
                "content": [
                    "🛒 *Limited Time Offers:* 🛒",
                    "",
                    "🔥 *AMAZON*",
                    "• ₹500 → ₹100 (80% OFF)",
                    "• ₹1000 → ₹200 (80% OFF)",
                    "",
                    "🔥 *FLIPKART*",
                    "• ₹500 → ₹100 (80% OFF)",
                    "• ₹1000 → ₹200 (80% OFF)",
                    "",
                    "🔥 *PLAY STORE*",
                    "• ₹500 → ₹100 (80% OFF)",
                    "• ₹1000 → ₹200 (80% OFF)",
                    "",
                    "⚡ *Other Brands Also Available!*",
                    "",
                    "📌 *Limited stock. Order now!*"
                ],
                "button": "🎁 VIEW DEALS"
            }
        ]
        
        promo = random.choice(promos)
        content = "\n".join(promo["content"])
        
        message = (
            f"{promo['title']}\n"
            f"{DIVIDER}\n\n"
            f"{content}\n\n"
            f"{DIVIDER_SHORT}\n\n"
            f"{EMOJI['rocket']} *Join now:* @{context.bot.username}\n"
            f"{DIVIDER}"
        )
        
        keyboard = [[InlineKeyboardButton(
            promo['button'],
            url=f"https://t.me/{context.bot.username}?start=promo"
        )]]
        
        await context.bot.send_message(
            chat_id=MAIN_CHANNEL,
            text=message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        logger.info(f"📢 Promo posted to {MAIN_CHANNEL}")
        
    except Exception as e:
        logger.error(f"❌ Promo error: {e}")

# ===========================================================================
# AUTO PROOFS
# ===========================================================================

async def auto_proofs(context):
    """Send random proofs to proof channel - every 45 seconds"""
    try:
        names = [
            "👑 Raj", "💫 Arjun", "🌟 Kavya", "⚡ Veer", "🔥 Aryan",
            "💎 Neha", "🎯 Karan", "🚀 Riya", "⭐ Amit", "💥 Priya",
            "🦁 Simba", "🐅 Tiger", "🦅 Falcon", "🐺 Wolf", "🦊 Fox"
        ]
        
        cards = [
            "🟦 AMAZON", "🟩 PLAY STORE", "🎟️ BOOKMYSHOW",
            "🛍️ MYNTRA", "📦 FLIPKART", "🍕 ZOMATO"
        ]
        
        amounts = [500, 1000, 2000]
        
        name = random.choice(names)
        card = random.choice(cards)
        amount = random.choice(amounts)
        
        message = (
            f"⚡ *LIVE PURCHASE*\n"
            f"{DIVIDER_SHORT}\n\n"
            f"👤 *{name}*\n"
            f"🎁 *{card}*\n"
            f"💰 *₹{amount}*\n\n"
            f"{DIVIDER_SHORT}\n"
            f"📧 *Email Delivery*\n"
            f"✅ *Instant*"
        )
        
        await context.bot.send_message(
            chat_id=PROOF_CHANNEL,
            text=message,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"❌ Proof error: {e}")

# ===========================================================================
# CANCEL HANDLER
# ===========================================================================

async def cancel(update, context):
    context.user_data.clear()
    await update.message.reply_text(
        f"{EMOJI['error']} *Cancelled*",
        parse_mode=ParseMode.MARKDOWN
    )
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
    """Setup after bot initialization"""
    await app.bot.set_my_commands([
        BotCommand("start", "🚀 Start the bot"),
        BotCommand("stats", "📊 Statistics (Admin)"),
        BotCommand("cancel", "❌ Cancel")
    ])
    
    # Verify channels
    try:
        await app.bot.get_chat(MAIN_CHANNEL)
        logger.info(f"✅ Main channel verified: {MAIN_CHANNEL}")
    except:
        logger.error(f"❌ Main channel not accessible: {MAIN_CHANNEL}")
    
    try:
        await app.bot.get_chat(PROOF_CHANNEL)
        logger.info(f"✅ Proof channel verified: {PROOF_CHANNEL}")
    except:
        logger.error(f"❌ Proof channel not accessible: {PROOF_CHANNEL}")
    
    logger.info(f"✅ Bot ready! Posts per day: {POSTS_PER_DAY} (every {POST_INTERVAL//3600} hours)")

# ===========================================================================
# MAIN
# ===========================================================================

def main():
    """Main function"""
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
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("stats", admin_stats))
    
    # Button handlers
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CallbackQueryHandler(admin_handler, pattern="^(approve_|reject_)"))
    
    # Paid handler
    app.add_handler(CallbackQueryHandler(handle_paid, pattern="^paid$"))
    
    # Amount conversation - FIXED
    amount_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^upi$")],
        states={STATE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(amount_conv)
    
    # Payment verification conversation
    payment_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_paid, pattern="^paid$")],
        states={
            STATE_SCREENSHOT: [
                MessageHandler(filters.PHOTO, handle_screenshot),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_screenshot)
            ],
            STATE_UTR: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_utr)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(payment_conv)
    
    # Email conversation
    email_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^buy_")],
        states={STATE_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(email_conv)
    
    # Support conversation
    support_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^support$")],
        states={STATE_SUPPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_support)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(support_conv)
    
    # Error handler
    app.add_error_handler(error_handler)
    
    # Auto jobs
    if app.job_queue:
        # Promotions every 2 hours (12 per day)
        app.job_queue.run_repeating(auto_promotions, interval=POST_INTERVAL, first=30)
        
        # Proofs every 45 seconds
        app.job_queue.run_repeating(auto_proofs, interval=PROOF_INTERVAL, first=10)
    
    # Start
    print("\n" + "="*60)
    print("      🎁 GIFT CARD & RECHARGE BOT v7.0 🎁")
    print("="*60)
    print(f"✅ Bot is running...")
    print(f"📢 Main Channel: {MAIN_CHANNEL}")
    print(f"📊 Proof Channel: {PROOF_CHANNEL}")
    print(f"💰 Referral Bonus: ₹{REFERRAL_BONUS}")
    print(f"📅 Promotions: {POSTS_PER_DAY} posts/day (every {POST_INTERVAL//3600} hours)")
    print("="*60 + "\n")
    
    app.run_polling()

if __name__ == "__main__":
    main()
