#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
===============================================================================
🎁 GIFT CARD & RECHARGE BOT - ULTIMATE EDITION v11.0 🎁
===============================================================================
NEW FEATURES ADDED:
✓ Message Reactions (1) ✓ Typing Indicators (2) ✓ Daily Rewards (3) 
✓ Price Drop Alerts (6) ✓ Discount Coupons (10) ✓ Bulk Purchase (12)
✓ Gift Card Gifting (13) ✓ Multi-Language Support (23) ✓ Admin Dashboard (24)
✓ Enhanced Visuals - Animated GIFs, Progress Bars, Badges, Tables
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
import qrcode
from io import BytesIO
from datetime import datetime, timedelta, date
from functools import wraps
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
import pandas as pd
from threading import Thread

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

# ===========================================================================
# ENHANCED FEATURES CONFIGURATION
# ===========================================================================

# Daily Rewards (Feature 3)
DAILY_REWARDS = {
    1: 5,    # Day 1: ₹5
    2: 8,    # Day 2: ₹8
    3: 10,   # Day 3: ₹10
    4: 12,   # Day 4: ₹12
    5: 15,   # Day 5: ₹15
    6: 18,   # Day 6: ₹18
    7: 25,   # Day 7: ₹25 (Bonus)
    10: 40,  # Day 10: ₹40 (Milestone)
    15: 60,  # Day 15: ₹60 (Milestone)
    30: 100  # Day 30: ₹100 (Monthly Bonus)
}

# Discount Coupons (Feature 10)
COUPONS = {
    "WELCOME10": {"discount": 10, "type": "percentage", "min": 100, "uses": 1},
    "SAVE20": {"discount": 20, "type": "fixed", "min": 200, "uses": 1},
    "FIRST50": {"discount": 50, "type": "fixed", "min": 500, "uses": 1},
    "FREESHIP": {"discount": 0, "type": "free_delivery", "min": 300, "uses": 1},
    "DIWALI22": {"discount": 22, "type": "percentage", "min": 200, "uses": 100},
    "HOLI15": {"discount": 15, "type": "percentage", "min": 150, "uses": 100},
    "FLASH50": {"discount": 50, "type": "percentage", "min": 500, "uses": 50}
}

# Bulk Purchase Discounts (Feature 12)
BULK_DISCOUNTS = {
    1: 0,    # No discount
    3: 3,    # 3% off on 3+ cards
    5: 5,    # 5% off on 5+ cards
    10: 10,  # 10% off on 10+ cards
    25: 15,  # 15% off on 25+ cards
    50: 20   # 20% off on 50+ cards
}

# Price Drop Alerts (Feature 6)
PRICE_ALERT_THRESHOLD = 10  # Alert when price drops by 10%

# Languages (Feature 23)
LANGUAGES = {
    "en": {"name": "English", "flag": "🇬🇧"},
    "hi": {"name": "हिन्दी", "flag": "🇮🇳"},
    "ta": {"name": "தமிழ்", "flag": "🇮🇳"},
    "te": {"name": "తెలుగు", "flag": "🇮🇳"},
    "bn": {"name": "বাংলা", "flag": "🇮🇳"},
    "gu": {"name": "ગુજરાતી", "flag": "🇮🇳"},
    "mr": {"name": "मराठी", "flag": "🇮🇳"}
}

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
    STATE_GIFT_EMAIL,
    STATE_COUPON,
    STATE_BULK_COUNT,
    STATE_PRICE_ALERT,
    STATE_LANGUAGE
) = range(10)

# ===========================================================================
# GIFT CARD DATA
# ===========================================================================

GIFT_CARDS = {
    "amazon": {
        "name": "AMAZON", "emoji": "🟦", "full_emoji": "🟦🛒", 
        "popular": True, "trending": True,
        "base_price": {500: 100, 1000: 200, 2000: 400, 5000: 1000}
    },
    "flipkart": {
        "name": "FLIPKART", "emoji": "📦", "full_emoji": "📦🛍️", 
        "popular": True, "trending": True,
        "base_price": {500: 100, 1000: 200, 2000: 400, 5000: 1000}
    },
    "playstore": {
        "name": "PLAY STORE", "emoji": "🟩", "full_emoji": "🟩🎮", 
        "popular": True, "trending": False,
        "base_price": {500: 100, 1000: 200, 2000: 400, 5000: 1000}
    },
    "bookmyshow": {
        "name": "BOOKMYSHOW", "emoji": "🎟️", "full_emoji": "🎟️🎬", 
        "popular": True, "trending": False,
        "base_price": {500: 100, 1000: 200, 2000: 400, 5000: 1000}
    },
    "myntra": {
        "name": "MYNTRA", "emoji": "🛍️", "full_emoji": "🛍️👗", 
        "popular": True, "trending": True,
        "base_price": {500: 100, 1000: 200, 2000: 400, 5000: 1000}
    },
    "zomato": {
        "name": "ZOMATO", "emoji": "🍕", "full_emoji": "🍕🍔", 
        "popular": True, "trending": False,
        "base_price": {500: 100, 1000: 200, 2000: 400, 5000: 1000}
    },
    "bigbasket": {
        "name": "BIG BASKET", "emoji": "🛒", "full_emoji": "🛒🥬", 
        "popular": False, "trending": False,
        "base_price": {500: 100, 1000: 200, 2000: 400, 5000: 1000}
    }
}

# Price configuration (dynamic - can be updated)
PRICES = {500: 100, 1000: 200, 2000: 400, 5000: 1000}
DENOMINATIONS = [500, 1000, 2000, 5000]

# ===========================================================================
# ENHANCED UI COMPONENTS
# ===========================================================================

class EnhancedUI:
    """Premium UI components with animations and visuals"""
    
    @staticmethod
    def fancy_header(title, emoji="🎁", width=40):
        """Create fancy header with borders"""
        border_top = "╔" + "═" * (width-2) + "╗"
        middle = f"║{emoji} {title} {emoji}".center(width)
        border_bottom = "╚" + "═" * (width-2) + "╝"
        return f"<pre>{border_top}\n{middle}\n{border_bottom}</pre>"
    
    @staticmethod
    def progress_bar(current, total, width=20):
        """Beautiful progress bar"""
        if total == 0:
            filled = 0
        else:
            filled = int(width * current / total)
        bar = "█" * filled + "░" * (width - filled)
        percent = int(100 * current / total) if total > 0 else 0
        return f"<code>{bar}</code> <b>{percent}%</b>"
    
    @staticmethod
    def price_table(prices):
        """Create price comparison table"""
        table = "<pre>"
        table += "┌─────────┬─────────┐\n"
        table += "│  Value  │  Price  │\n"
        table += "├─────────┼─────────┤\n"
        for value, price in prices.items():
            table += f"│ ₹{value:<6} │ ₹{price:<6} │\n"
        table += "└─────────┴─────────┘</pre>"
        return table
    
    @staticmethod
    def rating_stars(rating):
        """Convert rating to stars"""
        full = "⭐" * int(rating)
        half = "✨" if rating % 1 >= 0.5 else ""
        empty = "☆" * (5 - int(rating) - (1 if half else 0))
        return full + half + empty
    
    @staticmethod
    def user_badge(purchases):
        """Get user badge based on purchases"""
        if purchases >= 100:
            return "👑 VIP ELITE"
        elif purchases >= 50:
            return "💎 DIAMOND"
        elif purchases >= 25:
            return "🏆 GOLD"
        elif purchases >= 10:
            return "⭐ SILVER"
        elif purchases >= 5:
            return "🔥 BRONZE"
        elif purchases >= 1:
            return "🆕 BEGINNER"
        else:
            return "👤 NEW"
    
    @staticmethod
    def format_currency(amount):
        """Format currency with commas"""
        return f"₹{amount:,}"

class Animations:
    """Message animations"""
    
    @staticmethod
    async def typing(update, duration=1):
        """Show typing indicator"""
        await update.get_bot().send_chat_action(
            chat_id=update.effective_chat.id, 
            action="typing"
        )
        await asyncio.sleep(duration)
    
    @staticmethod
    async def uploading(update, duration=1):
        """Show uploading indicator"""
        await update.get_bot().send_chat_action(
            chat_id=update.effective_chat.id, 
            action="upload_photo"
        )
        await asyncio.sleep(duration)
    
    @staticmethod
    async def react(update, emoji="👍"):
        """React to message"""
        try:
            await update.message.react([{"type": "emoji", "emoji": emoji}])
        except:
            pass

