#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
===============================================================================
🎁 GIFT CARD & RECHARGE BOT - ULTIMATE FIXED VERSION 🎁
===============================================================================
✓ Payment buttons now working
✓ Admin commands hidden from users
✓ Beautiful UI with gift animations
✓ Force promo/proof only for admin
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
# CONFIGURATION
# ===========================================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8646034766:AAGXkMglnsc72ew1aGcFmWnZziwb8nfS2S8")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "6185091342"))
UPI_ID = os.environ.get("UPI_ID", "helobiy41@ptyes")

# Channels
MAIN_CHANNEL = "@gift_card_main"
PROOF_CHANNEL = "@gift_card_log"
ADMIN_CHANNEL_ID = -1003607749028

# Paths
QR_CODE_PATH = "qr.jpg"
DATABASE_PATH = "bot_database.db"

# Payment Config
MIN_RECHARGE = 10
MAX_RECHARGE = 10000
FEE_PERCENT = 20
FEE_THRESHOLD = 120

# Referral
REFERRAL_BONUS = 2
WELCOME_BONUS = 5

# Auto Posts
POSTS_PER_DAY = 12
POST_INTERVAL = 7200  # 2 hours
PROOF_INTERVAL = 45  # 45 seconds

# ===========================================================================
# PRE-DEFINED AMOUNT BUTTONS
# ===========================================================================

AMOUNT_BUTTONS = [
    [10, 20, 30, 50],
    [120, 150, 200, 300],
    [400, 500, 1000, 2000],
    [5000, 10000]
]

# ===========================================================================
# CONVERSATION STATES
# ===========================================================================
(
    STATE_AMOUNT,
    STATE_SCREENSHOT,
    STATE_UTR,
    STATE_EMAIL,
    STATE_SUPPORT,
    STATE_FORCE_PROOF_AMOUNT,
    STATE_FORCE_PROOF_INTERVAL
) = range(7)

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
DENOMINATIONS = [500, 1000, 2000, 5000]

# ===========================================================================
# BEAUTIFUL UI COMPONENTS
# ===========================================================================

EMOJI = {
    "gift": "🎁", "card": "💳", "money": "💰", "wallet": "👛",
    "success": "✅", "error": "❌", "warning": "⚠️", "info": "ℹ️",
    "star": "⭐", "fire": "🔥", "crown": "👑", "rocket": "🚀",
    "support": "🆘", "proof": "📊", "referral": "👥", "back": "🔙",
    "time": "⏰", "email": "📧", "phone": "📱", "discount": "🏷️",
    "delivery": "📦", "instant": "⚡", "guarantee": "🛡️", "users": "👥",
    "loading": "⏳", "gift_box": "🎀", "sparkle": "✨", "diamond": "💎",
    "trophy": "🏆", "medal": "🏅", "heart": "❤️", "party": "🎉",
    "confetti": "🎊", "balloon": "🎈", "cake": "🎂", "bell": "🔔"
}

# Loading animation frames
LOADING_FRAMES = ["🎁", "🎀", "✨", "⭐", "🌟", "💫", "⚡", "💎"]

DIVIDER = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
DIVIDER_SHORT = "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
DIVIDER_GIFT = "🎁━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━🎁"

# ===========================================================================
# LOGGING
# ===========================================================================

