#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
===============================================================================
🎬 GIFT CARD CINEMA - ULTIMATE EDITION 🎬
===============================================================================
A cinematic Telegram bot with stunning UI, animations, auto promotions,
and every feature you requested - now with BEAUTIFUL DESIGN!
===============================================================================
"""

import logging
import sqlite3
import asyncio
import random
import os
import sys
import re
import json
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

# ===========================================================================
# CINEMATIC CONFIGURATION
# ===========================================================================

# === ENVIRONMENT VARIABLES (SET THESE IN RAILWAY) ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8646034766:AAGXkMglnsc72ew1aGcFmWnZziwb8nfS2S8")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "6185091342"))
UPI_ID = os.environ.get("UPI_ID", "helobiy41@ptyes")

# === CHANNELS ===
MAIN_CHANNEL = "@gift_card_main"  # Your main channel
PROMO_CHANNEL = "@gift_card_main"  # Channel for auto promotions
PROOF_CHANNEL = "@gift_card_log"  # Channel for live proofs
ADMIN_CHANNEL_ID = -1003607749028

# === PATHS ===
QR_CODE_PATH = "qr.jpg"
DATABASE_PATH = "cinema_bot.db"

# === PAYMENT CONFIG ===
MIN_RECHARGE = 10
MAX_RECHARGE = 10000
FEE_PERCENT = 20
FEE_THRESHOLD = 120
REFERRAL_BONUS = 10
WELCOME_BONUS = 5

# === CINEMATIC UI THEME ===
THEME = {
    "primary": "🎬",      # Cinema
    "secondary": "✨",     # Sparkle
    "accent": "🌟",        # Star
    "success": "✅",       # Success
    "error": "❌",         # Error
    "warning": "⚠️",       # Warning
    "info": "ℹ️",          # Info
    "money": "💰",         # Money
    "card": "🎁",          # Gift
    "wallet": "💳",        # Wallet
    "support": "🆘",       # Support
    "proof": "📊",         # Proof
    "referral": "👥",      # Referral
    "back": "🔙",          # Back
    "next": "▶️",          # Next
    "prev": "◀️",          # Previous
    "menu": "📋",          # Menu
    "settings": "⚙️",      # Settings
    "crown": "👑",         # Crown
    "fire": "🔥",          # Fire
    "star": "⭐",           # Star
    "heart": "❤️",         # Heart
    "rocket": "🚀",        # Rocket
    "gem": "💎",           # Gem
    "trophy": "🏆",        # Trophy
    "medal": "🏅",         # Medal
}

# === CINEMATIC DIVIDERS ===
DIVIDER = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
DIVIDER_SHORT = "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
DIVIDER_DOTS = "⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯"
DIVIDER_STARS = "✧✧✧✧✧✧✧✧✧✧✧✧✧✧✧✧✧✧✧✧✧✧✧✧✧✧✧✧✧✧"

# === ANIMATION FRAMES ===
LOADING_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
SUCCESS_FRAMES = ["✨", "🌟", "⭐", "💫", "⚡"]
ERROR_FRAMES = ["❌", "💥", "🔥", "💢", "⚠️"]

# === GIFT CARDS - CINEMATIC EDITION ===
GIFT_CARDS = {
    "amazon": {
        "name": "AMAZON",
        "emoji": "🟦",
        "full_emoji": "🟦🎬",
        "cinematic": "🌌 AMAZON PRIME REALM",
        "tagline": "Shop Everything in the Universe",
        "color": "#FF9900",
        "popular": True,
        "exclusive": True
    },
    "flipkart": {
        "name": "FLIPKART",
        "emoji": "📦",
        "full_emoji": "📦🎬",
        "cinematic": "🚀 FLIPKART GALAXY",
        "tagline": "The Shopping Multiverse",
        "color": "#2874F0",
        "popular": True,
        "exclusive": True
    },
    "playstore": {
        "name": "PLAY STORE",
        "emoji": "🟩",
        "full_emoji": "🟩🎮",
        "cinematic": "🎮 GOOGLE PLAYVERSE",
        "tagline": "Apps, Games & Digital Dreams",
        "color": "#34A853",
        "popular": True,
        "exclusive": True
    },
    "bookmyshow": {
        "name": "BOOKMYSHOW",
        "emoji": "🎟️",
        "full_emoji": "🎟️🎬",
        "cinematic": "🎭 BOOKMYSHOW THEATER",
        "tagline": "Movies, Events & Entertainment",
        "color": "#C51C3E",
        "popular": True,
        "exclusive": False
    },
    "myntra": {
        "name": "MYNTRA",
        "emoji": "🛍️",
        "full_emoji": "🛍️👗",
        "cinematic": "👗 MYNTRA FASHIONVERSE",
        "tagline": "Style Beyond Reality",
        "color": "#E12B38",
        "popular": True,
        "exclusive": False
    },
    "zomato": {
        "name": "ZOMATO",
        "emoji": "🍕",
        "full_emoji": "🍕🍔",
        "cinematic": "🍽️ ZOMATO FEASTVERSE",
        "tagline": "Food Delivery from Another Dimension",
        "color": "#CB202D",
        "popular": True,
        "exclusive": False
    },
    "bigbasket": {
        "name": "BIG BASKET",
        "emoji": "🛒",
        "full_emoji": "🛒🥬",
        "cinematic": "🥬 BIG BASKET GROCERYVERSE",
        "tagline": "Fresh From the Future",
        "color": "#A7C83B",
        "popular": False,
        "exclusive": False
    },
    "netflix": {
        "name": "NETFLIX",
        "emoji": "🎬",
        "full_emoji": "🎬📺",
        "cinematic": "🎥 NETFLIX CINEMAVERSE",
        "tagline": "Streaming Beyond Imagination",
        "color": "#E50914",
        "popular": False,
        "exclusive": True
    },
    "spotify": {
        "name": "SPOTIFY",
        "emoji": "🎵",
        "full_emoji": "🎵🎧",
        "cinematic": "🎶 SPOTIFY AUDIOVERSE",
        "tagline": "Music for the Soul",
        "color": "#1DB954",
        "popular": False,
        "exclusive": True
    },
    "dream11": {
        "name": "DREAM11",
        "emoji": "🏏",
        "full_emoji": "🏏🎯",
        "cinematic": "🏆 DREAM11 SPORTSVERSE",
        "tagline": "Fantasy Sports Unleashed",
        "color": "#0F172A",
        "popular": False,
        "exclusive": False
    }
}

# === PRICE MATRIX ===
PRICES = {
    500: 100,
    1000: 200,
    2000: 400,
    3000: 600,
    5000: 1000,
    10000: 2000
}

DENOMINATIONS = [500, 1000, 2000, 3000, 5000, 10000]

# === CONVERSATION STATES ===
(
    STATE_AMOUNT,
    STATE_SCREENSHOT,
    STATE_UTR,
    STATE_EMAIL,
    STATE_SUPPORT,
    STATE_FEEDBACK,
    STATE_WITHDRAW,
    STATE_EXCHANGE,
    STATE_PROMO_CREATE
) = range(9)

# ===========================================================================
# CINEMATIC LOGGING
# ===========================================================================

class CinemaLogger:
    """Logging with cinematic flair"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._setup()
        return cls._instance
    
    def _setup(self):
        self.logger = logging.getLogger('CinemaBot')
        self.logger.setLevel(logging.INFO)
        
        # Console handler with colors
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        
        # Custom formatter with emojis
        class CinemaFormatter(logging.Formatter):
            def format(self, record):
                emoji_map = {
                    logging.INFO: "🎬",
                    logging.ERROR: "💥",
                    logging.WARNING: "⚠️",
                    logging.DEBUG: "🔍",
                    logging.CRITICAL: "🔥"
                }
                emoji = emoji_map.get(record.levelno, "📋")
                record.emoji = emoji
                return super().format(record)
        
        formatter = CinemaFormatter('%(emoji)s %(asctime)s | %(message)s')
        console.setFormatter(formatter)
        self.logger.addHandler(console)
    
    def info(self, msg): self.logger.info(msg)
    def error(self, msg): self.logger.error(msg)
    def warning(self, msg): self.logger.warning(msg)
    def debug(self, msg): self.logger.debug(msg)