# ===========================================================================
# MULTI-LANGUAGE SUPPORT
# ===========================================================================

class Translator:
    """Multi-language translation system"""
    
    translations = {
        "en": {
            "welcome": "Welcome to Gift Card Bot!",
            "balance": "Your Balance",
            "select_option": "Select an option:",
            "insufficient": "Insufficient Balance",
            "success": "Success!",
            "error": "Error!",
            "confirm": "Confirm",
            "cancel": "Cancel",
            "back": "Back",
            "gift_cards": "Gift Cards",
            "add_money": "Add Money",
            "my_wallet": "My Wallet",
            "referral": "Referral Program",
            "support": "Support",
            "daily_reward": "Daily Reward",
            "coupon": "Coupon",
            "bulk_purchase": "Bulk Purchase",
            "gift_card": "Send as Gift",
            "price_alert": "Price Alert"
        },
        "hi": {
            "welcome": "गिफ्ट कार्ड बॉट में आपका स्वागत है!",
            "balance": "आपका बैलेंस",
            "select_option": "कोई विकल्प चुनें:",
            "insufficient": "अपर्याप्त बैलेंस",
            "success": "सफल!",
            "error": "त्रुटि!",
            "confirm": "पुष्टि करें",
            "cancel": "रद्द करें",
            "back": "वापस",
            "gift_cards": "गिफ्ट कार्ड",
            "add_money": "पैसे जोड़ें",
            "my_wallet": "मेरा वॉलेट",
            "referral": "रेफरल प्रोग्राम",
            "support": "सहायता",
            "daily_reward": "दैनिक इनाम",
            "coupon": "कूपन",
            "bulk_purchase": "थोक खरीद",
            "gift_card": "उपहार के रूप में भेजें",
            "price_alert": "मूल्य अलर्ट"
        },
        "ta": {
            "welcome": "கிஃப்ட் கார்ட் போட்டுக்கு வரவேற்கிறோம்!",
            "balance": "உங்கள் இருப்பு",
            "select_option": "ஒரு விருப்பத்தைத் தேர்ந்தெடுக்கவும்:",
            "insufficient": "போதுமான இருப்பு இல்லை",
            "success": "வெற்றி!",
            "error": "பிழை!",
            "confirm": "உறுதிப்படுத்து",
            "cancel": "ரத்துசெய்",
            "back": "பின்",
            "gift_cards": "கிஃப்ட் கார்டுகள்",
            "add_money": "பணம் சேர்க்க",
            "my_wallet": "என் வாலட்",
            "referral": "ரெஃபரல் திட்டம்",
            "support": "ஆதரவு",
            "daily_reward": "தினசரி வெகுமதி",
            "coupon": "கூப்பன்",
            "bulk_purchase": "மொத்த கொள்முதல்",
            "gift_card": "பரிசாக அனுப்பு",
            "price_alert": "விலை எச்சரிக்கை"
        }
    }
    
    @staticmethod
    def get_text(user_id, key, lang=None):
        """Get translated text for user"""
        if lang is None:
            # Get user's language from database
            conn = sqlite3.connect(DATABASE_PATH)
            c = conn.cursor()
            c.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
            result = c.fetchone()
            conn.close()
            lang = result[0] if result and result[0] in Translator.translations else "en"
        
        return Translator.translations.get(lang, Translator.translations["en"]).get(key, key)

# ===========================================================================
# LOGGING
# ===========================================================================