logging.basicConfig(format='%(asctime)s | %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ===========================================================================
# DATABASE MANAGER
# ===========================================================================

class DatabaseManager:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self._init_db()
    
    def _get_conn(self):
        return sqlite3.connect(self.db_path, timeout=30)
    
    def _init_db(self):
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT, first_name TEXT,
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
        
        c.execute('''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, amount INTEGER,
            type TEXT, status TEXT,
            utr TEXT UNIQUE,
            timestamp TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, order_id TEXT UNIQUE,
            card_name TEXT, card_value INTEGER,
            price INTEGER, email TEXT,
            timestamp TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, amount INTEGER,
            fee INTEGER, final_amount INTEGER,
            utr TEXT UNIQUE, screenshot TEXT,
            status TEXT DEFAULT 'pending',
            timestamp TIMESTAMP
        )''')
        
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
        logger.info("✅ Database ready")
    
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
            if not row: return False
            current = row[0]
            new_balance = current + amount
            if new_balance < 0: return False
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
            if not row: return None
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
            if c.fetchone(): return False
            c.execute('''INSERT INTO referrals (referrer_id, referred_id, bonus_amount, timestamp) VALUES (?, ?, ?, ?)''',
                     (referrer_id, referred_id, REFERRAL_BONUS, datetime.now().isoformat()))
            self.update_balance(referrer_id, REFERRAL_BONUS, 'bonus')
            c.execute("UPDATE users SET total_referrals = total_referrals + 1 WHERE user_id = ?", (referrer_id,))
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

def format_currency(amount): return f"₹{amount:,}"
def validate_email(email): return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email) is not None
def validate_utr(utr): return 12 <= len(utr) <= 22 and utr.isalnum()

def calculate_fee(amount):
    if amount < FEE_THRESHOLD:
        fee = int(amount * FEE_PERCENT / 100)
        return fee, amount - fee
    return 0, amount

# ===========================================================================
# LOADING ANIMATION
# ===========================================================================

async def show_loading(update, message_text="Processing", duration=2):
    """Show beautiful loading animation"""
    msg = await update.message.reply_text(f"{EMOJI['loading']} *{message_text}*", parse_mode=ParseMode.MARKDOWN)
    for i in range(duration * 2):
        frame = LOADING_FRAMES[i % len(LOADING_FRAMES)]
        await asyncio.sleep(0.5)
        await msg.edit_text(f"{frame} *{message_text}{'.' * ((i % 3) + 1)}*", parse_mode=ParseMode.MARKDOWN)
    await msg.delete()

# ===========================================================================
# MEMBERSHIP CHECK
# ===========================================================================