log = CinemaLogger()

# ===========================================================================
# CINEMATIC DATABASE
# ===========================================================================

class CinemaDB:
    """Database with cinematic performance"""
    
    def __init__(self):
        self.db_path = DATABASE_PATH
        self._init()
        log.info("🎬 Cinema Database Initialized")
    
    def _connect(self):
        return sqlite3.connect(self.db_path, timeout=30)
    
    def _init(self):
        conn = self._connect()
        c = conn.cursor()
        
        # Users table - cinematic edition
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            balance INTEGER DEFAULT 0,
            bonus_balance INTEGER DEFAULT 0,
            total_recharged INTEGER DEFAULT 0,
            total_spent INTEGER DEFAULT 0,
            total_purchases INTEGER DEFAULT 0,
            total_referrals INTEGER DEFAULT 0,
            referral_code TEXT UNIQUE,
            referred_by INTEGER,
            join_date TIMESTAMP,
            last_active TIMESTAMP,
            vibe_score INTEGER DEFAULT 0,
            cinematic_tier TEXT DEFAULT 'BRONZE'
        )''')
        
        # Transactions table
        c.execute('''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            transaction_id TEXT UNIQUE,
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
        
        # Support tickets
        c.execute('''CREATE TABLE IF NOT EXISTS support (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            ticket_id TEXT UNIQUE,
            message TEXT,
            status TEXT DEFAULT 'open',
            timestamp TIMESTAMP
        )''')
        
        # Referrals
        c.execute('''CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_id INTEGER UNIQUE,
            bonus_amount INTEGER DEFAULT 10,
            status TEXT DEFAULT 'pending',
            timestamp TIMESTAMP
        )''')
        
        # Auto promotions
        c.execute('''CREATE TABLE IF NOT EXISTS promotions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT,
            media TEXT,
            schedule TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP,
            posted_at TIMESTAMP
        )''')
        
        conn.commit()
        conn.close()
    
    # === USER METHODS ===
    
    def get_user(self, user_id):
        conn = self._connect()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        return dict(zip([col[0] for col in c.description], row)) if row else None
    
    def create_user(self, user_id, username=None, first_name=None, referred_by=None):
        conn = self._connect()
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
        conn = self._connect()
        c = conn.cursor()
        c.execute("UPDATE users SET last_active = ? WHERE user_id = ?",
                 (datetime.now().isoformat(), user_id))
        conn.commit()
        conn.close()
    
    def get_balance(self, user_id):
        user = self.get_user(user_id)
        return user['balance'] if user else 0
    
    def update_balance(self, user_id, amount, txn_type, utr=None):
        conn = self._connect()
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
            
            tx_id = f"TXN{datetime.now().strftime('%y%m%d%H%M%S')}{random.randint(1000,9999)}"
            
            c.execute('''INSERT INTO transactions 
                (user_id, transaction_id, amount, type, status, utr, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (user_id, tx_id, abs(amount), txn_type, 'completed', utr, datetime.now().isoformat()))
            
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
            log.error(f"Balance error: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    # === VERIFICATION ===
    
    def create_verification(self, user_id, amount, fee, final, utr, screenshot):
        conn = self._connect()
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
        conn = self._connect()
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
        conn = self._connect()
        c = conn.cursor()
        c.execute("UPDATE verifications SET status = 'rejected' WHERE id = ?", (vid,))
        conn.commit()
        conn.close()
        return True
    
    # === PURCHASE ===
    
    def create_purchase(self, user_id, card_name, value, price, email):
        conn = self._connect()
        c = conn.cursor()
        order_id = f"GC{datetime.now().strftime('%y%m%d%H%M%S')}{random.randint(1000,9999)}"
        c.execute('''INSERT INTO purchases 
            (user_id, order_id, card_name, card_value, price, email, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (user_id, order_id, card_name, value, price, email, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return order_id
    
    # === REFERRAL ===
    
    def process_referral(self, referrer_id, referred_id):
        conn = self._connect()
        c = conn.cursor()
        try:
            c.execute("SELECT * FROM referrals WHERE referred_id = ?", (referred_id,))
            if c.fetchone():
                return False
            
            c.execute('''INSERT INTO referrals (referrer_id, referred_id, timestamp) VALUES (?, ?, ?)''',
                     (referrer_id, referred_id, datetime.now().isoformat()))
            
            self.update_balance(referrer_id, REFERRAL_BONUS, 'bonus')
            c.execute("UPDATE users SET total_referrals = total_referrals + 1 WHERE user_id = ?",
                     (referrer_id,))
            
            conn.commit()
            return True
        except:
            return False
        finally:
            conn.close()
    
    # === STATS ===
    
    def get_stats(self):
        conn = self._connect()
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM users")
        users = c.fetchone()[0]
        
        today = datetime.now().date().isoformat()
        c.execute("SELECT COUNT(*) FROM users WHERE date(last_active) = ?", (today,))
        active = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM verifications WHERE status='pending'")
        pending = c.fetchone()[0]
        
        c.execute("SELECT SUM(amount) FROM transactions WHERE type='credit'")
        revenue = c.fetchone()[0] or 0
        
        c.execute("SELECT SUM(price) FROM purchases")
        spent = c.fetchone()[0] or 0
        
        conn.close()
        return {
            'users': users,
            'active': active,
            'pending': pending,
            'revenue': revenue,
            'spent': spent
        }

# ===========================================================================
# CINEMATIC UI COMPONENTS
# ===========================================================================

class CinemaUI:
    """Beautiful UI components with animations"""
    
    @staticmethod
    def header(title, emoji="🎬"):
        """Cinematic header with animation"""
        return f"{emoji} *{title}* {emoji}\n{DIVIDER}\n"
    
    @staticmethod
    def section(title, emoji="✨"):
        """Section header"""
        return f"\n{emoji} *{title}* {emoji}\n{DIVIDER_SHORT}\n"
    
    @staticmethod
    def footer():
        """Footer with cinema credits"""
        return f"\n{DIVIDER_STARS}\n🎬 *GIFT CARD CINEMA* 🎬"
    
    @staticmethod
    def menu_button(text, emoji, callback):
        """Beautiful menu button"""
        return InlineKeyboardButton(f"{emoji} {text}", callback_data=callback)
    
    @staticmethod
    async def loading_animation(update, message, frames=LOADING_FRAMES, duration=2):
        """Show loading animation"""
        msg = await update.message.reply_text(f"🎬 {frames[0]} Loading...")
        for i in range(min(len(frames), duration*2)):
            await asyncio.sleep(0.5)
            await msg.edit_text(f"🎬 {frames[i % len(frames)]} {message}")
        await msg.delete()
    
    @staticmethod
    def format_currency(amount):
        """Beautiful currency formatting"""
        return f"`₹{amount:,}`"
    
    @staticmethod
    def progress_bar(current, total, width=10):
        """Beautiful progress bar"""
        filled = int(width * current / total) if total > 0 else 0
        bar = "█" * filled + "░" * (width - filled)
        percent = int(100 * current / total) if total > 0 else 0
        return f"{bar} {percent}%"

# ===========================================================================
# AUTO PROMOTION ENGINE
# ===========================================================================

class PromotionEngine:
    """Automatic promotion system for channels"""
    
    def __init__(self, bot):
        self.bot = bot
        self.channels = [MAIN_CHANNEL, PROMO_CHANNEL]
        self.promo_messages = [
            {
                "type": "offer",
                "emoji": "🔥",
                "title": "FLASH SALE!",
                "content": "Get {card} at {discount}% OFF!",
                "discount": 80
            },
            {
                "type": "new_user",
                "emoji": "🎁",
                "title": "WELCOME BONUS!",
                "content": "New users get ₹{bonus} FREE!",
                "bonus": WELCOME_BONUS
            },
            {
                "type": "referral",
                "emoji": "👥",
                "title": "REFER & EARN!",
                "content": "Earn ₹{bonus} per referral!",
                "bonus": REFERRAL_BONUS
            },
            {
                "type": "trending",
                "emoji": "📈",
                "title": "TRENDING NOW!",
                "content": "{card} is the most popular today!"
            },
            {
                "type": "limited",
                "emoji": "⏳",
                "title": "LIMITED TIME!",
                "content": "Special prices on {card}!"
            },
            {
                "type": "achievement",
                "emoji": "🏆",
                "title": "MILESTONE!",
                "content": "We just hit {users}+ users! 🎉"
            }
        ]
        
    async def create_promo(self, context):
        """Create automatic promotion"""
        try:
            promo = random.choice(self.promo_messages)
            cards = list(GIFT_CARDS.values())
            card = random.choice(cards)
            
            # Format message
            content = promo["content"]
            if "{card}" in content:
                content = content.replace("{card}", f"{card['full_emoji']} {card['name']}")
            if "{discount}" in content:
                content = content.replace("{discount}", str(promo.get("discount", 80)))
            if "{bonus}" in content:
                content = content.replace("{bonus}", str(promo.get("bonus", 10)))
            
            # Get user count
            conn = sqlite3.connect(DATABASE_PATH)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM users")
            users = c.fetchone()[0]
            conn.close()
            
            if "{users}" in content:
                content = content.replace("{users}", str(users))
            
            # Create cinematic message
            message = (
                f"{promo['emoji']} *{promo['title']}* {promo['emoji']}\n"
                f"{DIVIDER_SHORT}\n\n"
                f"{content}\n\n"
                f"{THEME['rocket']} *Join now:* @{context.bot.username}\n"
                f"{DIVIDER_STARS}"
            )
            
            # Post to all channels
            for channel in self.channels:
                try:
                    await context.bot.send_message(
                        chat_id=channel,
                        text=message,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    log.info(f"📢 Promo posted to {channel}")
                except Exception as e:
                    log.error(f"❌ Promo failed for {channel}: {e}")
            
            return True
            
        except Exception as e:
            log.error(f"❌ Promo creation error: {e}")
            return False
    
    async def create_proof(self, context):
        """Create live proof"""
        try:
            names = [
                "👑 Raj", "💫 Arjun", "🌟 Kavya", "⚡ Veer", "🔥 Aryan",
                "💎 Neha", "🎯 Karan", "🚀 Riya", "⭐ Amit", "💥 Priya",
                "🦁 Simba", "🐅 Tiger", "🦅 Falcon", "🐺 Wolf", "🦊 Fox"
            ]
            cards = [f"{c['full_emoji']} {c['name']}" for c in GIFT_CARDS.values()]
            amounts = [500, 1000, 2000, 5000]
            
            name = random.choice(names)
            card = random.choice(cards)
            amount = random.choice(amounts)
            
            # Different proof formats
            formats = [
                f"⚡ *LIVE PURCHASE*\n\n"
                f"{DIVIDER_SHORT}\n"
                f"👤 *{name}*\n"
                f"🎁 {card}\n"
                f"💰 `₹{amount}`\n"
                f"{DIVIDER_SHORT}\n"
                f"📧 *Email Delivery*\n"
                f"✅ *Instant*",
                
                f"🎉 *FRESH ORDER*\n\n"
                f"{DIVIDER_SHORT}\n"
                f"👤 {name}\n"
                f"🛍️ {card}\n"
                f"💳 ₹{amount}\n"
                f"{DIVIDER_SHORT}\n"
                f"⚡ *Delivered*",
                
                f"🌟 *NEW PURCHASE*\n\n"
                f"{DIVIDER_SHORT}\n"
                f"✨ {name} just bought\n"
                f"🎁 {card}\n"
                f"💰 ₹{amount}\n"
                f"{DIVIDER_SHORT}\n"
                f"📧 *Email Sent*"
            ]
            
            message = random.choice(formats)
            
            await context.bot.send_message(
                chat_id=PROOF_CHANNEL,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            log.error(f"❌ Proof error: {e}")

# ===========================================================================
# MEMBERSHIP CHECK
# ===========================================================================

async def is_member(user_id, context):
    """Check channel membership"""
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
            await update.message.reply_text(
                f"{THEME['error']} *Unauthorized*\n\nThis command is for cinema admins only.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def cinematic_log(func):
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        user = update.effective_user
        log.info(f"🎬 {user.id} | {user.first_name} → {func.__name__}")
        return await func(update, context, *args, **kwargs)
    return wrapper

# ===========================================================================
# CINEMATIC START
# ===========================================================================

@cinematic_log
async def cinematic_start(update, context):
    """Cinematic start command"""
    user = update.effective_user
    
    # Check configuration
    if not all([BOT_TOKEN, ADMIN_ID, UPI_ID]):
        await update.message.reply_text(
            f"{THEME['error']} *Configuration Error*\n\nPlease set environment variables.",
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
        log.info(f"✨ New user: {user.id}")
        
        # Welcome bonus
        if WELCOME_BONUS > 0:
            db.update_balance(user.id, WELCOME_BONUS, 'bonus')
        
        # Process referral
        if referred:
            db.process_referral(referred, user.id)
            try:
                await context.bot.send_message(
                    referred,
                    f"{THEME['referral']} *Referral Bonus!*\n\n"
                    f"{user.first_name} joined using your link!\n"
                    f"+{THEME['money']} *₹{REFERRAL_BONUS}*",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
    
    db.update_active(user.id)
    
    # Check membership
    if not await is_member(user.id, context):
        welcome = (
            f"{THEME['primary']} *WELCOME TO GIFT CARD CINEMA* {THEME['primary']}\n"
            f"{DIVIDER}\n\n"
            f"👋 *Hello {user.first_name}!*\n\n"
            f"{THEME['card']} *Get Gift Cards at 80% OFF*\n"
            f"{THEME['rocket']} *10+ Premium Brands*\n"
            f"{THEME['money']} *Instant Delivery*\n"
            f"{THEME['crown']} *VIP Benefits*\n\n"
            f"{DIVIDER_SHORT}\n\n"
            f"{THEME['warning']} *VERIFICATION REQUIRED*\n"
            f"Join our channel to enter the cinema!\n\n"
            f"{THEME['next']} *Click below to join*"
        )
        
        keyboard = [[
            InlineKeyboardButton("📢 JOIN CINEMA", url="https://t.me/gift_cinema"),
            InlineKeyboardButton("✅ VERIFY", callback_data="verify")
        ]]
        
        await update.message.reply_text(
            welcome,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Show main menu
    balance = db.get_balance(user.id)
    
    # Get stats
    stats = db.get_stats()
    
    menu = (
        f"{THEME['primary']} *GIFT CARD CINEMA* {THEME['primary']}\n"
        f"{DIVIDER}\n\n"
        f"👤 *{user.first_name}* {THEME['crown'] if balance > 1000 else ''}\n"
        f"{THEME['money']} *Balance:* `₹{balance:,}`\n"
        f"{DIVIDER_SHORT}\n"
        f"📊 *Today:* {stats['active']} active • {stats['pending']} pending\n"
        f"{DIVIDER}\n\n"
        f"*Choose your experience:* ⬇️"
    )
    
    keyboard = [
        [CinemaUI.menu_button("GIFT CARDS", THEME['card'], "giftcard")],
        [CinemaUI.menu_button("ADD MONEY", THEME['money'], "topup")],
        [CinemaUI.menu_button("MY WALLET", THEME['wallet'], "wallet")],
        [CinemaUI.menu_button("VIP REFERRAL", THEME['referral'], "referral")],
        [CinemaUI.menu_button("LIVE PROOFS", THEME['proof'], "proofs")],
        [CinemaUI.menu_button("CINEMA SUPPORT", THEME['support'], "support")]
    ]
    
    await update.message.reply_text(
        menu,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===========================================================================
# CINEMATIC BUTTON HANDLER
# ===========================================================================

@cinematic_log
async def cinematic_buttons(update, context):
    """Handle all button clicks with cinematic style"""
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
                f"{THEME['success']} *VERIFICATION SUCCESSFUL* {THEME['success']}\n"
                f"{DIVIDER}\n\n"
                f"👋 *Welcome to the Cinema, {user.first_name}!*\n"
                f"{THEME['money']} *Balance:* `₹{balance:,}`\n\n"
                f"{DIVIDER_SHORT}\n"
                f"✨ *VIP Access Granted*\n"
                f"{DIVIDER}\n\n"
                f"*Your journey begins now:* ⬇️"
            )
            
            keyboard = [
                [CinemaUI.menu_button("GIFT CARDS", THEME['card'], "giftcard")],
                [CinemaUI.menu_button("ADD MONEY", THEME['money'], "topup")],
                [CinemaUI.menu_button("MY WALLET", THEME['wallet'], "wallet")]
            ]
            
            await query.edit_message_text(
                success,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            fail = (
                f"{THEME['error']} *VERIFICATION FAILED* {THEME['error']}\n"
                f"{DIVIDER_SHORT}\n\n"
                f"You haven't joined our cinema yet!\n\n"
                f"1️⃣ Click JOIN CINEMA\n"
                f"2️⃣ Join @gift_cinema\n"
                f"3️⃣ Click VERIFY"
            )
            
            keyboard = [[
                InlineKeyboardButton("📢 JOIN CINEMA", url="https://t.me/gift_cinema"),
                InlineKeyboardButton("🔄 VERIFY", callback_data="verify")
            ]]
            
            await query.edit_message_text(
                fail,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return
    
    # Check membership for other actions
    if not await is_member(user.id, context):
        keyboard = [[
            InlineKeyboardButton("📢 JOIN CINEMA", url="https://t.me/gift_cinema"),
            InlineKeyboardButton("✅ VERIFY", callback_data="verify")
        ]]
        
        await query.edit_message_text(
            f"{THEME['warning']} *ACCESS DENIED*\n\nJoin @gift_cinema first!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # ===== MAIN MENU =====
    if data == "main_menu":
        balance = db.get_balance(user.id)
        
        menu = (
            f"{THEME['primary']} *GIFT CARD CINEMA* {THEME['primary']}\n"
            f"{DIVIDER}\n\n"
            f"👤 *{user.first_name}*\n"
            f"{THEME['money']} *Balance:* `₹{balance:,}`\n"
            f"{DIVIDER}\n\n"
            f"*Choose your experience:* ⬇️"
        )
        
        keyboard = [
            [CinemaUI.menu_button("GIFT CARDS", THEME['card'], "giftcard")],
            [CinemaUI.menu_button("ADD MONEY", THEME['money'], "topup")],
            [CinemaUI.menu_button("MY WALLET", THEME['wallet'], "wallet")],
            [CinemaUI.menu_button("VIP REFERRAL", THEME['referral'], "referral")],
            [CinemaUI.menu_button("LIVE PROOFS", THEME['proof'], "proofs")],
            [CinemaUI.menu_button("CINEMA SUPPORT", THEME['support'], "support")]
        ]
        
        await query.edit_message_text(
            menu,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== GIFT CARDS =====
    elif data == "giftcard":
        menu = (
            f"{THEME['card']} *GIFT CARD CINEMA* {THEME['card']}\n"
            f"{DIVIDER}\n\n"
            f"*Featured Collections:*\n"
            f"{DIVIDER_SHORT}\n"
        )
        
        keyboard = []
        
        # Featured cards
        featured = [cid for cid, card in GIFT_CARDS.items() if card.get('exclusive', False)]
        for cid in featured[:3]:
            card = GIFT_CARDS[cid]
            menu += f"\n{card['full_emoji']} *{card['cinematic']}*\n`{card['tagline']}`\n"
        
        menu += f"\n{DIVIDER_SHORT}\n*All Brands:*\n"
        
        # All cards
        for cid, card in GIFT_CARDS.items():
            star = "⭐" if card.get('exclusive', False) else ""
            keyboard.append([InlineKeyboardButton(
                f"{card['full_emoji']} {card['name']} {star}",
                callback_data=f"card_{cid}"
            )])
        
        keyboard.append([CinemaUI.menu_button("BACK TO CINEMA", THEME['back'], "main_menu")])
        
        await query.edit_message_text(
            menu,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== CARD DETAILS =====
    elif data.startswith("card_"):
        cid = data.replace("card_", "")
        card = GIFT_CARDS.get(cid)
        if not card:
            return
        
        details = (
            f"{card['full_emoji']} *{card['cinematic']}* {card['full_emoji']}\n"
            f"{DIVIDER}\n\n"
            f"✨ *{card['tagline']}*\n"
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
                    f"💎 ₹{denom} → ₹{price} (Save {percent}%)",
                    callback_data=f"buy_{cid}_{denom}"
                )])
        
        keyboard.append([CinemaUI.menu_button("BACK TO COLLECTION", THEME['back'], "giftcard")])
        
        await query.edit_message_text(
            details,
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
            short = price - balance
            keyboard = [[CinemaUI.menu_button("ADD MONEY", THEME['money'], "topup")]]
            
            await query.edit_message_text(
                f"{THEME['error']} *Insufficient Balance*\n\n"
                f"Need: `₹{price:,}`\n"
                f"Have: `₹{balance:,}`\n"
                f"Short: `₹{short:,}`",
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
            f"{THEME['success']} *Balance Sufficient* {THEME['success']}\n\n"
            f"{card['full_emoji']} *{card['name']} ₹{value}*\n"
            f"Price: `₹{price:,}`\n"
            f"You Save: `₹{savings:,}` ({percent}% OFF)\n\n"
            f"{DIVIDER_SHORT}\n\n"
            f"📧 *Enter your email for delivery:*",
            parse_mode=ParseMode.MARKDOWN
        )
        
        return STATE_EMAIL
    
    # ===== TOP UP =====
    elif data == "topup":
        menu = (
            f"{THEME['money']} *ADD MONEY TO WALLET* {THEME['money']}\n"
            f"{DIVIDER}\n\n"
            f"*Select payment method:*\n\n"
            f"📱 *UPI* - Instant\n"
            f"   Min: `₹{MIN_RECHARGE}` • Max: `₹{MAX_RECHARGE}`\n"
            f"   Fee: {FEE_PERCENT}% below ₹{FEE_THRESHOLD}\n"
        )
        
        keyboard = [
            [CinemaUI.menu_button("📱 UPI PAYMENT", "💳", "upi")],
            [CinemaUI.menu_button("BACK", THEME['back'], "main_menu")]
        ]
        
        await query.edit_message_text(
            menu,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== UPI =====
    elif data == "upi":
        await query.edit_message_text(
            f"{THEME['money']} *UPI RECHARGE* {THEME['money']}\n"
            f"{DIVIDER}\n\n"
            f"*Enter amount:*\n\n"
            f"Min: `₹{MIN_RECHARGE}`\n"
            f"Max: `₹{MAX_RECHARGE}`\n\n"
            f"📌 Fee: {FEE_PERCENT}% below ₹{FEE_THRESHOLD}\n"
            f"   • Pay ₹100 → Get ₹80\n"
            f"   • Pay ₹200 → Get ₹200\n\n"
            f"`Enter amount in numbers:`",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_AMOUNT
    
    # ===== WALLET =====
    elif data == "wallet":
        balance = db.get_balance(user.id)
        
        wallet = (
            f"{THEME['wallet']} *YOUR CINEMA WALLET* {THEME['wallet']}\n"
            f"{DIVIDER}\n\n"
            f"💰 *Balance:* `₹{balance:,}`\n"
            f"{DIVIDER_SHORT}\n\n"
            f"*Quick Actions:*\n"
        )
        
        keyboard = [
            [CinemaUI.menu_button("ADD MONEY", THEME['money'], "topup")],
            [CinemaUI.menu_button("BUY CARDS", THEME['card'], "giftcard")],
            [CinemaUI.menu_button("BACK", THEME['back'], "main_menu")]
        ]
        
        await query.edit_message_text(
            wallet,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== REFERRAL =====
    elif data == "referral":
        bot = await context.bot.get_me()
        link = f"https://t.me/{bot.username}?start=ref_{user.id}"
        
        ref = (
            f"{THEME['referral']} *VIP REFERRAL PROGRAM* {THEME['referral']}\n"
            f"{DIVIDER}\n\n"
            f"✨ *Earn ₹{REFERRAL_BONUS} per friend!*\n\n"
            f"🔗 *Your VIP Link:*\n"
            f"`{link}`\n\n"
            f"📌 *How it works:*\n"
            f"1️⃣ Share your link\n"
            f"2️⃣ Friend joins\n"
            f"3️⃣ You get ₹{REFERRAL_BONUS}\n"
            f"4️⃣ Friend gets ₹{WELCOME_BONUS}\n\n"
            f"{THEME['rocket']} *Start sharing now!*"
        )
        
        keyboard = [[CinemaUI.menu_button("BACK", THEME['back'], "main_menu")]]
        
        await query.edit_message_text(
            ref,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== PROOFS =====
    elif data == "proofs":
        proofs = (
            f"{THEME['proof']} *LIVE CINEMA PROOFS* {THEME['proof']}\n"
            f"{DIVIDER}\n\n"
            f"📊 *See real purchases from real users*\n\n"
            f"👉 {PROOF_CHANNEL}\n\n"
            f"⚡ *Latest Activity:*\n"
            f"• 1000+ successful deliveries\n"
            f"• Instant email delivery\n"
            f"• 24/7 automatic processing\n"
            f"• 4.9/5 user rating\n\n"
            f"{THEME['next']} *Click below to join*"
        )
        
        keyboard = [
            [InlineKeyboardButton("📢 VIEW PROOFS", url=f"https://t.me/{PROOF_CHANNEL[1:]}")],
            [CinemaUI.menu_button("BACK", THEME['back'], "main_menu")]
        ]
        
        await query.edit_message_text(
            proofs,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== SUPPORT =====
    elif data == "support":
        support = (
            f"{THEME['support']} *CINEMA SUPPORT* {THEME['support']}\n"
            f"{DIVIDER}\n\n"
            f"❓ *FAQs:*\n\n"
            f"1️⃣ *How to buy?*\n"
            f"   → Add money → Select card → Enter email\n\n"
            f"2️⃣ *Delivery time?*\n"
            f"   → Instant (2-5 minutes)\n\n"
            f"3️⃣ *Payment issues?*\n"
            f"   → Send screenshot + UTR to admin\n\n"
            f"4️⃣ *Card not received?*\n"
            f"   → Check spam, contact support\n\n"
            f"{DIVIDER_SHORT}\n\n"
            f"📝 *Type your issue below:*"
        )
        
        keyboard = [[CinemaUI.menu_button("BACK", THEME['back'], "main_menu")]]
        
        await query.edit_message_text(
            support,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return STATE_SUPPORT

# ===========================================================================
# AMOUNT HANDLER
# ===========================================================================

async def handle_amount(update, context):
    """Handle amount input with cinematic style"""
    text = update.message.text.strip()
    
    try:
        amount = int(text)
    except:
        await update.message.reply_text(
            f"{THEME['error']} *Invalid Input*\n\nPlease enter a valid number.",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_AMOUNT
    
    if amount < MIN_RECHARGE or amount > MAX_RECHARGE:
        await update.message.reply_text(
            f"{THEME['error']} *Invalid Amount*\n\n"
            f"Amount must be between `₹{MIN_RECHARGE}` and `₹{MAX_RECHARGE}`.",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_AMOUNT
    
    fee, final = calculate_fee(amount)
    context.user_data['topup'] = {'amount': amount, 'fee': fee, 'final': final}
    
    keyboard = [
        [CinemaUI.menu_button("✅ I HAVE PAID", "💰", "paid")],
        [CinemaUI.menu_button("❌ CANCEL", "🚫", "main_menu")]
    ]
    
    if os.path.exists(QR_CODE_PATH):
        with open(QR_CODE_PATH, 'rb') as qr:
            await update.message.reply_photo(
                photo=qr,
                caption=(
                    f"{THEME['money']} *PAYMENT DETAILS* {THEME['money']}\n"
                    f"{DIVIDER}\n\n"
                    f"💳 *UPI ID:* `{UPI_ID}`\n"
                    f"💰 *Amount:* `₹{amount:,}`\n"
                    f"📉 *Fee:* `₹{fee:,}`\n"
                    f"✨ *You get:* `₹{final:,}`\n\n"
                    f"{DIVIDER_SHORT}\n\n"
                    f"📱 *After payment, click I HAVE PAID*"
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    else:
        await update.message.reply_text(
            f"{THEME['money']} *PAYMENT DETAILS* {THEME['money']}\n"
            f"{DIVIDER}\n\n"
            f"💳 *UPI ID:* `{UPI_ID}`\n"
            f"💰 *Amount:* `₹{amount:,}`\n"
            f"📉 *Fee:* `₹{fee:,}`\n"
            f"✨ *You get:* `₹{final:,}`\n\n"
            f"{DIVIDER_SHORT}\n\n"
            f"📱 *After payment, click I HAVE PAID*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    return ConversationHandler.END

# ===========================================================================
# PAID HANDLER
# ===========================================================================

async def handle_paid(update, context):
    """Handle paid button click"""
    query = update.callback_query
    await query.answer()
    
    if 'topup' not in context.user_data:
        await query.edit_message_text(
            f"{THEME['error']} *Session Expired*\n\nPlease start over.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    await query.edit_message_text(
        f"{THEME['money']} *SEND PAYMENT PROOF* {THEME['money']}\n"
        f"{DIVIDER}\n\n"
        f"1️⃣ *Send SCREENSHOT* of payment\n"
        f"2️⃣ *Send UTR NUMBER*\n\n"
        f"📌 *UTR Example:* `SBIN1234567890`",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return STATE_SCREENSHOT

# ===========================================================================
# SCREENSHOT HANDLER
# ===========================================================================

async def handle_screenshot(update, context):
    """Handle screenshot"""
    if not update.message.photo:
        await update.message.reply_text(
            f"{THEME['error']} *Please send a PHOTO*",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_SCREENSHOT
    
    context.user_data['screenshot'] = update.message.photo[-1].file_id
    
    await update.message.reply_text(
        f"{THEME['success']} *Screenshot Received*\n\nNow send UTR number:",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return STATE_UTR

# ===========================================================================
# UTR HANDLER
# ===========================================================================

async def handle_utr(update, context):
    """Handle UTR input"""
    user = update.effective_user
    utr = update.message.text.strip()
    
    if not (12 <= len(utr) <= 22 and utr.isalnum()):
        await update.message.reply_text(
            f"{THEME['error']} *Invalid UTR*\n\nUTR should be 12-22 characters.",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_UTR
    
    if 'topup' not in context.user_data or 'screenshot' not in context.user_data:
        await update.message.reply_text(
            f"{THEME['error']} *Session Expired*\n\nPlease start over.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    data = context.user_data['topup']
    vid = db.create_verification(
        user.id, data['amount'], data['fee'], data['final'], utr, context.user_data['screenshot']
    )
    
    # Admin notification
    await context.bot.send_photo(
        chat_id=ADMIN_CHANNEL_ID,
        photo=context.user_data['screenshot'],
        caption=(
            f"{THEME['primary']} *NEW PAYMENT* {THEME['primary']}\n"
            f"{DIVIDER}\n\n"
            f"👤 *User:* {user.first_name}\n"
            f"🆔 *ID:* `{user.id}`\n"
            f"💰 *Amount:* `₹{data['amount']:,}`\n"
            f"✨ *Credit:* `₹{data['final']:,}`\n"
            f"🔢 *UTR:* `{utr}`\n"
            f"🆔 *Verification:* `{vid}`"
        ),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{vid}"),
            InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{vid}")
        ]])
    )
    
    context.user_data.clear()
    
    await update.message.reply_text(
        f"{THEME['success']} *VERIFICATION SUBMITTED!*\n\n"
        f"Your payment is being verified.\n"
        f"You'll be notified within 5-10 minutes.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ConversationHandler.END

# ===========================================================================
# EMAIL HANDLER
# ===========================================================================

async def handle_email(update, context):
    """Handle email input"""
    user = update.effective_user
    email = update.message.text.strip()
    
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        await update.message.reply_text(
            f"{THEME['error']} *Invalid Email*\n\nPlease enter a valid email.",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_EMAIL
    
    if 'purchase' not in context.user_data:
        await update.message.reply_text(
            f"{THEME['error']} *Session Expired*\n\nPlease start over.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    p = context.user_data['purchase']
    balance = db.get_balance(user.id)
    
    if balance < p['price']:
        await update.message.reply_text(
            f"{THEME['error']} *Insufficient Balance*",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    # Process purchase
    db.update_balance(user.id, -p['price'], 'debit')
    order_id = db.create_purchase(user.id, p['card'], p['value'], p['price'], email)
    
    context.user_data.clear()
    
    await update.message.reply_text(
        f"{THEME['success']} *PURCHASE SUCCESSFUL!*\n\n"
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
    """Handle support message"""
    user = update.effective_user
    msg = update.message.text.strip()
    
    if len(msg) < 10:
        await update.message.reply_text(
            f"{THEME['error']} *Message Too Short*\n\nPlease describe your issue (min 10 chars).",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_SUPPORT
    
    # Save ticket
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO support (user_id, message, timestamp) VALUES (?, ?, ?)''',
              (user.id, msg, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    # Notify admin
    await context.bot.send_message(
        ADMIN_ID,
        f"{THEME['support']} *SUPPORT TICKET*\n\n"
        f"👤 {user.first_name}\n"
        f"🆔 `{user.id}`\n"
        f"💬 {msg}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    await update.message.reply_text(
        f"{THEME['success']} *SUPPORT SENT!*\n\n"
        f"We'll contact you within 24 hours.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ConversationHandler.END

# ===========================================================================
# ADMIN HANDLER
# ===========================================================================

async def admin_handler(update, context):
    """Handle admin callbacks"""
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
                caption=query.message.caption + f"\n\n{THEME['success']} *APPROVED BY ADMIN*",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Notify user
            await context.bot.send_message(
                v['user_id'],
                f"{THEME['success']} *PAYMENT APPROVED!*\n\n"
                f"💰 `₹{v['final_amount']:,}` added to your balance.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif action == "reject":
        db.reject_verification(vid)
        await query.edit_message_caption(
            caption=query.message.caption + f"\n\n{THEME['error']} *REJECTED BY ADMIN*",
            parse_mode=ParseMode.MARKDOWN
        )

# ===========================================================================
# ADMIN COMMANDS
# ===========================================================================

@admin_only
async def admin_stats(update, context):
    """Admin statistics"""
    stats = db.get_stats()
    
    await update.message.reply_text(
        f"{THEME['primary']} *CINEMA STATISTICS* {THEME['primary']}\n"
        f"{DIVIDER}\n\n"
        f"👥 *Users:* `{stats['users']:,}`\n"
        f"📱 *Active Today:* `{stats['active']}`\n"
        f"⏳ *Pending:* `{stats['pending']}`\n"
        f"💰 *Revenue:* `₹{stats['revenue']:,}`\n"
        f"💳 *Spent:* `₹{stats['spent']:,}`",
        parse_mode=ParseMode.MARKDOWN
    )

@admin_only
async def admin_promo(update, context):
    """Manually trigger promotion"""
    promo = PromotionEngine(context.bot)
    success = await promo.create_promo(context)
    
    if success:
        await update.message.reply_text(
            f"{THEME['success']} *Promotion Posted!*",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            f"{THEME['error']} *Promotion Failed*",
            parse_mode=ParseMode.MARKDOWN
        )

# ===========================================================================
# AUTO PROMOTIONS & PROOFS
# ===========================================================================

async def auto_promotions(context):
    """Auto post promotions to channels"""
    promo = PromotionEngine(context.bot)
    await promo.create_promo(context)

async def auto_proofs(context):
    """Auto post proofs to channel"""
    promo = PromotionEngine(context.bot)
    await promo.create_proof(context)

# ===========================================================================
# CANCEL HANDLER
# ===========================================================================

async def cancel(update, context):
    """Cancel current operation"""
    context.user_data.clear()
    await update.message.reply_text(
        f"{THEME['error']} *Cancelled*",
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END

# ===========================================================================
# ERROR HANDLER
# ===========================================================================

async def error_handler(update, context):
    """Handle errors gracefully"""
    log.error(f"💥 Error: {context.error}")

# ===========================================================================
# POST INIT
# ===========================================================================

async def post_init(app):
    """Setup after bot initialization"""
    await app.bot.set_my_commands([
        BotCommand("start", "🎬 Enter Cinema"),
        BotCommand("stats", "📊 Stats (Admin)"),
        BotCommand("promo", "📢 Create Promo (Admin)"),
        BotCommand("cancel", "❌ Cancel")
    ])
    
    # Verify channels
    try:
        await app.bot.get_chat(MAIN_CHANNEL)
        log.info(f"✅ Main channel verified: {MAIN_CHANNEL}")
    except:
        log.error(f"❌ Main channel not accessible: {MAIN_CHANNEL}")
    
    try:
        await app.bot.get_chat(PROOF_CHANNEL)
        log.info(f"✅ Proof channel verified: {PROOF_CHANNEL}")
    except:
        log.error(f"❌ Proof channel not accessible: {PROOF_CHANNEL}")
    
    log.info("🎬 Cinema Bot Ready!")

# ===========================================================================
# MAIN
# ===========================================================================

db = CinemaDB()

def main():
    """Main function"""
    # Validate config
    if not BOT_TOKEN:
        log.error("❌ BOT_TOKEN not set")
        sys.exit(1)
    if not ADMIN_ID:
        log.error("❌ ADMIN_ID not set")
        sys.exit(1)
    if not UPI_ID:
        log.error("❌ UPI_ID not set")
        sys.exit(1)
    
    # Create app
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", cinematic_start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("promo", admin_promo))
    
    # Button handlers
    app.add_handler(CallbackQueryHandler(cinematic_buttons))
    app.add_handler(CallbackQueryHandler(admin_handler, pattern="^(approve_|reject_)"))
    
    # Paid handler
    app.add_handler(CallbackQueryHandler(handle_paid, pattern="^paid$"))
    
    # Amount conversation
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(cinematic_buttons, pattern="^upi$")],
        states={STATE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    ))
    
    # Payment verification conversation
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
        entry_points=[CallbackQueryHandler(cinematic_buttons, pattern="^buy_")],
        states={STATE_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    ))
    
    # Support conversation
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(cinematic_buttons, pattern="^support$")],
        states={STATE_SUPPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_support)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    ))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    # Auto jobs
    if app.job_queue:
        # Auto promotions every 2 hours
        app.job_queue.run_repeating(auto_promotions, interval=7200, first=60)
        
        # Auto proofs every 45 seconds
        app.job_queue.run_repeating(auto_proofs, interval=45, first=30)
    
    # Start
    print("\n" + "="*60)
    print("      🎬 GIFT CARD CINEMA v7.0 ULTIMATE 🎬")
    print("="*60)
    print("✅ Bot is running...")
    print("📢 Auto promotions: Every 2 hours")
    print("📊 Auto proofs: Every 45 seconds")
    print("="*60 + "\n")
    
    app.run_polling()

if __name__ == "__main__":
    main()