logging.basicConfig(format='%(asctime)s | %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ===========================================================================
# DATABASE MANAGER - ENHANCED
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
        
        # Users table - enhanced with more fields
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
            language TEXT DEFAULT 'en',
            streak INTEGER DEFAULT 0,
            last_claim DATE,
            badges TEXT DEFAULT '[]',
            alerts TEXT DEFAULT '[]'
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
            quantity INTEGER DEFAULT 1,
            price INTEGER,
            original_price INTEGER,
            discount INTEGER DEFAULT 0,
            coupon TEXT,
            email TEXT,
            is_gift INTEGER DEFAULT 0,
            recipient_email TEXT,
            gift_message TEXT,
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
        
        # Daily rewards table
        c.execute('''CREATE TABLE IF NOT EXISTS daily_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            claim_date DATE,
            streak INTEGER DEFAULT 1,
            amount INTEGER,
            UNIQUE(user_id, claim_date)
        )''')
        
        # Coupons table
        c.execute('''CREATE TABLE IF NOT EXISTS coupons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            user_id INTEGER,
            discount_type TEXT,
            discount_value INTEGER,
            min_amount INTEGER,
            used INTEGER DEFAULT 0,
            expires TIMESTAMP
        )''')
        
        # Price alerts table
        c.execute('''CREATE TABLE IF NOT EXISTS price_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            card_name TEXT,
            target_price INTEGER,
            current_price INTEGER,
            active INTEGER DEFAULT 1,
            created TIMESTAMP
        )''')
        
        # Admin logs table
        c.execute('''CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            action TEXT,
            details TEXT,
            timestamp TIMESTAMP
        )''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Enhanced Database ready")
    
    # ===== USER METHODS =====
    
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
    
    def update_user(self, user_id, **kwargs):
        conn = self._get_conn()
        c = conn.cursor()
        fields = []
        values = []
        for key, value in kwargs.items():
            fields.append(f"{key} = ?")
            values.append(value)
        values.append(user_id)
        query = f"UPDATE users SET {', '.join(fields)} WHERE user_id = ?"
        c.execute(query, values)
        conn.commit()
        conn.close()
    
    def update_active(self, user_id):
        self.update_user(user_id, last_active=datetime.now().isoformat())
    
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
            logger.error(f"Balance error: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    # ===== DAILY REWARDS (Feature 3) =====
    
    def claim_daily_reward(self, user_id):
        """Claim daily reward"""
        conn = self._get_conn()
        c = conn.cursor()
        
        today = date.today()
        
        # Check if already claimed today
        c.execute("SELECT streak FROM daily_rewards WHERE user_id = ? AND claim_date = ?", 
                  (user_id, today))
        if c.fetchone():
            conn.close()
            return None
        
        # Get last claim
        c.execute("SELECT claim_date, streak FROM daily_rewards WHERE user_id = ? ORDER BY claim_date DESC LIMIT 1", 
                  (user_id,))
        last = c.fetchone()
        
        if last:
            last_date = datetime.strptime(last[0], '%Y-%m-%d').date()
            if (today - last_date).days == 1:
                streak = last[1] + 1
            else:
                streak = 1
        else:
            streak = 1
        
        # Calculate reward
        if streak in DAILY_REWARDS:
            reward = DAILY_REWARDS[streak]
        elif streak > 30:
            reward = 100
        elif streak > 15:
            reward = 60
        elif streak > 10:
            reward = 40
        elif streak > 7:
            reward = 30
        else:
            reward = 5 + (streak - 1) * 2
        
        # Save reward
        c.execute("INSERT INTO daily_rewards (user_id, claim_date, streak, amount) VALUES (?, ?, ?, ?)",
                  (user_id, today, streak, reward))
        
        # Update user balance
        self.update_balance(user_id, reward, 'bonus')
        
        conn.commit()
        conn.close()
        
        return {"streak": streak, "reward": reward}
    
    # ===== COUPONS (Feature 10) =====
    
    def validate_coupon(self, code, amount):
        """Validate and apply coupon"""
        conn = self._get_conn()
        c = conn.cursor()
        
        if code not in COUPONS:
            return None
        
        coupon = COUPONS[code].copy()
        
        # Check minimum amount
        if amount < coupon.get("min", 0):
            return {"error": f"Minimum amount ₹{coupon['min']} required"}
        
        # Check uses
        c.execute("SELECT COUNT(*) FROM coupons WHERE code = ? AND used = 1", (code,))
        uses = c.fetchone()[0]
        if uses >= coupon.get("uses", 1):
            return {"error": "Coupon expired"}
        
        # Calculate discount
        if coupon["type"] == "percentage":
            discount = int(amount * coupon["discount"] / 100)
            final = amount - discount
        elif coupon["type"] == "fixed":
            discount = coupon["discount"]
            final = amount - discount
        else:
            discount = 0
            final = amount
        
        conn.close()
        return {
            "code": code,
            "discount": discount,
            "final": final,
            "type": coupon["type"]
        }
    
    def use_coupon(self, code, user_id):
        """Mark coupon as used"""
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("INSERT INTO coupons (code, user_id, used, expires) VALUES (?, ?, 1, ?)",
                  (code, user_id, (datetime.now() + timedelta(days=30)).isoformat()))
        conn.commit()
        conn.close()
    
    # ===== PRICE ALERTS (Feature 6) =====
    
    def add_price_alert(self, user_id, card_name, target_price):
        """Add price alert"""
        conn = self._get_conn()
        c = conn.cursor()
        current_price = GIFT_CARDS[card_name]["base_price"][500]  # Use base price
        c.execute("INSERT INTO price_alerts (user_id, card_name, target_price, current_price, created) VALUES (?, ?, ?, ?, ?)",
                  (user_id, card_name, target_price, current_price, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    
    def check_price_alerts(self, card_name, new_price):
        """Check and trigger price alerts"""
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT user_id, target_price FROM price_alerts WHERE card_name = ? AND active = 1 AND target_price >= ?",
                  (card_name, new_price))
        alerts = c.fetchall()
        conn.close()
        return alerts
    
    # ===== STATISTICS FOR ADMIN DASHBOARD (Feature 24) =====
    
    def get_dashboard_stats(self):
        """Get comprehensive statistics for admin dashboard"""
        conn = self._get_conn()
        c = conn.cursor()
        
        stats = {}
        
        # User statistics
        c.execute("SELECT COUNT(*) FROM users")
        stats['total_users'] = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM users WHERE date(last_active) = date('now')")
        stats['active_today'] = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM users WHERE date(join_date) = date('now')")
        stats['new_today'] = c.fetchone()[0]
        
        # Transaction statistics
        c.execute("SELECT COUNT(*) FROM transactions")
        stats['total_transactions'] = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM transactions WHERE date(timestamp) = date('now')")
        stats['transactions_today'] = c.fetchone()[0]
        
        c.execute("SELECT SUM(amount) FROM transactions WHERE type = 'credit'")
        stats['total_revenue'] = c.fetchone()[0] or 0
        
        c.execute("SELECT SUM(amount) FROM transactions WHERE type = 'credit' AND date(timestamp) = date('now')")
        stats['revenue_today'] = c.fetchone()[0] or 0
        
        # Purchase statistics
        c.execute("SELECT COUNT(*) FROM purchases")
        stats['total_purchases'] = c.fetchone()[0]
        
        c.execute("SELECT SUM(price) FROM purchases")
        stats['total_spent'] = c.fetchone()[0] or 0
        
        c.execute("SELECT card_name, COUNT(*) as count FROM purchases GROUP BY card_name ORDER BY count DESC LIMIT 5")
        stats['top_cards'] = c.fetchall()
        
        # Verification statistics
        c.execute("SELECT COUNT(*) FROM verifications WHERE status = 'pending'")
        stats['pending'] = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM verifications WHERE status = 'approved' AND date(verified_at) = date('now')")
        stats['approved_today'] = c.fetchone()[0]
        
        # Referral statistics
        c.execute("SELECT COUNT(*) FROM referrals")
        stats['total_referrals'] = c.fetchone()[0]
        
        c.execute("SELECT SUM(bonus_amount) FROM referrals")
        stats['total_bonus'] = c.fetchone()[0] or 0
        
        # Daily rewards statistics
        c.execute("SELECT COUNT(*) FROM daily_rewards WHERE claim_date = date('now')")
        stats['daily_claims'] = c.fetchone()[0]
        
        c.execute("SELECT AVG(streak) FROM daily_rewards WHERE claim_date = date('now')")
        stats['avg_streak'] = c.fetchone()[0] or 0
        
        conn.close()
        return stats
    
    def log_admin_action(self, admin_id, action, details):
        """Log admin action"""
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("INSERT INTO admin_logs (admin_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
                  (admin_id, action, details, datetime.now().isoformat()))
        conn.commit()
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

def calculate_bulk_discount(quantity, price):
    """Calculate bulk discount based on quantity"""
    if quantity >= 50:
        discount = BULK_DISCOUNTS[50]
    elif quantity >= 25:
        discount = BULK_DISCOUNTS[25]
    elif quantity >= 10:
        discount = BULK_DISCOUNTS[10]
    elif quantity >= 5:
        discount = BULK_DISCOUNTS[5]
    elif quantity >= 3:
        discount = BULK_DISCOUNTS[3]
    else:
        discount = 0
    
    total = price * quantity
    discount_amount = int(total * discount / 100)
    final = total - discount_amount
    
    return {
        "quantity": quantity,
        "unit_price": price,
        "total": total,
        "discount_percent": discount,
        "discount_amount": discount_amount,
        "final": final
    }

# ===========================================================================
# LOADING ANIMATION
# ===========================================================================

LOADING_FRAMES = ["🎁", "🎀", "✨", "⭐", "🌟", "💫", "⚡", "💎"]

async def show_loading(update, message_text="Processing", duration=2):
    """Show beautiful loading animation"""
    msg = await update.message.reply_text(f"⏳ *{message_text}*", parse_mode=ParseMode.MARKDOWN)
    for i in range(duration * 2):
        frame = LOADING_FRAMES[i % len(LOADING_FRAMES)]
        await asyncio.sleep(0.5)
        await msg.edit_text(f"{frame} *{message_text}{'.' * ((i % 3) + 1)}*", parse_mode=ParseMode.MARKDOWN)
    await msg.delete()

# ===========================================================================
# MEMBERSHIP CHECK
# ===========================================================================

async def check_membership(user_id, context):
    """Check if user is member of main channel"""
    try:
        member = await context.bot.get_chat_member(chat_id=MAIN_CHANNEL, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Membership check error: {e}")
        return False

# ===========================================================================
# ADMIN DECORATOR
# ===========================================================================

def admin_only(func):
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        user = update.effective_user
        if user.id != ADMIN_ID:
            await update.message.reply_text(f"❌ *Unauthorized*", parse_mode=ParseMode.MARKDOWN)
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# ===========================================================================
# START COMMAND - WITH ENHANCED UI
# ===========================================================================

async def start(update, context):
    user = update.effective_user
    
    # React to message (Feature 1)
    await Animations.react(update, "👋")
    
    if not all([BOT_TOKEN, ADMIN_ID, UPI_ID]):
        await update.message.reply_text(f"❌ *Configuration Error*", parse_mode=ParseMode.MARKDOWN)
        return
    
    # Create user in database
    db_user = db.get_user(user.id)
    if not db_user:
        referred = None
        if context.args and context.args[0].startswith('ref_'):
            try:
                referred = int(context.args[0].replace('ref_', ''))
                if referred == user.id: referred = None
            except: pass
        db.create_user(user.id, user.username, user.first_name, referred)
        if WELCOME_BONUS > 0: 
            db.update_balance(user.id, WELCOME_BONUS, 'bonus')
        if referred:
            db.process_referral(referred, user.id)
            try:
                await context.bot.send_message(referred,
                    f"👥 *Referral Bonus!*\n\n{user.first_name} joined!\n+₹{REFERRAL_BONUS}",
                    parse_mode=ParseMode.MARKDOWN)
            except: pass
    
    db.update_active(user.id)
    
    # Show typing indicator (Feature 2)
    await Animations.typing(update, 1)
    
    # Check channel membership
    is_member = await check_membership(user.id, context)
    
    if not is_member:
        welcome = (
            f"{EnhancedUI.fancy_header('WELCOME', '🎁', 40)}\n\n"
            f"👋 *Hello {user.first_name}!*\n\n"
            f"🎁 *Get Gift Cards at 80% OFF*\n"
            f"⭐ *7+ Premium Brands*\n"
            f"⚡ *Instant Email Delivery*\n"
            f"🛡️ *100% Working Codes*\n\n"
            f"🔒 *MANDATORY VERIFICATION*\n"
            f"You MUST join our main channel to use this bot.\n\n"
            f"👇 *Click below to join and verify*"
        )
        keyboard = [[
            InlineKeyboardButton(f"📢 JOIN MAIN CHANNEL", url="https://t.me/gift_card_main"),
            InlineKeyboardButton(f"✅ I HAVE JOINED", callback_data="verify")
        ]]
        await update.message.reply_text(welcome, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # Show loading animation for verified users
    await show_loading(update, "Loading Gift Cards", 1)
    
    # Get user stats for badge
    badge = EnhancedUI.user_badge(db_user.get('total_purchases', 0))
    
    # Main menu with enhanced UI
    balance = db.get_balance(user.id)
    menu = (
        f"{EnhancedUI.fancy_header('MAIN MENU', '🎁', 40)}\n\n"
        f"👤 *User:* {user.first_name} {badge}\n"
        f"💰 *Balance:* {EnhancedUI.format_currency(balance)}\n"
        f"📊 *Purchases:* {db_user.get('total_purchases', 0)}\n"
        f"{EnhancedUI.progress_bar(db_user.get('total_purchases', 0), 100, 15)}\n\n"
        f"*Select an option:* ⬇️"
    )
    keyboard = [
        [InlineKeyboardButton(f"🎁 GIFT CARDS", callback_data="giftcard")],
        [InlineKeyboardButton(f"💰 ADD MONEY", callback_data="topup")],
        [InlineKeyboardButton(f"👛 MY WALLET", callback_data="wallet")],
        [InlineKeyboardButton(f"👥 REFERRAL (₹{REFERRAL_BONUS}/friend)", callback_data="referral")],
        [InlineKeyboardButton(f"📅 DAILY REWARD", callback_data="daily")],
        [InlineKeyboardButton(f"🏷️ COUPONS", callback_data="coupon")],
        [InlineKeyboardButton(f"📦 BULK PURCHASE", callback_data="bulk")],
        [InlineKeyboardButton(f"🎁 SEND GIFT", callback_data="gift")],
        [InlineKeyboardButton(f"🔔 PRICE ALERT", callback_data="alert")],
        [InlineKeyboardButton(f"🌐 LANGUAGE", callback_data="language")],
        [InlineKeyboardButton(f"🆘 SUPPORT", callback_data="support")]
    ]
    await update.message.reply_text(menu, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

# ===========================================================================
# DAILY REWARD HANDLER (Feature 3)
# ===========================================================================

async def daily_reward(update, context):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    # Show typing indicator
    await Animations.typing(update, 0.5)
    
    result = db.claim_daily_reward(user.id)
    
    if result is None:
        # Already claimed today
        await query.edit_message_text(
            f"{EnhancedUI.fancy_header('DAILY REWARD', '📅', 40)}\n\n"
            f"❌ *Already claimed today!*\n\n"
            f"Come back tomorrow for your next reward.\n\n"
            f"Keep your streak going! 🔥",
            parse_mode="HTML"
        )
    else:
        # Success
        await query.edit_message_text(
            f"{EnhancedUI.fancy_header('DAILY REWARD', '🎁', 40)}\n\n"
            f"✅ *Reward Claimed!*\n\n"
            f"🔥 *Streak:* {result['streak']} days\n"
            f"💰 *Amount:* ₹{result['reward']}\n\n"
            f"{EnhancedUI.progress_bar(result['streak'] % 7, 7, 10)}\n\n"
            f"Come back tomorrow for more!",
            parse_mode="HTML"
        )
        
        # React with success
        await Animations.react(update, "🎁")

# ===========================================================================
# COUPON HANDLER (Feature 10)
# ===========================================================================

async def coupon_menu(update, context):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        f"{EnhancedUI.fancy_header('COUPONS', '🏷️', 40)}\n\n"
        f"✨ *Available Coupons:*\n\n"
        f"• WELCOME10 - 10% off (Min ₹100)\n"
        f"• SAVE20 - ₹20 off (Min ₹200)\n"
        f"• FIRST50 - ₹50 off (Min ₹500)\n"
        f"• DIWALI22 - 22% off (Min ₹200)\n"
        f"• HOLI15 - 15% off (Min ₹150)\n"
        f"• FLASH50 - 50% off (Min ₹500)\n\n"
        f"📝 *Enter coupon code:*",
        parse_mode="HTML"
    )
    return STATE_COUPON

async def handle_coupon(update, context):
    code = update.message.text.strip().upper()
    user = update.effective_user
    
    # Show typing
    await Animations.typing(update, 0.5)
    
    # Store coupon in context for later use
    context.user_data['coupon'] = code
    
    result = db.validate_coupon(code, 100)  # Sample validation
    
    if result and "error" not in result:
        await update.message.reply_text(
            f"✅ *Coupon Valid!*\n\n"
            f"Code: `{code}`\n"
            f"Discount: {result.get('discount', 0)}%\n\n"
            f"Use this coupon during checkout!",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        error_msg = result.get("error", "Invalid coupon") if result else "Invalid coupon"
        await update.message.reply_text(
            f"❌ *{error_msg}*",
            parse_mode=ParseMode.MARKDOWN
        )
    
    return ConversationHandler.END

# ===========================================================================
# BULK PURCHASE HANDLER (Feature 12)
# ===========================================================================

async def bulk_menu(update, context):
    query = update.callback_query
    await query.answer()
    
    text = (
        f"{EnhancedUI.fancy_header('BULK PURCHASE', '📦', 40)}\n\n"
        f"✨ *Bulk Discounts:*\n\n"
        f"• 3+ cards → 3% OFF\n"
        f"• 5+ cards → 5% OFF\n"
        f"• 10+ cards → 10% OFF\n"
        f"• 25+ cards → 15% OFF\n"
        f"• 50+ cards → 20% OFF\n\n"
        f"📝 *Enter quantity:*"
    )
    
    await query.edit_message_text(text, parse_mode="HTML")
    return STATE_BULK_COUNT

async def handle_bulk_count(update, context):
    try:
        quantity = int(update.message.text.strip())
        context.user_data['bulk_quantity'] = quantity
    except:
        await update.message.reply_text("❌ Invalid quantity")
        return STATE_BULK_COUNT
    
    # Show available cards
    text = f"{EnhancedUI.fancy_header('BULK PURCHASE', '📦', 40)}\n\nSelect card:\n\n"
    keyboard = []
    for cid, card in GIFT_CARDS.items():
        keyboard.append([InlineKeyboardButton(
            f"{card['full_emoji']} {card['name']}",
            callback_data=f"bulk_{cid}"
        )])
    
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END

async def handle_bulk_card(update, context):
    query = update.callback_query
    await query.answer()
    
    cid = query.data.replace("bulk_", "")
    card = GIFT_CARDS.get(cid)
    quantity = context.user_data.get('bulk_quantity', 1)
    
    price = PRICES[500]  # Base price
    discount_info = calculate_bulk_discount(quantity, price)
    
    text = (
        f"{EnhancedUI.fancy_header('BULK ORDER', '📦', 40)}\n\n"
        f"Card: {card['full_emoji']} {card['name']}\n"
        f"Quantity: {quantity}\n\n"
        f"Unit Price: ₹{price}\n"
        f"Total: ₹{discount_info['total']}\n"
        f"Discount: {discount_info['discount_percent']}% (₹{discount_info['discount_amount']})\n"
        f"*Final: ₹{discount_info['final']}*\n\n"
        f"Proceed to payment?"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ PAY NOW", callback_data=f"bulk_pay_{cid}_{quantity}")],
        [InlineKeyboardButton("❌ CANCEL", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

# ===========================================================================
# GIFT CARD GIFTING (Feature 13)
# ===========================================================================

async def gift_menu(update, context):
    query = update.callback_query
    await query.answer()
    
    text = f"{EnhancedUI.fancy_header('SEND GIFT', '🎁', 40)}\n\nSelect card to gift:\n\n"
    keyboard = []
    for cid, card in GIFT_CARDS.items():
        keyboard.append([InlineKeyboardButton(
            f"{card['full_emoji']} {card['name']}",
            callback_data=f"gift_card_{cid}"
        )])
    
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_gift_card(update, context):
    query = update.callback_query
    await query.answer()
    
    cid = query.data.replace("gift_card_", "")
    context.user_data['gift_card'] = cid
    
    text = f"{EnhancedUI.fancy_header('SEND GIFT', '🎁', 40)}\n\nEnter recipient's email:"
    await query.edit_message_text(text, parse_mode="HTML")
    return STATE_GIFT_EMAIL

async def handle_gift_email(update, context):
    email = update.message.text.strip()
    
    if not validate_email(email):
        await update.message.reply_text("❌ Invalid email")
        return STATE_GIFT_EMAIL
    
    cid = context.user_data.get('gift_card')
    card = GIFT_CARDS.get(cid)
    
    text = (
        f"{EnhancedUI.fancy_header('GIFT DETAILS', '🎁', 40)}\n\n"
        f"Card: {card['full_emoji']} {card['name']}\n"
        f"Recipient: {email}\n\n"
        f"Add a personal message (optional):"
    )
    
    await update.message.reply_text(text, parse_mode="HTML")
    # Store email and continue
    context.user_data['gift_email'] = email
    # Continue to message input...
    return ConversationHandler.END

# ===========================================================================
# PRICE ALERT HANDLER (Feature 6)
# ===========================================================================

async def alert_menu(update, context):
    query = update.callback_query
    await query.answer()
    
    text = f"{EnhancedUI.fancy_header('PRICE ALERT', '🔔', 40)}\n\nSelect card to track:\n\n"
    keyboard = []
    for cid, card in GIFT_CARDS.items():
        keyboard.append([InlineKeyboardButton(
            f"{card['full_emoji']} {card['name']}",
            callback_data=f"alert_card_{cid}"
        )])
    
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_alert_card(update, context):
    query = update.callback_query
    await query.answer()
    
    cid = query.data.replace("alert_card_", "")
    context.user_data['alert_card'] = cid
    
    text = f"{EnhancedUI.fancy_header('PRICE ALERT', '🔔', 40)}\n\nEnter target price (e.g., 80 for ₹80):"
    await query.edit_message_text(text, parse_mode="HTML")
    return STATE_PRICE_ALERT

async def handle_alert_price(update, context):
    try:
        target = int(update.message.text.strip())
        cid = context.user_data.get('alert_card')
        card = GIFT_CARDS.get(cid)
        
        db.add_price_alert(update.effective_user.id, card['name'], target)
        
        await update.message.reply_text(
            f"✅ *Alert Set!*\n\n"
            f"We'll notify you when {card['name']} price drops below ₹{target}.",
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        await update.message.reply_text("❌ Invalid price")
    
    return ConversationHandler.END

# ===========================================================================
# LANGUAGE SELECTOR (Feature 23)
# ===========================================================================

async def language_menu(update, context):
    query = update.callback_query
    await query.answer()
    
    text = f"{EnhancedUI.fancy_header('LANGUAGE', '🌐', 40)}\n\nSelect your language:\n\n"
    keyboard = []
    for code, lang in LANGUAGES.items():
        keyboard.append([InlineKeyboardButton(
            f"{lang['flag']} {lang['name']}",
            callback_data=f"lang_{code}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 BACK", callback_data="main_menu")])
    
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_language(update, context):
    query = update.callback_query
    await query.answer()
    
    code = query.data.replace("lang_", "")
    user = query.from_user
    
    db.update_user(user.id, language=code)
    
    # Get translation
    msg = Translator.get_text(user.id, "welcome", code)
    
    await query.edit_message_text(
        f"✅ *Language set to {LANGUAGES[code]['name']}!*\n\n{msg}",
        parse_mode=ParseMode.MARKDOWN
    )

# ===========================================================================
# ADMIN DASHBOARD (Feature 24)
# ===========================================================================

@admin_only
async def admin_dashboard(update, context):
    """Admin dashboard with statistics"""
    await Animations.typing(update, 1)
    
    stats = db.get_dashboard_stats()
    db.log_admin_action(update.effective_user.id, "view_dashboard", "Viewed admin dashboard")
    
    dashboard = (
        f"{EnhancedUI.fancy_header('ADMIN DASHBOARD', '📊', 50)}\n\n"
        f"📅 *{datetime.now().strftime('%d %b %Y, %I:%M %p')}*\n"
        f"{'─' * 40}\n\n"
        f"*👥 USER STATISTICS*\n"
        f"• Total Users: `{stats['total_users']:,}`\n"
        f"• Active Today: `{stats['active_today']}`\n"
        f"• New Today: `{stats['new_today']}`\n\n"
        f"*💰 FINANCIAL STATISTICS*\n"
        f"• Total Revenue: `{EnhancedUI.format_currency(stats['total_revenue'])}`\n"
        f"• Revenue Today: `{EnhancedUI.format_currency(stats['revenue_today'])}`\n"
        f"• Total Spent: `{EnhancedUI.format_currency(stats['total_spent'])}`\n\n"
        f"*📊 TRANSACTIONS*\n"
        f"• Total: `{stats['total_transactions']:,}`\n"
        f"• Today: `{stats['transactions_today']}`\n"
        f"• Pending: `{stats['pending']}`\n\n"
        f"*🏆 TOP CARDS*\n"
    )
    
    for i, (card, count) in enumerate(stats['top_cards'], 1):
        dashboard += f"• {i}. {card}: `{count}` purchases\n"
    
    dashboard += (
        f"\n*👥 REFERRALS*\n"
        f"• Total: `{stats['total_referrals']}`\n"
        f"• Bonus Paid: `{EnhancedUI.format_currency(stats['total_bonus'])}`\n\n"
        f"*📅 DAILY REWARDS*\n"
        f"• Claims Today: `{stats['daily_claims']}`\n"
        f"• Avg Streak: `{stats['avg_streak']:.1f} days`\n"
        f"{'─' * 40}"
    )
    
    keyboard = [
        [InlineKeyboardButton("📤 EXPORT DATA", callback_data="admin_export")],
        [InlineKeyboardButton("🔄 REFRESH", callback_data="admin_refresh")],
        [InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]
    ]
    
    await update.message.reply_text(dashboard, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

@admin_only
async def admin_export(update, context):
    """Export data as CSV"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("📤 *Exporting data...*", parse_mode=ParseMode.MARKDOWN)
    
    # Export users
    conn = sqlite3.connect(DATABASE_PATH)
    df_users = pd.read_sql_query("SELECT user_id, username, first_name, balance, total_purchases, join_date FROM users", conn)
    df_users.to_csv('users_export.csv', index=False)
    
    # Export transactions
    df_trans = pd.read_sql_query("SELECT * FROM transactions", conn)
    df_trans.to_csv('transactions_export.csv', index=False)
    
    # Export purchases
    df_purch = pd.read_sql_query("SELECT * FROM purchases", conn)
    df_purch.to_csv('purchases_export.csv', index=False)
    
    conn.close()
    
    # Send files
    await context.bot.send_document(
        chat_id=update.effective_user.id,
        document=open('users_export.csv', 'rb'),
        caption="📊 Users Data Export"
    )
    await context.bot.send_document(
        chat_id=update.effective_user.id,
        document=open('transactions_export.csv', 'rb'),
        caption="📊 Transactions Data Export"
    )
    await context.bot.send_document(
        chat_id=update.effective_user.id,
        document=open('purchases_export.csv', 'rb'),
        caption="📊 Purchases Data Export"
    )
    
    db.log_admin_action(update.effective_user.id, "export_data", "Exported all data")
    
    await query.edit_message_text("✅ *Data exported successfully!*", parse_mode=ParseMode.MARKDOWN)

# ===========================================================================
# BUTTON HANDLER - UPDATED WITH NEW FEATURES
# ===========================================================================

async def button_handler(update, context):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data
    
    logger.info(f"Button clicked: {data} by {user.first_name}")
    
    db.update_active(user.id)
    
    # React to button click
    await Animations.react(update, "👆")
    
    # ===== VERIFY BUTTON =====
    if data == "verify":
        is_member = await check_membership(user.id, context)
        
        if is_member:
            balance = db.get_balance(user.id)
            await show_loading(update, "Verifying", 1)
            success = (
                f"{EnhancedUI.fancy_header('VERIFIED', '✅', 40)}\n\n"
                f"👋 *Welcome {user.first_name}!*\n"
                f"💰 *Balance:* {EnhancedUI.format_currency(balance)}\n\n"
                f"🚀 *You now have full access!*"
            )
            keyboard = [
                [InlineKeyboardButton(f"🎁 GIFT CARDS", callback_data="giftcard")],
                [InlineKeyboardButton(f"💰 ADD MONEY", callback_data="topup")],
                [InlineKeyboardButton(f"👛 MY WALLET", callback_data="wallet")]
            ]
            await query.edit_message_text(success, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            fail = (
                f"{EnhancedUI.fancy_header('FAILED', '❌', 40)}\n\n"
                f"You haven't joined our channel yet!\n\n"
                f"1️⃣ Click JOIN CHANNEL\n"
                f"2️⃣ Join @gift_card_main\n"
                f"3️⃣ Click VERIFY again"
            )
            keyboard = [[
                InlineKeyboardButton(f"📢 JOIN CHANNEL", url="https://t.me/gift_card_main"),
                InlineKeyboardButton(f"🔄 VERIFY AGAIN", callback_data="verify")
            ]]
            await query.edit_message_text(fail, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # Check membership for ALL other actions
    is_member = await check_membership(user.id, context)
    if not is_member:
        keyboard = [[
            InlineKeyboardButton(f"📢 JOIN CHANNEL", url="https://t.me/gift_card_main"),
            InlineKeyboardButton(f"✅ VERIFY", callback_data="verify")
        ]]
        await query.edit_message_text(
            f"⚠️ *ACCESS DENIED*\n\nYou MUST join @gift_card_main to use the bot!",
            parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # ===== NEW FEATURE HANDLERS =====
    if data == "daily":
        await daily_reward(update, context)
    elif data == "coupon":
        await coupon_menu(update, context)
    elif data == "bulk":
        await bulk_menu(update, context)
    elif data.startswith("bulk_"):
        await handle_bulk_card(update, context)
    elif data == "gift":
        await gift_menu(update, context)
    elif data.startswith("gift_card_"):
        await handle_gift_card(update, context)
    elif data == "alert":
        await alert_menu(update, context)
    elif data.startswith("alert_card_"):
        await handle_alert_card(update, context)
    elif data == "language":
        await language_menu(update, context)
    elif data.startswith("lang_"):
        await handle_language(update, context)
    elif data == "admin_dashboard":
        await admin_dashboard(update, context)
    elif data == "admin_export":
        await admin_export(update, context)
    elif data == "admin_refresh":
        await admin_dashboard(update, context)
    
    # ===== MAIN MENU =====
    elif data == "main_menu":
        balance = db.get_balance(user.id)
        db_user = db.get_user(user.id)
        badge = EnhancedUI.user_badge(db_user.get('total_purchases', 0))
        
        menu = (
            f"{EnhancedUI.fancy_header('MAIN MENU', '🎁', 40)}\n\n"
            f"👤 *User:* {user.first_name} {badge}\n"
            f"💰 *Balance:* {EnhancedUI.format_currency(balance)}\n"
            f"📊 *Purchases:* {db_user.get('total_purchases', 0)}\n"
            f"{EnhancedUI.progress_bar(db_user.get('total_purchases', 0), 100, 15)}\n\n"
            f"*Select an option:* ⬇️"
        )
        keyboard = [
            [InlineKeyboardButton(f"🎁 GIFT CARDS", callback_data="giftcard")],
            [InlineKeyboardButton(f"💰 ADD MONEY", callback_data="topup")],
            [InlineKeyboardButton(f"👛 MY WALLET", callback_data="wallet")],
            [InlineKeyboardButton(f"👥 REFERRAL (₹{REFERRAL_BONUS}/friend)", callback_data="referral")],
            [InlineKeyboardButton(f"📅 DAILY REWARD", callback_data="daily")],
            [InlineKeyboardButton(f"🏷️ COUPONS", callback_data="coupon")],
            [InlineKeyboardButton(f"📦 BULK PURCHASE", callback_data="bulk")],
            [InlineKeyboardButton(f"🎁 SEND GIFT", callback_data="gift")],
            [InlineKeyboardButton(f"🔔 PRICE ALERT", callback_data="alert")],
            [InlineKeyboardButton(f"🌐 LANGUAGE", callback_data="language")],
            [InlineKeyboardButton(f"🆘 SUPPORT", callback_data="support")]
        ]
        await query.edit_message_text(menu, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    
    # ===== GIFT CARDS =====
    elif data == "giftcard":
        text = f"{EnhancedUI.fancy_header('GIFT CARDS', '🎁', 40)}\n\n{EnhancedUI.price_table(PRICES)}\n\n*Select a brand:*\n"
        keyboard = []
        for cid, card in GIFT_CARDS.items():
            trending = "🔥" if card.get('trending', False) else ""
            keyboard.append([InlineKeyboardButton(
                f"{card['full_emoji']} {card['name']} {trending}",
                callback_data=f"card_{cid}"
            )])
        keyboard.append([InlineKeyboardButton(f"🔙 BACK", callback_data="main_menu")])
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    
    # ===== CARD DETAILS =====
    elif data.startswith("card_"):
        cid = data.replace("card_", "")
        card = GIFT_CARDS.get(cid)
        if not card: return
        
        # Check for price alerts
        alerts = db.check_price_alerts(card['name'], PRICES[500])
        alert_text = "🔔 *Price Alert Active!*" if alerts else ""
        
        text = (
            f"{card['full_emoji']} *{card['name']} GIFT CARD* {card['full_emoji']}\n"
            f"{'─' * 40}\n\n"
            f"✨ *Features:*\n"
            f"• Instant Email Delivery\n"
            f"• 100% Working Codes\n"
            f"• No Expiry\n"
            f"{EnhancedUI.rating_stars(4.8)} 4.8/5\n\n"
            f"{EnhancedUI.price_table(card['base_price'])}\n\n"
            f"{alert_text}\n"
            f"*Select amount:*\n"
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
        
        keyboard.append([InlineKeyboardButton(f"🔙 BACK", callback_data="giftcard")])
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    
    # ===== BUY CARD =====
    elif data.startswith("buy_"):
        parts = data.split("_")
        if len(parts) < 3: return
        cid, value = parts[1], int(parts[2])
        card = GIFT_CARDS.get(cid)
        if not card or value not in PRICES: return
        
        price = PRICES[value]
        balance = db.get_balance(user.id)
        
        # Check for coupon in context
        coupon_code = context.user_data.get('coupon')
        if coupon_code:
            coupon_result = db.validate_coupon(coupon_code, price)
            if coupon_result and "error" not in coupon_result:
                price = coupon_result['final']
        
        if balance < price:
            keyboard = [[InlineKeyboardButton(f"💰 ADD MONEY", callback_data="topup")]]
            await query.edit_message_text(
                f"❌ *Insufficient Balance*\n\nNeed: `{EnhancedUI.format_currency(price)}`\nYou have: `{EnhancedUI.format_currency(balance)}`",
                parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        savings = value - price
        percent = int(((value - price) / value) * 100)
        context.user_data['purchase'] = {'card': card['name'], 'emoji': card['full_emoji'], 'value': value, 'price': price}
        
        await query.edit_message_text(
            f"{EnhancedUI.fancy_header('PURCHASE', '✅', 40)}\n\n"
            f"{card['full_emoji']} *{card['name']} ₹{value}*\n"
            f"Price: `{EnhancedUI.format_currency(price)}`\n"
            f"You Save: `{EnhancedUI.format_currency(savings)}` ({percent}% OFF)\n\n"
            f"📧 *Enter your email for delivery:*",
            parse_mode="HTML"
        )
        return STATE_EMAIL
    
    # ===== TOP UP WITH AMOUNT BUTTONS =====
    elif data == "topup":
        text = (
            f"{EnhancedUI.fancy_header('ADD MONEY', '💰', 40)}\n\n"
            f"*Select amount or enter manually:*\n\n"
        )
        
        # Create amount buttons
        keyboard = []
        for row in AMOUNT_BUTTONS:
            button_row = []
            for amt in row:
                button_row.append(InlineKeyboardButton(f"₹{amt}", callback_data=f"amount_{amt}"))
            keyboard.append(button_row)
        
        keyboard.append([InlineKeyboardButton(f"🔙 BACK", callback_data="main_menu")])
        
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== AMOUNT BUTTON SELECTED =====
    elif data.startswith("amount_"):
        amount = int(data.replace("amount_", ""))
        fee, final = calculate_fee(amount)
        context.user_data['topup'] = {'amount': amount, 'fee': fee, 'final': final}
        
        keyboard = [
            [InlineKeyboardButton(f"✅ I HAVE PAID", callback_data="paid")],
            [InlineKeyboardButton(f"🔙 CANCEL", callback_data="main_menu")]
        ]
        
        # Generate QR code dynamically
        qr = qrcode.QRCode()
        qr.add_data(f"upi://pay?pa={UPI_ID}&pn=GiftCardBot&am={amount}")
        qr.make()
        img = qr.make_image()
        
        bio = BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        
        payment_text = (
            f"{EnhancedUI.fancy_header('PAYMENT', '💰', 40)}\n\n"
            f"📱 *UPI ID:* `{UPI_ID}`\n"
            f"💰 *Amount:* `{EnhancedUI.format_currency(amount)}`\n"
            f"📉 *Fee:* `{EnhancedUI.format_currency(fee) if fee > 0 else 'No fee'}`\n"
            f"✨ *You get:* `{EnhancedUI.format_currency(final)}`\n\n"
            f"{'─' * 40}\n\n"
            f"📱 *How to Pay:*\n"
            f"1️⃣ Scan QR code or pay to UPI ID\n"
            f"2️⃣ Take a screenshot\n"
            f"3️⃣ Copy UTR number\n"
            f"4️⃣ Click 'I HAVE PAID'\n\n"
            f"⏳ *Auto-cancel in 10 minutes*"
        )
        
        await query.message.reply_photo(
            photo=bio,
            caption=payment_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        await query.edit_message_text(
            f"{EnhancedUI.fancy_header('AMOUNT SELECTED', '✅', 40)}\n\n"
            f"Amount: ₹{amount}\n\n"
            f"Please check the payment details above.",
            parse_mode="HTML"
        )
    
    # ===== WALLET =====
    elif data == "wallet":
        balance = db.get_balance(user.id)
        db_user = db.get_user(user.id)
        
        text = (
            f"{EnhancedUI.fancy_header('YOUR WALLET', '👛', 40)}\n\n"
            f"💰 *Balance:* {EnhancedUI.format_currency(balance)}\n"
            f"💳 *Total Spent:* {EnhancedUI.format_currency(db_user['total_spent'])}\n"
            f"📦 *Purchases:* {db_user['total_purchases']}\n"
            f"👥 *Referrals:* {db_user['total_referrals']}\n"
            f"{EnhancedUI.progress_bar(db_user['total_purchases'], 100, 15)}\n\n"
            f"*Quick Actions:* ⬇️"
        )
        keyboard = [
            [InlineKeyboardButton(f"💰 ADD MONEY", callback_data="topup")],
            [InlineKeyboardButton(f"🎁 BUY CARDS", callback_data="giftcard")],
            [InlineKeyboardButton(f"🔙 BACK", callback_data="main_menu")]
        ]
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    
    # ===== REFERRAL =====
    elif data == "referral":
        bot = await context.bot.get_me()
        link = f"https://t.me/{bot.username}?start=ref_{user.id}"
        text = (
            f"{EnhancedUI.fancy_header('REFERRAL', '👥', 40)}\n\n"
            f"💰 *Earn ₹{REFERRAL_BONUS} per friend!*\n\n"
            f"🔗 *Your Referral Link:*\n"
            f"<code>{link}</code>\n\n"
            f"📌 *How it works:*\n"
            f"1️⃣ Share your link with friends\n"
            f"2️⃣ Friend joins using your link\n"
            f"3️⃣ You get ₹{REFERRAL_BONUS} instantly\n"
            f"4️⃣ Friend gets ₹{WELCOME_BONUS} welcome bonus\n\n"
            f"🚀 *Start sharing now!*"
        )
        keyboard = [[InlineKeyboardButton(f"🔙 BACK", callback_data="main_menu")]]
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    
    # ===== SUPPORT =====
    elif data == "support":
        text = (
            f"{EnhancedUI.fancy_header('SUPPORT', '🆘', 40)}\n\n"
            f"❓ *Frequently Asked Questions:*\n\n"
            f"1️⃣ *How to buy a gift card?*\n"
            f"   → Add money → Select card → Enter email\n\n"
            f"2️⃣ *How long does delivery take?*\n"
            f"   → Instant (2-5 minutes)\n\n"
            f"3️⃣ *Payment not credited?*\n"
            f"   → Send screenshot + UTR to admin\n\n"
            f"4️⃣ *Card not received?*\n"
            f"   → Check spam folder\n\n"
            f"{'─' * 40}\n\n"
            f"📝 *Type your issue below and we'll respond within 24h*"
        )
        keyboard = [[InlineKeyboardButton(f"🔙 BACK", callback_data="main_menu")]]
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        return STATE_SUPPORT

# ===========================================================================
# PAID HANDLER
# ===========================================================================

async def handle_paid(update, context):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    if 'topup' not in context.user_data:
        await query.edit_message_text(
            f"❌ *Session Expired*\n\nPlease start over.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    data = context.user_data['topup']
    context.user_data['verification'] = {
        'amount': data['amount'],
        'fee': data['fee'],
        'final': data['final']
    }
    
    await query.edit_message_text(
        f"{EnhancedUI.fancy_header('SEND PROOF', '📤', 40)}\n\n"
        f"Amount: `{EnhancedUI.format_currency(data['amount'])}`\n"
        f"You get: `{EnhancedUI.format_currency(data['final'])}`\n\n"
        f"1️⃣ Send SCREENSHOT of payment\n"
        f"2️⃣ Send UTR number\n\n"
        f"📌 *UTR Example:* `SBIN1234567890`",
        parse_mode="HTML"
    )
    
    return STATE_SCREENSHOT

# ===========================================================================
# SCREENSHOT HANDLER
# ===========================================================================

async def handle_screenshot(update, context):
    user = update.effective_user
    
    if not update.message.photo:
        await update.message.reply_text(f"❌ *Please send a PHOTO*", parse_mode=ParseMode.MARKDOWN)
        return STATE_SCREENSHOT
    
    await Animations.uploading(update, 1)
    
    context.user_data['screenshot'] = update.message.photo[-1].file_id
    logger.info(f"Screenshot received from {user.first_name}")
    
    await update.message.reply_text(
        f"✅ *Screenshot Received*\n\nNow send UTR number:",
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
            f"❌ *Invalid UTR*\n\nUTR should be 12-22 characters.",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_UTR
    
    if 'verification' not in context.user_data or 'screenshot' not in context.user_data:
        await update.message.reply_text(
            f"❌ *Session Expired*\n\nPlease start over.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    data = context.user_data['verification']
    screenshot = context.user_data['screenshot']
    
    vid = db.create_verification(
        user.id, 
        data['amount'], 
        data['fee'], 
        data['final'], 
        utr, 
        screenshot
    )
    
    logger.info(f"Verification created: {vid} for user {user.first_name}")
    
    await context.bot.send_photo(
        chat_id=ADMIN_CHANNEL_ID,
        photo=screenshot,
        caption=(
            f"{EnhancedUI.fancy_header('NEW PAYMENT', '💰', 40)}\n\n"
            f"👤 *User:* {user.first_name}\n"
            f"🆔 *ID:* `{user.id}`\n"
            f"💰 *Amount:* `{EnhancedUI.format_currency(data['amount'])}`\n"
            f"✨ *Credit:* `{EnhancedUI.format_currency(data['final'])}`\n"
            f"🔢 *UTR:* `{utr}`\n"
            f"🆔 *Verification ID:* `{vid}`"
        ),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{vid}"),
            InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{vid}")
        ]])
    )
    
    context.user_data.clear()
    
    await update.message.reply_text(
        f"{EnhancedUI.fancy_header('SUBMITTED', '✅', 40)}\n\n"
        f"Your payment is being verified.\n"
        f"You'll be notified within 5-10 minutes.",
        parse_mode="HTML"
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
            f"❌ *Invalid Email*\n\nPlease enter a valid email.",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_EMAIL
    
    if 'purchase' not in context.user_data:
        await update.message.reply_text(
            f"❌ *Session Expired*\n\nPlease start over.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    p = context.user_data['purchase']
    balance = db.get_balance(user.id)
    
    if balance < p['price']:
        await update.message.reply_text(
            f"❌ *Insufficient Balance*",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    # Process purchase
    db.update_balance(user.id, -p['price'], 'debit')
    order_id = db.create_purchase(user.id, p['card'], p['value'], p['price'], email)
    
    context.user_data.clear()
    
    await show_loading(update, "Processing Purchase", 1)
    await Animations.react(update, "🎉")
    
    await update.message.reply_text(
        f"{EnhancedUI.fancy_header('SUCCESS', '🎉', 40)}\n\n"
        f"{p['emoji']} *{p['card']} ₹{p['value']}*\n"
        f"🆔 *Order ID:* `{order_id}`\n"
        f"📧 *Sent to:* `{email}`\n\n"
        f"✨ *Check your inbox (and spam folder)!*",
        parse_mode="HTML"
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
            f"❌ *Message Too Short*\n\nPlease describe your issue (min 10 chars).",
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
    
    await Animations.react(update, "👍")
    
    # Notify admin
    await context.bot.send_message(
        ADMIN_ID,
        f"{EnhancedUI.fancy_header('SUPPORT TICKET', '🆘', 40)}\n\n"
        f"👤 {user.first_name}\n"
        f"🆔 `{user.id}`\n"
        f"💬 {msg}",
        parse_mode="HTML"
    )
    
    await update.message.reply_text(
        f"✅ *SUPPORT SENT!*\n\nWe'll contact you within 24 hours.",
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
    
    action = parts[0]
    vid = parts[1]
    
    logger.info(f"Admin action: {action} on verification {vid}")
    db.log_admin_action(ADMIN_ID, action, f"Verification {vid}")
    
    if action == "approve":
        v = db.approve_verification(vid)
        if v:
            await query.edit_message_caption(
                caption=query.message.caption + f"\n\n✅ *APPROVED BY ADMIN*", 
                parse_mode="HTML"
            )
            await context.bot.send_message(
                v['user_id'],
                f"{EnhancedUI.fancy_header('APPROVED', '✅', 40)}\n\n"
                f"💰 `{EnhancedUI.format_currency(v['final_amount'])}` added to your balance.",
                parse_mode="HTML"
            )
            logger.info(f"Verification {vid} approved")
    
    elif action == "reject":
        db.reject_verification(vid)
        await query.edit_message_caption(
            caption=query.message.caption + f"\n\n❌ *REJECTED BY ADMIN*", 
            parse_mode="HTML"
        )
        logger.info(f"Verification {vid} rejected")

# ===========================================================================
# ADMIN COMMANDS
# ===========================================================================

@admin_only
async def admin_stats(update, context):
    stats = db.get_dashboard_stats()
    
    await update.message.reply_text(
        f"{EnhancedUI.fancy_header('STATISTICS', '📊', 40)}\n\n"
        f"👥 *Users:* `{stats['total_users']}`\n"
        f"⏳ *Pending:* `{stats['pending']}`\n"
        f"💰 *Revenue:* `{EnhancedUI.format_currency(stats['total_revenue'])}`\n"
        f"💳 *Spent:* `{EnhancedUI.format_currency(stats['total_spent'])}`",
        parse_mode="HTML"
    )

@admin_only
async def admin_force_promo(update, context):
    await show_loading(update, "Creating Promotion", 2)
    await auto_promotions(context)
    await update.message.reply_text(f"✅ *Promotion Posted!*", parse_mode=ParseMode.MARKDOWN)

# ===========================================================================
# AUTO PROMOTIONS
# ===========================================================================

async def auto_promotions(context):
    """Auto post promotions to main channel"""
    try:
        promos = [
            {
                "title": f"🔥🔥 FLASH SALE 🔥🔥",
                "content": [
                    f"🎁 *Get Gift Cards at 80% OFF!*",
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
                    f"🚀 *Join now and start saving!*"
                ]
            },
            {
                "title": f"👥👥 REFER & EARN 👥👥",
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
                    f"🚀 *Start referring now!*"
                ]
            },
            {
                "title": f"📅📅 DAILY REWARDS 📅📅",
                "content": [
                    f"📅 *Claim Daily Rewards!*",
                    "",
                    "🔥 *Streak Bonuses:*",
                    "• Day 1: ₹5",
                    "• Day 3: ₹10",
                    "• Day 7: ₹25",
                    "• Day 15: ₹60",
                    "• Day 30: ₹100",
                    "",
                    "⚡ *Don't break your streak!*",
                    "",
                    f"🚀 *Start claiming now!*"
                ]
            }
        ]
        
        promo = random.choice(promos)
        content = "\n".join(promo["content"])
        
        message = (
            f"{promo['title']}\n"
            f"{'─' * 40}\n\n"
            f"{content}\n\n"
            f"{'─' * 40}\n\n"
            f"🚀 *Join now:* @{context.bot.username}\n"
            f"{'─' * 40}"
        )
        
        keyboard = [[InlineKeyboardButton(
            f"🎁 SHOP NOW",
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
# CANCEL HANDLER
# ===========================================================================

async def cancel(update, context):
    context.user_data.clear()
    await update.message.reply_text(f"❌ *Cancelled*", parse_mode=ParseMode.MARKDOWN)
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
        BotCommand("start", "🚀 Start the bot"),
        BotCommand("cancel", "❌ Cancel"),
        BotCommand("dashboard", "📊 Admin Dashboard"),
        BotCommand("stats", "📈 Statistics"),
        BotCommand("forcepromo", "📢 Force Promotion")
    ])
    
    # Verify main channel
    try:
        await app.bot.get_chat(MAIN_CHANNEL)
        logger.info(f"✅ Main channel verified: {MAIN_CHANNEL}")
    except:
        logger.error(f"❌ Main channel not accessible: {MAIN_CHANNEL}")
    
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
    app.add_handler(CommandHandler("dashboard", admin_dashboard))
    
    # Admin command handlers
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("forcepromo", admin_force_promo))
    
    # Button handlers
    app.add_handler(CallbackQueryHandler(admin_handler, pattern="^(approve_|reject_)"))
    app.add_handler(CallbackQueryHandler(handle_paid, pattern="^paid$"))
    app.add_handler(CallbackQueryHandler(button_handler))
    
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
    
    # Coupon conversation
    coupon_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^coupon$")],
        states={STATE_COUPON: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_coupon)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(coupon_conv)
    
    # Bulk purchase conversation
    bulk_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^bulk$")],
        states={STATE_BULK_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bulk_count)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(bulk_conv)
    
    # Gift card conversation
    gift_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^gift$")],
        states={STATE_GIFT_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gift_email)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(gift_conv)
    
    # Price alert conversation
    alert_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^alert$")],
        states={STATE_PRICE_ALERT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_alert_price)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(alert_conv)
    
    # Error handler
    app.add_error_handler(error_handler)
    
    # Auto jobs
    if app.job_queue:
        app.job_queue.run_repeating(auto_promotions, interval=POST_INTERVAL, first=30)
    
    # Start
    print("\n" + "="*70)
    print(f"      🎁 GIFT CARD BOT ULTIMATE v11.0 🎁")
    print("="*70)
    print(f"✅ Bot: @GIFT_CARD_41BOT")
    print(f"📢 Main Channel: {MAIN_CHANNEL}")
    print(f"💰 Referral Bonus: ₹{REFERRAL_BONUS}")
    print(f"📅 Promotions: {POSTS_PER_DAY} posts/day")
    print(f"✨ New Features: Daily Rewards, Coupons, Bulk Purchase,")
    print(f"   Gift Gifting, Price Alerts, Multi-Language, Admin Dashboard")
    print("="*70 + "\n")
    
    app.run_polling()

if __name__ == "__main__":
    main()