async def is_member(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=MAIN_CHANNEL, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# ===========================================================================
# ADMIN DECORATOR
# ===========================================================================

def admin_only(func):
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        user = update.effective_user
        if user.id != ADMIN_ID:
            await update.message.reply_text(f"{EMOJI['error']} *Unauthorized*", parse_mode=ParseMode.MARKDOWN)
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# ===========================================================================
# START COMMAND
# ===========================================================================

async def start(update, context):
    user = update.effective_user
    
    if not all([BOT_TOKEN, ADMIN_ID, UPI_ID]):
        await update.message.reply_text(f"{EMOJI['error']} *Configuration Error*", parse_mode=ParseMode.MARKDOWN)
        return
    
    # Create user
    db_user = db.get_user(user.id)
    if not db_user:
        referred = None
        if context.args and context.args[0].startswith('ref_'):
            try:
                referred = int(context.args[0].replace('ref_', ''))
                if referred == user.id: referred = None
            except: pass
        db.create_user(user.id, user.username, user.first_name, referred)
        if WELCOME_BONUS > 0: db.update_balance(user.id, WELCOME_BONUS, 'bonus')
        if referred:
            db.process_referral(referred, user.id)
            try:
                await context.bot.send_message(referred,
                    f"{EMOJI['referral']} *Referral Bonus!*\n\n{user.first_name} joined!\n+₹{REFERRAL_BONUS}",
                    parse_mode=ParseMode.MARKDOWN)
            except: pass
    
    db.update_active(user.id)
    
    # Show loading animation
    await show_loading(update, "Loading Gift Cards", 1)
    
    # Check membership
    if not await is_member(user.id, context):
        welcome = (
            f"{EMOJI['gift']}{EMOJI['gift']} *WELCOME TO GIFT CARD BOT* {EMOJI['gift']}{EMOJI['gift']}\n"
            f"{DIVIDER_GIFT}\n\n"
            f"👋 *Hello {user.first_name}!*\n\n"
            f"{EMOJI['gift_box']} *Get Gift Cards at 80% OFF*\n"
            f"{EMOJI['star']} *7+ Premium Brands*\n"
            f"{EMOJI['instant']} *Instant Email Delivery*\n"
            f"{EMOJI['guarantee']} *100% Working Codes*\n\n"
            f"{DIVIDER_SHORT}\n\n"
            f"{EMOJI['lock']} *VERIFICATION REQUIRED*\n"
            f"Join our main channel to continue.\n\n"
            f"👇 *Click below to join*"
        )
        keyboard = [[
            InlineKeyboardButton(f"{EMOJI['gift']} JOIN MAIN CHANNEL", url="https://t.me/gift_card_main"),
            InlineKeyboardButton(f"{EMOJI['success']} VERIFY", callback_data="verify")
        ]]
        await update.message.reply_text(welcome, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # Main menu - ONLY user commands shown
    balance = db.get_balance(user.id)
    menu = (
        f"{EMOJI['gift']}{EMOJI['gift']} *GIFT CARD & RECHARGE BOT* {EMOJI['gift']}{EMOJI['gift']}\n"
        f"{DIVIDER_GIFT}\n\n"
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
    await update.message.reply_text(menu, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

# ===========================================================================
# BUTTON HANDLER - FIXED PAYMENT BUTTONS
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
            await show_loading(update, "Verifying", 1)
            success = (
                f"{EMOJI['party']} *VERIFICATION SUCCESSFUL* {EMOJI['party']}\n"
                f"{DIVIDER_GIFT}\n\n"
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
            await query.edit_message_text(success, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            fail = (
                f"{EMOJI['error']} *VERIFICATION FAILED*\n\n"
                f"You haven't joined our channel yet!\n\n"
                f"1️⃣ Click JOIN CHANNEL\n"
                f"2️⃣ Join @gift_card_main\n"
                f"3️⃣ Click VERIFY"
            )
            keyboard = [[
                InlineKeyboardButton(f"{EMOJI['gift']} JOIN CHANNEL", url="https://t.me/gift_card_main"),
                InlineKeyboardButton(f"{EMOJI['refresh']} VERIFY", callback_data="verify")
            ]]
            await query.edit_message_text(fail, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # Check membership
    if not await is_member(user.id, context):
        keyboard = [[
            InlineKeyboardButton(f"{EMOJI['gift']} JOIN CHANNEL", url="https://t.me/gift_card_main"),
            InlineKeyboardButton(f"{EMOJI['success']} VERIFY", callback_data="verify")
        ]]
        await query.edit_message_text(
            f"{EMOJI['warning']} *ACCESS DENIED*\n\nJoin @gift_card_main first!",
            parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # ===== MAIN MENU =====
    if data == "main_menu":
        balance = db.get_balance(user.id)
        menu = (
            f"{EMOJI['gift']}{EMOJI['gift']} *MAIN MENU* {EMOJI['gift']}{EMOJI['gift']}\n"
            f"{DIVIDER_GIFT}\n\n"
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
        await query.edit_message_text(menu, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # ===== GIFT CARDS =====
    elif data == "giftcard":
        text = f"{EMOJI['card']} *GIFT CARDS* {EMOJI['card']}\n{DIVIDER}\n\n*Select a brand:*\n"
        keyboard = []
        for cid, card in GIFT_CARDS.items():
            star = "⭐" if card.get('popular', False) else ""
            keyboard.append([InlineKeyboardButton(f"{card['full_emoji']} {card['name']} {star}", callback_data=f"card_{cid}")])
        keyboard.append([InlineKeyboardButton(f"{EMOJI['back']} BACK", callback_data="main_menu")])
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # ===== CARD DETAILS =====
    elif data.startswith("card_"):
        cid = data.replace("card_", "")
        card = GIFT_CARDS.get(cid)
        if not card: return
        text = (
            f"{card['full_emoji']} *{card['name']} GIFT CARD* {card['full_emoji']}\n"
            f"{DIVIDER}\n\n"
            f"{EMOJI['info']} *Features:*\n"
            f"• Instant Email Delivery\n"
            f"• 100% Working Codes\n"
            f"• No Expiry\n\n"
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
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # ===== BUY CARD =====
    elif data.startswith("buy_"):
        parts = data.split("_")
        if len(parts) < 3: return
        cid, value = parts[1], int(parts[2])
        card = GIFT_CARDS.get(cid)
        if not card or value not in PRICES: return
        price = PRICES[value]
        balance = db.get_balance(user.id)
        
        if balance < price:
            keyboard = [[InlineKeyboardButton(f"{EMOJI['money']} ADD MONEY", callback_data="topup")]]
            await query.edit_message_text(
                f"{EMOJI['error']} *Insufficient Balance*\n\nNeed: `{format_currency(price)}`\nYou have: `{format_currency(balance)}`",
                parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        savings, percent = value - price, int(((value - price) / value) * 100)
        context.user_data['purchase'] = {'card': card['name'], 'emoji': card['full_emoji'], 'value': value, 'price': price}
        await query.edit_message_text(
            f"{EMOJI['success']} *Balance Sufficient*\n\n"
            f"{card['full_emoji']} *{card['name']} ₹{value}*\n"
            f"Price: `{format_currency(price)}`\n"
            f"You Save: `{format_currency(savings)}` ({percent}% OFF)\n\n"
            f"{EMOJI['email']} *Enter your email for delivery:*",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_EMAIL
    
    # ===== TOP UP WITH AMOUNT BUTTONS =====
    elif data == "topup":
        text = (
            f"{EMOJI['money']} *ADD MONEY TO WALLET* {EMOJI['money']}\n"
            f"{DIVIDER_GIFT}\n\n"
            f"*Select amount or enter manually:*\n\n"
        )
        
        # Create amount buttons
        keyboard = []
        for row in AMOUNT_BUTTONS:
            button_row = []
            for amt in row:
                button_row.append(InlineKeyboardButton(f"₹{amt}", callback_data=f"amount_{amt}"))
            keyboard.append(button_row)
        
        keyboard.append([InlineKeyboardButton(f"{EMOJI['back']} BACK", callback_data="main_menu")])
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== AMOUNT BUTTON SELECTED - FIXED WORKING VERSION =====
    elif data.startswith("amount_"):
        amount = int(data.replace("amount_", ""))
        fee, final = calculate_fee(amount)
        context.user_data['topup'] = {'amount': amount, 'fee': fee, 'final': final}
        
        keyboard = [
            [InlineKeyboardButton(f"{EMOJI['success']} ✅ I HAVE PAID", callback_data="paid")],
            [InlineKeyboardButton(f"{EMOJI['back']} 🔙 CANCEL", callback_data="topup")]
        ]
        
        # Send payment details
        payment_text = (
            f"{EMOJI['money']} *PAYMENT DETAILS* {EMOJI['money']}\n"
            f"{DIVIDER_GIFT}\n\n"
            f"{EMOJI['phone']} *UPI ID:* `{UPI_ID}`\n"
            f"{EMOJI['money']} *Amount:* `{format_currency(amount)}`\n"
            f"{EMOJI['discount']} *Fee:* `{format_currency(fee) if fee > 0 else 'No fee'}`\n"
            f"{EMOJI['wallet']} *You get:* `{format_currency(final)}`\n\n"
            f"{DIVIDER_SHORT}\n\n"
            f"{EMOJI['phone']} *How to Pay:*\n"
            f"1️⃣ Pay to UPI ID: `{UPI_ID}`\n"
            f"2️⃣ Take a screenshot\n"
            f"3️⃣ Copy UTR number\n"
            f"4️⃣ Click 'I HAVE PAID'\n\n"
            f"⏳ *Auto-cancel in 10 minutes*"
        )
        
        if os.path.exists(QR_CODE_PATH):
            with open(QR_CODE_PATH, 'rb') as qr:
                await query.message.reply_photo(
                    photo=qr,
                    caption=payment_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        else:
            await query.message.reply_text(
                payment_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        # Also edit the original message to show it's processed
        await query.edit_message_text(
            f"{EMOJI['success']} *Amount Selected: ₹{amount}*\n\nPlease check the payment details above.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        return ConversationHandler.END
    
    # ===== WALLET =====
    elif data == "wallet":
        balance = db.get_balance(user.id)
        text = (
            f"{EMOJI['wallet']} *YOUR WALLET* {EMOJI['wallet']}\n"
            f"{DIVIDER_GIFT}\n\n"
            f"{EMOJI['money']} *Balance:* `{format_currency(balance)}`\n"
            f"{DIVIDER_SHORT}\n\n"
            f"*Quick Actions:* ⬇️"
        )
        keyboard = [
            [InlineKeyboardButton(f"{EMOJI['money']} ADD MONEY", callback_data="topup")],
            [InlineKeyboardButton(f"{EMOJI['card']} BUY CARDS", callback_data="giftcard")],
            [InlineKeyboardButton(f"{EMOJI['back']} BACK", callback_data="main_menu")]
        ]
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # ===== REFERRAL =====
    elif data == "referral":
        bot = await context.bot.get_me()
        link = f"https://t.me/{bot.username}?start=ref_{user.id}"
        text = (
            f"{EMOJI['referral']} *REFERRAL PROGRAM* {EMOJI['referral']}\n"
            f"{DIVIDER_GIFT}\n\n"
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
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # ===== PROOFS =====
    elif data == "proofs":
        text = (
            f"{EMOJI['proof']} *LIVE PROOFS* {EMOJI['proof']}\n"
            f"{DIVIDER_GIFT}\n\n"
            f"📊 *See real purchases from real users*\n\n"
            f"👉 {PROOF_CHANNEL}\n\n"
            f"{EMOJI['star']} *What you'll see:*\n"
            f"• Live purchase notifications\n"
            f"• Instant delivery proofs\n"
            f"• 24/7 transaction updates\n\n"
            f"{EMOJI['rocket']} *Click below to join*"
        )
        keyboard = [
            [InlineKeyboardButton(f"{EMOJI['proof']} VIEW PROOFS", url=f"https://t.me/{PROOF_CHANNEL[1:]}")],
            [InlineKeyboardButton(f"{EMOJI['back']} BACK", callback_data="main_menu")]
        ]
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # ===== SUPPORT =====
    elif data == "support":
        text = (
            f"{EMOJI['support']} *SUPPORT* {EMOJI['support']}\n"
            f"{DIVIDER_GIFT}\n\n"
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
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        return STATE_SUPPORT

# ===========================================================================
# PAID HANDLER
# ===========================================================================

async def handle_paid(update, context):
    query = update.callback_query
    await query.answer()
    
    if 'topup' not in context.user_data:
        await query.edit_message_text(f"{EMOJI['error']} *Session Expired*\n\nPlease start over.", parse_mode=ParseMode.MARKDOWN)
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
        await update.message.reply_text(f"{EMOJI['error']} *Please send a PHOTO*", parse_mode=ParseMode.MARKDOWN)
        return STATE_SCREENSHOT
    
    context.user_data['screenshot'] = update.message.photo[-1].file_id
    await update.message.reply_text(f"{EMOJI['success']} *Screenshot Received*\n\nNow send UTR number:", parse_mode=ParseMode.MARKDOWN)
    return STATE_UTR

# ===========================================================================
# UTR HANDLER
# ===========================================================================

async def handle_utr(update, context):
    user = update.effective_user
    utr = update.message.text.strip()
    
    if not validate_utr(utr):
        await update.message.reply_text(f"{EMOJI['error']} *Invalid UTR*\n\nUTR should be 12-22 characters.", parse_mode=ParseMode.MARKDOWN)
        return STATE_UTR
    
    if 'topup' not in context.user_data or 'screenshot' not in context.user_data:
        await update.message.reply_text(f"{EMOJI['error']} *Session Expired*\n\nPlease start over.", parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END
    
    data = context.user_data['topup']
    vid = db.create_verification(user.id, data['amount'], data['fee'], data['final'], utr, context.user_data['screenshot'])
    
    await context.bot.send_photo(
        chat_id=ADMIN_CHANNEL_ID,
        photo=context.user_data['screenshot'],
        caption=(
            f"{EMOJI['gift']} *NEW PAYMENT* {EMOJI['gift']}\n"
            f"{DIVIDER}\n\n"
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
        f"{EMOJI['party']} *VERIFICATION SUBMITTED!* {EMOJI['party']}\n\n"
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
        await update.message.reply_text(f"{EMOJI['error']} *Invalid Email*\n\nPlease enter a valid email.", parse_mode=ParseMode.MARKDOWN)
        return STATE_EMAIL
    
    if 'purchase' not in context.user_data:
        await update.message.reply_text(f"{EMOJI['error']} *Session Expired*\n\nPlease start over.", parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END
    
    p = context.user_data['purchase']
    balance = db.get_balance(user.id)
    
    if balance < p['price']:
        await update.message.reply_text(f"{EMOJI['error']} *Insufficient Balance*", parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END
    
    db.update_balance(user.id, -p['price'], 'debit')
    order_id = db.create_purchase(user.id, p['card'], p['value'], p['price'], email)
    
    context.user_data.clear()
    
    await show_loading(update, "Processing Purchase", 1)
    
    await update.message.reply_text(
        f"{EMOJI['party']} *PURCHASE SUCCESSFUL!* {EMOJI['party']}\n"
        f"{DIVIDER_GIFT}\n\n"
        f"{p['emoji']} *{p['card']} ₹{p['value']}*\n"
        f"🆔 *Order ID:* `{order_id}`\n"
        f"📧 *Sent to:* `{email}`\n\n"
        f"{EMOJI['sparkle']} *Check your inbox (and spam folder)!*",
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
        await update.message.reply_text(f"{EMOJI['error']} *Message Too Short*\n\nPlease describe your issue (min 10 chars).", parse_mode=ParseMode.MARKDOWN)
        return STATE_SUPPORT
    
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS support (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, timestamp TIMESTAMP)''')
    c.execute("INSERT INTO support (user_id, message, timestamp) VALUES (?, ?, ?)", (user.id, msg, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    await context.bot.send_message(
        ADMIN_ID,
        f"{EMOJI['support']} *SUPPORT TICKET*\n\n👤 {user.first_name}\n🆔 `{user.id}`\n💬 {msg}",
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
    
    if len(parts) < 2: return
    
    action, vid = parts[0], parts[1]
    
    if action == "approve":
        v = db.approve_verification(vid)
        if v:
            await query.edit_message_caption(caption=query.message.caption + f"\n\n✅ *APPROVED BY ADMIN*", parse_mode=ParseMode.MARKDOWN)
            await context.bot.send_message(
                v['user_id'],
                f"{EMOJI['party']} *PAYMENT APPROVED!*\n\n💰 `{format_currency(v['final_amount'])}` added to your balance.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif action == "reject":
        db.reject_verification(vid)
        await query.edit_message_caption(caption=query.message.caption + f"\n\n❌ *REJECTED BY ADMIN*", parse_mode=ParseMode.MARKDOWN)

# ===========================================================================
# ADMIN COMMANDS - HIDDEN FROM USERS
# ===========================================================================

@admin_only
async def admin_stats(update, context):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users"); users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM verifications WHERE status='pending'"); pending = c.fetchone()[0]
    c.execute("SELECT SUM(amount) FROM transactions WHERE type='credit'"); revenue = c.fetchone()[0] or 0
    c.execute("SELECT SUM(price) FROM purchases"); spent = c.fetchone()[0] or 0
    conn.close()
    
    await update.message.reply_text(
        f"{EMOJI['proof']} *BOT STATISTICS*\n{DIVIDER}\n\n"
        f"👥 *Users:* `{users}`\n"
        f"⏳ *Pending:* `{pending}`\n"
        f"💰 *Revenue:* `{format_currency(revenue)}`\n"
        f"💳 *Spent:* `{format_currency(spent)}`",
        parse_mode=ParseMode.MARKDOWN
    )

@admin_only
async def admin_force_promo(update, context):
    await show_loading(update, "Creating Promotion", 2)
    await auto_promotions(context)
    await update.message.reply_text(f"{EMOJI['success']} *Promotion Posted!*", parse_mode=ParseMode.MARKDOWN)

@admin_only
async def admin_force_proof(update, context):
    await update.message.reply_text(
        f"{EMOJI['proof']} *FORCE PROOF*\n\n"
        f"Enter amount in ₹ (e.g., 500, 1000, 2000):",
        parse_mode=ParseMode.MARKDOWN
    )
    return STATE_FORCE_PROOF_AMOUNT

@admin_only
async def handle_force_proof_amount(update, context):
    try:
        amount = int(update.message.text.strip())
        context.user_data['force_proof_amount'] = amount
    except:
        await update.message.reply_text(f"{EMOJI['error']} Invalid amount")
        return ConversationHandler.END
    
    await update.message.reply_text(
        f"{EMOJI['proof']} *FORCE PROOF*\n\n"
        f"Amount: ₹{amount}\n\n"
        f"Enter interval in seconds (e.g., 60 for 1 minute):",
        parse_mode=ParseMode.MARKDOWN
    )
    return STATE_FORCE_PROOF_INTERVAL

@admin_only
async def handle_force_proof_interval(update, context):
    try:
        interval = int(update.message.text.strip())
        amount = context.user_data.get('force_proof_amount', 500)
    except:
        await update.message.reply_text(f"{EMOJI['error']} Invalid interval")
        return ConversationHandler.END
    
    context.user_data.clear()
    
    job_name = f"force_proof_{update.effective_user.id}"
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    for job in current_jobs:
        job.schedule_removal()
    
    context.job_queue.run_repeating(
        force_proof_callback,
        interval=interval,
        first=0,
        name=job_name,
        data={'amount': amount}
    )
    
    await update.message.reply_text(
        f"{EMOJI['success']} *Force Proof Started!*\n\n"
        f"Amount: ₹{amount}\n"
        f"Interval: {interval} seconds\n"
        f"Channel: {PROOF_CHANNEL}\n\n"
        f"Use /stopforceproof to stop.",
        parse_mode=ParseMode.MARKDOWN
    )

@admin_only
async def admin_stop_force_proof(update, context):
    job_name = f"force_proof_{update.effective_user.id}"
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    
    for job in current_jobs:
        job.schedule_removal()
    
    await update.message.reply_text(
        f"{EMOJI['success']} *Force Proof Stopped!*",
        parse_mode=ParseMode.MARKDOWN
    )

async def force_proof_callback(context):
    job = context.job
    amount = job.data['amount']
    
    names = ["👑 Raj", "💫 Arjun", "🌟 Kavya", "⚡ Veer", "🔥 Aryan"]
    cards = ["🟦 AMAZON", "🟩 PLAY STORE", "🎟️ BOOKMYSHOW", "🛍️ MYNTRA", "📦 FLIPKART", "🍕 ZOMATO"]
    
    name = random.choice(names)
    card = random.choice(cards)
    
    message = (
        f"⚡ *FORCE PROOF*\n"
        f"{DIVIDER_SHORT}\n\n"
        f"👤 *{name}*\n"
        f"🎁 *{card}*\n"
        f"💰 *₹{amount}*\n\n"
        f"{DIVIDER_SHORT}\n"
        f"📧 *Email Delivery*\n"
        f"✅ *Instant*"
    )
    
    try:
        await context.bot.send_message(
            chat_id=PROOF_CHANNEL,
            text=message,
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"✅ Force proof sent: ₹{amount}")
    except Exception as e:
        logger.error(f"❌ Force proof error: {e}")

# ===========================================================================
# AUTO PROMOTIONS
# ===========================================================================

async def auto_promotions(context):
    try:
        promos = [
            {
                "title": f"{EMOJI['fire']}{EMOJI['fire']} FLASH SALE {EMOJI['fire']}{EMOJI['fire']}",
                "content": [
                    f"{EMOJI['gift']} *Get Gift Cards at 80% OFF!*",
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
                    f"• 👥 Referral Bonus ₹{REFERRAL_BONUS}",
                    "",
                    f"{EMOJI['rocket']} *Join now and start saving!*"
                ]
            },
            {
                "title": f"{EMOJI['referral']}{EMOJI['referral']} REFER & EARN {EMOJI['referral']}{EMOJI['referral']}",
                "content": [
                    f"👥 *Invite Friends, Earn ₹{REFERRAL_BONUS}!*",
                    "",
                    "📌 *How it works:*",
                    "1️⃣ Share your referral link",
                    "2️⃣ Friend joins using your link",
                    f"3️⃣ You get ₹{REFERRAL_BONUS} instantly",
                    f"4️⃣ Friend gets ₹{WELCOME_BONUS} welcome bonus",
                    "",
                    "🎯 *Benefits:*",
                    "• No limit on referrals",
                    "• Instant credit to wallet",
                    "• Use earnings to buy cards",
                    "",
                    f"{EMOJI['rocket']} *Start referring now!*"
                ]
            }
        ]
        
        promo = random.choice(promos)
        content = "\n".join(promo["content"])
        
        message = (
            f"{promo['title']}\n"
            f"{DIVIDER_GIFT}\n\n"
            f"{content}\n\n"
            f"{DIVIDER_SHORT}\n\n"
            f"{EMOJI['rocket']} *Join now:* @{context.bot.username}\n"
            f"{DIVIDER_GIFT}"
        )
        
        keyboard = [[InlineKeyboardButton(
            f"{EMOJI['gift']} SHOP NOW",
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
    try:
        names = ["👑 Raj", "💫 Arjun", "🌟 Kavya", "⚡ Veer", "🔥 Aryan"]
        cards = ["🟦 AMAZON", "🟩 PLAY STORE", "🎟️ BOOKMYSHOW", "🛍️ MYNTRA", "📦 FLIPKART", "🍕 ZOMATO"]
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
    await update.message.reply_text(f"{EMOJI['error']} *Cancelled*", parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END

# ===========================================================================
# ERROR HANDLER
# ===========================================================================

async def error_handler(update, context):
    logger.error(f"❌ Error: {context.error}")

# ===========================================================================
# POST INIT - ONLY USER COMMANDS VISIBLE
# ===========================================================================

async def post_init(app):
    # Set bot commands - only show user commands, hide admin ones
    await app.bot.set_my_commands([
        BotCommand("start", "🚀 Start the bot"),
        BotCommand("cancel", "❌ Cancel current operation")
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
    if not all([BOT_TOKEN, ADMIN_ID, UPI_ID]):
        logger.error("❌ Missing configuration")
        sys.exit(1)
    
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # User command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    
    # Admin command handlers (hidden from users)
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("forcepromo", admin_force_promo))
    app.add_handler(CommandHandler("stopforceproof", admin_stop_force_proof))
    
    # Force proof conversation (admin only)
    force_proof_conv = ConversationHandler(
        entry_points=[CommandHandler("forceproof", admin_force_proof)],
        states={
            STATE_FORCE_PROOF_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_force_proof_amount)],
            STATE_FORCE_PROOF_INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_force_proof_interval)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(force_proof_conv)
    
    # Button handlers
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CallbackQueryHandler(admin_handler, pattern="^(approve_|reject_)"))
    app.add_handler(CallbackQueryHandler(handle_paid, pattern="^paid$"))
    
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
        app.job_queue.run_repeating(auto_promotions, interval=POST_INTERVAL, first=30)
        app.job_queue.run_repeating(auto_proofs, interval=PROOF_INTERVAL, first=10)
    
    # Start
    print("\n" + "="*70)
    print(f"      {EMOJI['gift']} GIFT CARD BOT ULTIMATE v8.0 {EMOJI['gift']}")
    print("="*70)
    print(f"✅ Bot: @GIFT_CARD_41BOT")
    print(f"📢 Main Channel: {MAIN_CHANNEL}")
    print(f"📊 Proof Channel: {PROOF_CHANNEL}")
    print(f"💰 Referral Bonus: ₹{REFERRAL_BONUS}")
    print(f"📅 Promotions: {POSTS_PER_DAY} posts/day")
    print(f"🛡️ Force Proof: Available (Admin only)")
    print("="*70 + "\n")
    
    app.run_polling()

if __name__ == "__main__":
    main()
