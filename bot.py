#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
===============================================================================
GIFT CARD & RECHARGE BOT - PREMIUM EDITION
===============================================================================
A fully featured Telegram bot for selling gift cards and managing recharges
with beautiful UI, complete error handling, and professional design.

Version: 5.0.0 (Stable Production Release)
Author: Professional Bot Developer
Last Updated: 2024
===============================================================================
"""

import logging
import sqlite3
import asyncio
import random
import os
import sys
import time
import json
import hashlib
import re
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union
from functools import wraps
from pathlib import Path
from collections import defaultdict
from contextlib import contextmanager
import threading
from queue import Queue
from enum import Enum

# ===========================================================================
# TELEGRAM IMPORTS
# ===========================================================================
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, 
    filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode
from telegram.error import TelegramError, RetryAfter, TimedOut, NetworkError

# ===========================================================================
# BOT CONFIGURATION
# ===========================================================================

class Config:
    """Centralized configuration management"""
    
    # Bot Credentials
    BOT_TOKEN = "8646034766:AAGXkMglnsc72ew1aGcFmWnZziwb8nfS2S8"
    ADMIN_ID = 6185091342
    
    # Channel Configuration
    MAIN_CHANNEL = "@gift_card_main"
    PROOF_CHANNEL = "@gift_card_log"
    ADMIN_CHANNEL_ID = -1003607749028
    
    # Payment Configuration
    UPI_ID = "helobiy41@ptyes"
    MIN_RECHARGE = 10
    MAX_RECHARGE = 10000
    FEE_PERCENT = 20
    FEE_THRESHOLD = 120
    
    # File Paths
    QR_CODE_PATH = "qr.jpg"
    DATABASE_PATH = "bot_database.db"
    LOG_FILE = "bot.log"
    
    # Timeouts and Limits
    SESSION_TIMEOUT = 600  # 10 minutes
    RATE_LIMIT = 30  # requests per minute
    
    # UI Configuration
    BOT_NAME = "🎁 GIFT CARD BOT"
    BOT_VERSION = "5.0.0"

config = Config()

# ===========================================================================
# ENUMS AND CONSTANTS
# ===========================================================================

class UserRole(Enum):
    USER = "user"
    ADMIN = "admin"
    BANNED = "banned"

class TransactionType(Enum):
    CREDIT = "credit"
    DEBIT = "debit"
    BONUS = "bonus"

class PaymentMethod(Enum):
    UPI = "upi"
    BANK = "bank"
    CRYPTO = "crypto"

# Conversation States
(
    STATE_AMOUNT,
    STATE_SCREENSHOT,
    STATE_UTR,
    STATE_EMAIL,
    STATE_SUPPORT,
    STATE_FEEDBACK
) = range(6)

# ===========================================================================
# GIFT CARD DATA
# ===========================================================================

GIFT_CARDS = {
    "amazon": {
        "name": "AMAZON",
        "emoji": "🟦",
        "full_emoji": "🟦🛒",
        "description": "Amazon.in Gift Card - Shop everything",
        "popular": True
    },
    "playstore": {
        "name": "PLAY STORE",
        "emoji": "🟩",
        "full_emoji": "🟩🎮",
        "description": "Google Play - Apps & Games",
        "popular": True
    },
    "bookmyshow": {
        "name": "BOOKMYSHOW",
        "emoji": "🎟️",
        "full_emoji": "🎟️🎬",
        "description": "Movie Tickets & Events",
        "popular": True
    },
    "myntra": {
        "name": "MYNTRA",
        "emoji": "🛍️",
        "full_emoji": "🛍️👗",
        "description": "Fashion & Lifestyle",
        "popular": True
    },
    "flipkart": {
        "name": "FLIPKART",
        "emoji": "📦",
        "full_emoji": "📦🛒",
        "description": "Online Shopping",
        "popular": True
    },
    "zomato": {
        "name": "ZOMATO",
        "emoji": "🍕",
        "full_emoji": "🍕🍔",
        "description": "Food Delivery",
        "popular": True
    },
    "bigbasket": {
        "name": "BIG BASKET",
        "emoji": "🛒",
        "full_emoji": "🛒🥬",
        "description": "Grocery Delivery",
        "popular": True
    },
    "netflix": {
        "name": "NETFLIX",
        "emoji": "🎬",
        "full_emoji": "🎬📺",
        "description": "Streaming Service",
        "popular": False
    },
    "spotify": {
        "name": "SPOTIFY",
        "emoji": "🎵",
        "full_emoji": "🎵🎧",
        "description": "Music Streaming",
        "popular": False
    },
    "dream11": {
        "name": "DREAM11",
        "emoji": "🏏",
        "full_emoji": "🏏🎯",
        "description": "Fantasy Sports",
        "popular": False
    }
}

# Price configuration
PRICES = {
    500: 100,
    1000: 200,
    2000: 400,
    5000: 1000
}

AVAILABLE_DENOMINATIONS = [500, 1000, 2000, 5000]

# ===========================================================================
# SETUP LOGGING
# ===========================================================================

def setup_logging():
    """Setup logging system"""
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "bot.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ===========================================================================
# DATABASE MANAGER - THREAD SAFE VERSION
# ===========================================================================

class DatabaseManager:
    """Thread-safe database manager"""
    
    def __init__(self):
        self.db_path = config.DATABASE_PATH
        self._init_database()
        logger.info("✅ Database Manager initialized")
    
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
            role TEXT DEFAULT 'user',
            status TEXT DEFAULT 'active',
            joined_date TIMESTAMP,
            last_active TIMESTAMP
        )''')
        
        # Transactions table
        c.execute('''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            transaction_id TEXT UNIQUE,
            amount INTEGER,
            type TEXT,
            status TEXT,
            payment_method TEXT,
            utr TEXT,
            fee INTEGER DEFAULT 0,
            final_amount INTEGER,
            description TEXT,
            timestamp TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
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
            status TEXT DEFAULT 'completed',
            timestamp TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )''')
        
        # Verifications table
        c.execute('''CREATE TABLE IF NOT EXISTS verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            fee INTEGER,
            final INTEGER,
            utr TEXT,
            screenshot TEXT,
            status TEXT DEFAULT 'pending',
            timestamp TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )''')
        
        # Support tickets table
        c.execute('''CREATE TABLE IF NOT EXISTS support (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            ticket_id TEXT UNIQUE,
            message TEXT,
            status TEXT DEFAULT 'open',
            timestamp TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )''')
        
        # Referrals table
        c.execute('''CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_id INTEGER UNIQUE,
            bonus_amount INTEGER DEFAULT 10,
            status TEXT DEFAULT 'pending',
            timestamp TIMESTAMP,
            FOREIGN KEY (referrer_id) REFERENCES users(user_id),
            FOREIGN KEY (referred_id) REFERENCES users(user_id)
        )''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Database tables initialized")
    
    def _get_connection(self):
        """Get a new database connection"""
        return sqlite3.connect(self.db_path, check_same_thread=False)
    
    # ===== USER METHODS =====
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        conn = self._get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        
        if row:
            columns = [description[0] for description in c.description]
            return dict(zip(columns, row))
        return None
    
    def create_user(self, user_id: int, username: str = None, first_name: str = None) -> Dict:
        """Create new user"""
        conn = self._get_connection()
        c = conn.cursor()
        
        now = datetime.now().isoformat()
        c.execute('''INSERT OR IGNORE INTO users 
            (user_id, username, first_name, joined_date, last_active)
            VALUES (?, ?, ?, ?, ?)''',
            (user_id, username, first_name, now, now))
        
        conn.commit()
        conn.close()
        return self.get_user(user_id)
    
    def update_last_active(self, user_id: int):
        """Update user's last active timestamp"""
        conn = self._get_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET last_active = ? WHERE user_id = ?",
                 (datetime.now().isoformat(), user_id))
        conn.commit()
        conn.close()
    
    def get_balance(self, user_id: int) -> int:
        """Get user balance"""
        conn = self._get_connection()
        c = conn.cursor()
        c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else 0
    
    def update_balance(self, user_id: int, amount: int, transaction_type: str, **kwargs) -> bool:
        """Update user balance and record transaction"""
        conn = self._get_connection()
        c = conn.cursor()
        
        try:
            # Get current balance
            c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            result = c.fetchone()
            if not result:
                return False
            
            current_balance = result[0]
            new_balance = current_balance + amount
            
            if new_balance < 0:
                return False
            
            # Update balance
            c.execute("UPDATE users SET balance = ?, last_active = ? WHERE user_id = ?",
                     (new_balance, datetime.now().isoformat(), user_id))
            
            # Generate transaction ID
            tx_id = f"TXN{datetime.now().strftime('%y%m%d%H%M%S')}{random.randint(1000, 9999)}"
            
            # Record transaction
            c.execute('''INSERT INTO transactions 
                (user_id, transaction_id, amount, type, status, payment_method, utr, fee, final_amount, description, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (user_id, tx_id, abs(amount), transaction_type, 'completed',
                 kwargs.get('payment_method'), kwargs.get('utr'), kwargs.get('fee', 0),
                 kwargs.get('final_amount', amount), kwargs.get('description', ''),
                 datetime.now().isoformat()))
            
            # Update totals
            if amount > 0:
                c.execute("UPDATE users SET total_recharged = total_recharged + ? WHERE user_id = ?",
                         (amount, user_id))
            else:
                c.execute("UPDATE users SET total_spent = total_spent + ? WHERE user_id = ?",
                         (abs(amount), user_id))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"❌ Balance update error: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    # ===== VERIFICATION METHODS =====
    
    def create_verification(self, user_id: int, amount: int, fee: int, final: int, utr: str, screenshot: str) -> int:
        """Create payment verification"""
        conn = self._get_connection()
        c = conn.cursor()
        
        c.execute('''INSERT INTO verifications 
            (user_id, amount, fee, final, utr, screenshot, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (user_id, amount, fee, final, utr, screenshot, datetime.now().isoformat()))
        
        verification_id = c.lastrowid
        conn.commit()
        conn.close()
        return verification_id
    
    def get_pending_verifications(self) -> List[Dict]:
        """Get all pending verifications"""
        conn = self._get_connection()
        c = conn.cursor()
        c.execute('''SELECT * FROM verifications 
            WHERE status = 'pending' 
            ORDER BY timestamp DESC''')
        rows = c.fetchall()
        
        result = []
        if rows:
            columns = [description[0] for description in c.description]
            for row in rows:
                result.append(dict(zip(columns, row)))
        
        conn.close()
        return result
    
    def approve_verification(self, verification_id: int) -> bool:
        """Approve payment verification"""
        conn = self._get_connection()
        c = conn.cursor()
        
        try:
            # Get verification
            c.execute("SELECT * FROM verifications WHERE id = ?", (verification_id,))
            row = c.fetchone()
            if not row:
                return False
            
            columns = [description[0] for description in c.description]
            verification = dict(zip(columns, row))
            
            # Update verification status
            c.execute("UPDATE verifications SET status = 'approved' WHERE id = ?", (verification_id,))
            
            # Update user balance
            self.update_balance(
                verification['user_id'],
                verification['final'],
                'credit',
                payment_method='UPI',
                utr=verification['utr'],
                fee=verification['fee'],
                final_amount=verification['final'],
                description='UPI Recharge'
            )
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"❌ Approval error: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def reject_verification(self, verification_id: int) -> bool:
        """Reject payment verification"""
        conn = self._get_connection()
        c = conn.cursor()
        
        try:
            c.execute("UPDATE verifications SET status = 'rejected' WHERE id = ?", (verification_id,))
            conn.commit()
            return c.rowcount > 0
        except Exception as e:
            logger.error(f"❌ Rejection error: {e}")
            return False
        finally:
            conn.close()
    
    # ===== PURCHASE METHODS =====
    
    def create_purchase(self, user_id: int, card_type: str, value: int, price: int, email: str) -> str:
        """Create purchase record"""
        conn = self._get_connection()
        c = conn.cursor()
        
        order_id = f"GC{datetime.now().strftime('%y%m%d%H%M%S')}{random.randint(1000, 9999)}"
        
        c.execute('''INSERT INTO purchases 
            (user_id, order_id, card_type, card_value, price, email, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (user_id, order_id, card_type, value, price, email, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        return order_id
    
    def get_purchases(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get user purchases"""
        conn = self._get_connection()
        c = conn.cursor()
        c.execute('''SELECT * FROM purchases 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?''', (user_id, limit))
        rows = c.fetchall()
        
        result = []
        if rows:
            columns = [description[0] for description in c.description]
            for row in rows:
                result.append(dict(zip(columns, row)))
        
        conn.close()
        return result
    
    # ===== SUPPORT METHODS =====
    
    def create_support_ticket(self, user_id: int, message: str) -> str:
        """Create support ticket"""
        conn = self._get_connection()
        c = conn.cursor()
        
        ticket_id = f"TKT{datetime.now().strftime('%y%m%d%H%M%S')}{random.randint(1000, 9999)}"
        
        c.execute('''INSERT INTO support 
            (user_id, ticket_id, message, timestamp)
            VALUES (?, ?, ?, ?)''',
            (user_id, ticket_id, message, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        return ticket_id
    
    # ===== REFERRAL METHODS =====
    
    def process_referral(self, referrer_id: int, referred_id: int) -> bool:
        """Process referral bonus"""
        conn = self._get_connection()
        c = conn.cursor()
        
        try:
            # Check if already referred
            c.execute("SELECT * FROM referrals WHERE referred_id = ?", (referred_id,))
            if c.fetchone():
                return False
            
            # Create referral record
            c.execute('''INSERT INTO referrals 
                (referrer_id, referred_id, timestamp)
                VALUES (?, ?, ?)''',
                (referrer_id, referred_id, datetime.now().isoformat()))
            
            # Give bonus to referrer
            self.update_balance(
                referrer_id,
                10,
                'bonus',
                description=f'Referral bonus for user {referred_id}'
            )
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"❌ Referral error: {e}")
            return False
        finally:
            conn.close()
    
    # ===== STATISTICS METHODS =====
    
    def get_statistics(self) -> Dict:
        """Get bot statistics"""
        conn = self._get_connection()
        c = conn.cursor()
        stats = {}
        
        # Total users
        c.execute("SELECT COUNT(*) FROM users")
        stats['total_users'] = c.fetchone()[0]
        
        # Active today
        today = datetime.now().date().isoformat()
        c.execute("SELECT COUNT(*) FROM users WHERE date(last_active) = ?", (today,))
        stats['active_today'] = c.fetchone()[0]
        
        # Total revenue
        c.execute("SELECT SUM(amount) FROM transactions WHERE type = 'credit'")
        stats['total_revenue'] = c.fetchone()[0] or 0
        
        # Total spent
        c.execute("SELECT SUM(price) FROM purchases")
        stats['total_spent'] = c.fetchone()[0] or 0
        
        # Pending verifications
        c.execute("SELECT COUNT(*) FROM verifications WHERE status = 'pending'")
        stats['pending'] = c.fetchone()[0]
        
        # Open tickets
        c.execute("SELECT COUNT(*) FROM support WHERE status = 'open'")
        stats['open_tickets'] = c.fetchone()[0]
        
        conn.close()
        return stats

# ===========================================================================
# DATABASE INSTANCE
# ===========================================================================

db = DatabaseManager()

# ===========================================================================
# HELPER FUNCTIONS
# ===========================================================================

def format_currency(amount: int) -> str:
    """Format amount with ₹ symbol"""
    return f"₹{amount:,}"

def validate_email(email: str) -> bool:
    """Validate email address"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_utr(utr: str) -> bool:
    """Validate UTR number"""
    return 12 <= len(utr) <= 22 and utr.isalnum()

def calculate_fee(amount: int) -> Tuple[int, int]:
    """Calculate fee and final amount"""
    if amount < config.FEE_THRESHOLD:
        fee = int(amount * config.FEE_PERCENT / 100)
        return fee, amount - fee
    return 0, amount

# ===========================================================================
# CHECK MEMBERSHIP
# ===========================================================================

async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is member of main channel"""
    try:
        member = await context.bot.get_chat_member(
            chat_id=config.MAIN_CHANNEL,
            user_id=user_id
        )
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"❌ Membership check error: {e}")
        return False

# ===========================================================================
# DECORATORS
# ===========================================================================

def admin_only(func):
    """Decorator to restrict to admin only"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if user.id != config.ADMIN_ID:
            await update.message.reply_text(
                "❌ *Unauthorized*\n\nThis command is for admins only.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def log_action(func):
    """Decorator to log user actions"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        logger.info(f"👤 User {user.id} ({user.first_name}) performed: {func.__name__}")
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            logger.error(f"❌ Error in {func.__name__}: {e}")
            raise
    return wrapper

# ===========================================================================
# START COMMAND
# ===========================================================================

@log_action
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    # Create user if not exists
    db_user = db.get_user(user.id)
    if not db_user:
        db.create_user(user.id, user.username, user.first_name)
        logger.info(f"✅ New user registered: {user.id}")
    
    db.update_last_active(user.id)
    
    # Check membership
    is_member = await check_membership(user.id, context)
    
    if not is_member:
        welcome_text = (
            f"✨ *WELCOME TO {config.BOT_NAME}* ✨\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👋 *Hello {user.first_name}!*\n\n"
            f"🎁 *Get Gift Cards at 80% OFF!*\n"
            f"• Amazon • Flipkart • Play Store\n"
            f"• Myntra • Zomato • & More!\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔒 *VERIFICATION REQUIRED*\n"
            f"To ensure safe transactions, you must join our channel.\n\n"
            f"👇 *Click below to join and verify*"
        )
        
        keyboard = [[
            InlineKeyboardButton("📢 JOIN CHANNEL", url="https://t.me/gift_card_main"),
            InlineKeyboardButton("✅ VERIFY", callback_data="verify")
        ]]
        
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Show main menu
    balance = db.get_balance(user.id)
    
    menu_text = (
        f"🏠 *MAIN MENU*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *User:* {user.first_name}\n"
        f"💰 *Balance:* {format_currency(balance)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"*Please select an option:* ⬇️"
    )
    
    keyboard = [
        [InlineKeyboardButton("🎁 GIFT CARDS", callback_data="giftcard")],
        [InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")],
        [InlineKeyboardButton("💳 MY WALLET", callback_data="wallet")],
        [InlineKeyboardButton("🆘 SUPPORT", callback_data="support")],
        [InlineKeyboardButton("📊 PROOFS", callback_data="proofs")],
        [InlineKeyboardButton("🎁 REFERRAL", callback_data="referral")]
    ]
    
    await update.message.reply_text(
        menu_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===========================================================================
# BUTTON HANDLER
# ===========================================================================

@log_action
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all button clicks"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data
    
    logger.info(f"🔘 Button: {data} by {user.first_name}")
    
    db.update_last_active(user.id)
    
    # ===== VERIFY BUTTON =====
    if data == "verify":
        is_member = await check_membership(user.id, context)
        
        if is_member:
            balance = db.get_balance(user.id)
            
            text = (
                f"✅ *VERIFICATION SUCCESSFUL!*\n\n"
                f"👋 *Welcome {user.first_name}!*\n"
                f"💰 *Balance:* {format_currency(balance)}\n\n"
                f"*You now have full access!*\n\n"
                f"⬇️ *Choose an option:*"
            )
            
            keyboard = [
                [InlineKeyboardButton("🎁 GIFT CARDS", callback_data="giftcard")],
                [InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")],
                [InlineKeyboardButton("💳 MY WALLET", callback_data="wallet")],
                [InlineKeyboardButton("🆘 SUPPORT", callback_data="support")]
            ]
            
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            keyboard = [[
                InlineKeyboardButton("📢 JOIN CHANNEL", url="https://t.me/gift_card_main"),
                InlineKeyboardButton("🔄 VERIFY AGAIN", callback_data="verify")
            ]]
            
            await query.edit_message_text(
                "❌ *Not a member!*\n\nJoin @gift_card_main first",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return
    
    # Check membership for other actions
    if not await check_membership(user.id, context):
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
        
        text = (
            f"🏠 *MAIN MENU*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *User:* {user.first_name}\n"
            f"💰 *Balance:* {format_currency(balance)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"*Select an option:*"
        )
        
        keyboard = [
            [InlineKeyboardButton("🎁 GIFT CARDS", callback_data="giftcard")],
            [InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")],
            [InlineKeyboardButton("💳 MY WALLET", callback_data="wallet")],
            [InlineKeyboardButton("🆘 SUPPORT", callback_data="support")],
            [InlineKeyboardButton("📊 PROOFS", callback_data="proofs")],
            [InlineKeyboardButton("🎁 REFERRAL", callback_data="referral")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== GIFT CARD MENU =====
    elif data == "giftcard":
        keyboard = []
        for card_id, card in GIFT_CARDS.items():
            if card.get('popular', False):
                keyboard.append([InlineKeyboardButton(
                    f"{card['full_emoji']} {card['name']} ⭐", 
                    callback_data=f"card_{card_id}"
                )])
        
        for card_id, card in GIFT_CARDS.items():
            if not card.get('popular', False):
                keyboard.append([InlineKeyboardButton(
                    f"{card['full_emoji']} {card['name']}", 
                    callback_data=f"card_{card_id}"
                )])
        
        keyboard.append([InlineKeyboardButton("🔙 BACK", callback_data="main_menu")])
        
        text = (
            f"🎁 *GIFT CARDS*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"*Choose from 10+ brands:*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💳 *Instant Email Delivery*\n"
            f"✅ *100% Working Codes*\n\n"
            f"*Select a brand:* ⬇️"
        )
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== CARD DETAILS =====
    elif data.startswith("card_"):
        card_id = data.replace("card_", "")
        card = GIFT_CARDS.get(card_id)
        
        if not card:
            return
        
        keyboard = []
        for denom in AVAILABLE_DENOMINATIONS:
            if denom in PRICES:
                price = PRICES[denom]
                keyboard.append([InlineKeyboardButton(
                    f"₹{denom} → ₹{price}", 
                    callback_data=f"buy_{card_id}_{denom}"
                )])
        
        keyboard.append([InlineKeyboardButton("🔙 BACK", callback_data="giftcard")])
        
        text = (
            f"{card['full_emoji']} *{card['name']}*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 *{card['description']}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"*Available Denominations:*\n\n"
            f"*Select amount:* ⬇️"
        )
        
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
        
        card_id = parts[1]
        try:
            value = int(parts[2])
        except:
            return
        
        card = GIFT_CARDS.get(card_id)
        if not card or value not in PRICES:
            return
        
        price = PRICES[value]
        balance = db.get_balance(user.id)
        
        if balance < price:
            keyboard = [[InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")]]
            await query.edit_message_text(
                f"❌ *Insufficient Balance*\n\n"
                f"Need: {format_currency(price)}\n"
                f"You have: {format_currency(balance)}",
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
            f"✅ *Balance Sufficient*\n\n"
            f"*{card['full_emoji']} {card['name']} ₹{value}*\n"
            f"*Price:* {format_currency(price)}\n\n"
            f"📧 *Enter your email address:*",
            parse_mode=ParseMode.MARKDOWN
        )
        
        return STATE_EMAIL
    
    # ===== TOP UP MENU =====
    elif data == "topup":
        keyboard = [
            [InlineKeyboardButton("📱 UPI", callback_data="upi")],
            [InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]
        ]
        
        text = (
            f"💰 *ADD MONEY*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"*Select payment method:*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📱 *UPI* - Instant & Easy\n"
            f"• Google Pay • PhonePe • Paytm\n\n"
            f"*Choose method:* ⬇️"
        )
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== UPI =====
    elif data == "upi":
        text = (
            f"💳 *UPI RECHARGE*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"*Enter amount to add:*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 *Min:* {format_currency(config.MIN_RECHARGE)}\n"
            f"💰 *Max:* {format_currency(config.MAX_RECHARGE)}\n\n"
            f"📌 *Fee:* {config.FEE_PERCENT}% below ₹{config.FEE_THRESHOLD}\n"
            f"   Pay ₹100 → Get ₹80\n"
            f"   Pay ₹200 → Get ₹200\n\n"
            f"*Enter amount:*"
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
            f"💳 *YOUR WALLET*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 *Balance:* {format_currency(balance)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"*Quick Actions:* ⬇️"
        )
        
        keyboard = [
            [InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")],
            [InlineKeyboardButton("🎁 BUY CARDS", callback_data="giftcard")],
            [InlineKeyboardButton("📜 HISTORY", callback_data="history")],
            [InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== HISTORY =====
    elif data == "history":
        purchases = db.get_purchases(user.id, 5)
        
        text = f"📜 *PURCHASE HISTORY*\n\n"
        text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        if not purchases:
            text += "📭 No purchases yet\n"
        else:
            for p in purchases:
                text += (
                    f"• {p['card_type']} ₹{p['card_value']}\n"
                    f"  🆔 `{p['order_id']}`\n"
                    f"  📧 {p['email']}\n\n"
                )
        
        text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="wallet")]]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== SUPPORT =====
    elif data == "support":
        text = (
            f"🆘 *SUPPORT*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"*Type your issue below:*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"We'll respond within 24 hours.\n\n"
            f"*Enter your message:*"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return STATE_SUPPORT
    
    # ===== PROOFS =====
    elif data == "proofs":
        text = (
            f"📊 *LIVE PROOFS*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ *See real purchases:*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👉 {config.PROOF_CHANNEL}\n\n"
            f"*Click below to join*"
        )
        
        keyboard = [
            [InlineKeyboardButton("📢 VIEW CHANNEL", url="https://t.me/gift_card_log")],
            [InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== REFERRAL =====
    elif data == "referral":
        bot_username = (await context.bot.get_me()).username
        referral_link = f"https://t.me/{bot_username}?start=ref_{user.id}"
        
        text = (
            f"🎁 *REFERRAL PROGRAM*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"*Earn ₹10 per friend!*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔗 *Your Link:*\n"
            f"`{referral_link}`\n\n"
            f"📌 *How it works:*\n"
            f"1️⃣ Share your link\n"
            f"2️⃣ Friend joins\n"
            f"3️⃣ You get ₹10\n\n"
            f"*Start sharing now!* 🚀"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ===========================================================================
# AMOUNT HANDLER
# ===========================================================================

@log_action
async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle amount input"""
    text = update.message.text.strip()
    
    try:
        amount = int(text)
    except ValueError:
        await update.message.reply_text(
            "❌ *Invalid amount*\n\nPlease enter a valid number.",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_AMOUNT
    
    if amount < config.MIN_RECHARGE or amount > config.MAX_RECHARGE:
        await update.message.reply_text(
            f"❌ *Invalid amount*\n\nAmount must be between "
            f"{format_currency(config.MIN_RECHARGE)} and {format_currency(config.MAX_RECHARGE)}.",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_AMOUNT
    
    fee, final = calculate_fee(amount)
    
    context.user_data['topup'] = {
        'amount': amount,
        'fee': fee,
        'final': final
    }
    
    keyboard = [
        [InlineKeyboardButton("✅ I PAID", callback_data="paid")],
        [InlineKeyboardButton("❌ CANCEL", callback_data="main_menu")]
    ]
    
    # Send QR code if exists
    if os.path.exists(config.QR_CODE_PATH):
        with open(config.QR_CODE_PATH, 'rb') as qr:
            await update.message.reply_photo(
                photo=qr,
                caption=(
                    f"💳 *PAYMENT DETAILS*\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"*UPI ID:* `{config.UPI_ID}`\n"
                    f"*Amount:* {format_currency(amount)}\n"
                    f"*Fee:* {format_currency(fee) if fee > 0 else 'No fee'}\n"
                    f"*You get:* {format_currency(final)}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"📱 *After payment, click I PAID*"
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    else:
        await update.message.reply_text(
            f"💳 *PAYMENT DETAILS*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"*UPI ID:* `{config.UPI_ID}`\n"
            f"*Amount:* {format_currency(amount)}\n"
            f"*Fee:* {format_currency(fee) if fee > 0 else 'No fee'}\n"
            f"*You get:* {format_currency(final)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📱 *After payment, click I PAID*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    return ConversationHandler.END

# ===========================================================================
# PAID HANDLER
# ===========================================================================

@log_action
async def handle_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle paid button click"""
    query = update.callback_query
    await query.answer()
    
    if 'topup' not in context.user_data:
        await query.edit_message_text(
            "❌ *Session expired*\n\nPlease start over.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]]
    
    await query.edit_message_text(
        f"📤 *SEND PROOF*\n\n"
        f"1️⃣ Send SCREENSHOT\n"
        f"2️⃣ Send UTR number\n\n"
        f"Example UTR: `SBIN1234567890`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return STATE_SCREENSHOT

# ===========================================================================
# SCREENSHOT HANDLER
# ===========================================================================

@log_action
async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle screenshot"""
    if not update.message.photo:
        await update.message.reply_text(
            "❌ *Please send a photo*",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_SCREENSHOT
    
    context.user_data['screenshot'] = update.message.photo[-1].file_id
    
    await update.message.reply_text(
        "✅ *Screenshot received*\n\nNow send UTR number:",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return STATE_UTR

# ===========================================================================
# UTR HANDLER
# ===========================================================================

@log_action
async def handle_utr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle UTR input"""
    user = update.effective_user
    utr = update.message.text.strip()
    
    if not validate_utr(utr):
        await update.message.reply_text(
            "❌ *Invalid UTR*\n\nUTR should be 12-22 characters.",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_UTR
    
    if 'topup' not in context.user_data or 'screenshot' not in context.user_data:
        await update.message.reply_text(
            "❌ *Session expired*\n\nPlease start over.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    data = context.user_data['topup']
    screenshot = context.user_data['screenshot']
    
    # Create verification
    vid = db.create_verification(
        user.id, data['amount'], data['fee'], data['final'], utr, screenshot
    )
    
    # Notify admin
    caption = (
        f"🔔 *NEW PAYMENT*\n\n"
        f"👤 *User:* {user.first_name}\n"
        f"🆔 *ID:* `{user.id}`\n"
        f"💰 *Amount:* {format_currency(data['amount'])}\n"
        f"🎁 *Credit:* {format_currency(data['final'])}\n"
        f"🔢 *UTR:* `{utr}`"
    )
    
    keyboard = [[
        InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{vid}"),
        InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{vid}")
    ]]
    
    await context.bot.send_photo(
        chat_id=config.ADMIN_CHANNEL_ID,
        photo=screenshot,
        caption=caption,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    context.user_data.clear()
    
    keyboard = [[InlineKeyboardButton("🏠 MAIN MENU", callback_data="main_menu")]]
    
    await update.message.reply_text(
        "✅ *VERIFICATION SUBMITTED!*\n\nWe'll notify you soon.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ConversationHandler.END

# ===========================================================================
# EMAIL HANDLER
# ===========================================================================

@log_action
async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle email input"""
    user = update.effective_user
    email = update.message.text.strip()
    
    if not validate_email(email):
        await update.message.reply_text(
            "❌ *Invalid email*\n\nPlease enter a valid email.",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_EMAIL
    
    if 'purchase' not in context.user_data:
        await update.message.reply_text(
            "❌ *Session expired*\n\nPlease start over.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    purchase = context.user_data['purchase']
    balance = db.get_balance(user.id)
    
    if balance < purchase['price']:
        await update.message.reply_text(
            "❌ *Insufficient balance*",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    # Process purchase
    db.update_balance(user.id, -purchase['price'], 'debit')
    order_id = db.create_purchase(
        user.id, purchase['card'], purchase['value'], purchase['price'], email
    )
    
    context.user_data.clear()
    
    keyboard = [[InlineKeyboardButton("🏠 MAIN MENU", callback_data="main_menu")]]
    
    await update.message.reply_text(
        f"✅ *PURCHASE SUCCESSFUL!*\n\n"
        f"*{purchase['emoji']} {purchase['card']} ₹{purchase['value']}*\n"
        f"*Order ID:* `{order_id}`\n\n"
        f"*Sent to:* `{email}`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ConversationHandler.END

# ===========================================================================
# SUPPORT HANDLER
# ===========================================================================

@log_action
async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle support message"""
    user = update.effective_user
    message = update.message.text.strip()
    
    if len(message) < 10:
        await update.message.reply_text(
            "❌ *Message too short*\n\nPlease describe your issue.",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_SUPPORT
    
    ticket_id = db.create_support_ticket(user.id, message)
    
    # Notify admin
    await context.bot.send_message(
        chat_id=config.ADMIN_ID,
        text=f"🆘 *SUPPORT*\n\n👤 {user.first_name}\n💬 {message}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    keyboard = [[InlineKeyboardButton("🏠 MAIN MENU", callback_data="main_menu")]]
    
    await update.message.reply_text(
        f"✅ *SUPPORT SENT!*\n\nTicket ID: `{ticket_id}`\n\nWe'll contact you soon.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ConversationHandler.END

# ===========================================================================
# ADMIN CALLBACK HANDLER
# ===========================================================================

@admin_only
async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    parts = data.split("_")
    
    if len(parts) < 2:
        return
    
    action = parts[0]
    try:
        vid = int(parts[1])
    except:
        return
    
    if action == "approve":
        if db.approve_verification(vid):
            await query.edit_message_caption("✅ APPROVED")
            
            # Get verification for notification
            conn = sqlite3.connect(config.DATABASE_PATH)
            c = conn.cursor()
            c.execute("SELECT user_id, final FROM verifications WHERE id = ?", (vid,))
            row = c.fetchone()
            conn.close()
            
            if row:
                await context.bot.send_message(
                    chat_id=row[0],
                    text=f"✅ *PAYMENT APPROVED!*\n\n{format_currency(row[1])} added to your balance.",
                    parse_mode=ParseMode.MARKDOWN
                )
    
    elif action == "reject":
        if db.reject_verification(vid):
            await query.edit_message_caption("❌ REJECTED")
            
            # Get verification for notification
            conn = sqlite3.connect(config.DATABASE_PATH)
            c = conn.cursor()
            c.execute("SELECT user_id FROM verifications WHERE id = ?", (vid,))
            row = c.fetchone()
            conn.close()
            
            if row:
                await context.bot.send_message(
                    chat_id=row[0],
                    text="❌ *PAYMENT REJECTED*\n\nPlease try again.",
                    parse_mode=ParseMode.MARKDOWN
                )

# ===========================================================================
# ADMIN COMMANDS
# ===========================================================================

@admin_only
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin stats command"""
    stats = db.get_statistics()
    
    text = (
        f"📊 *BOT STATISTICS*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 *Users:* {stats['total_users']}\n"
        f"📱 *Active Today:* {stats['active_today']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 *Revenue:* {format_currency(stats['total_revenue'])}\n"
        f"💳 *Spent:* {format_currency(stats['total_spent'])}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ *Pending:* {stats['pending']}\n"
        f"🎫 *Tickets:* {stats['open_tickets']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@admin_only
async def admin_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin pending verifications"""
    pending = db.get_pending_verifications()
    
    if not pending:
        await update.message.reply_text(
            "✅ *No pending verifications*",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text = f"⏳ *PENDING VERIFICATIONS ({len(pending)})*\n\n"
    
    for p in pending[:5]:
        text += (
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 *ID:* `{p['id']}`\n"
            f"👤 *User:* `{p['user_id']}`\n"
            f"💰 *Amount:* {format_currency(p['amount'])}\n"
            f"🎁 *Credit:* {format_currency(p['final'])}\n"
            f"🔢 *UTR:* `{p['utr']}`\n"
        )
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@admin_only
async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin broadcast command"""
    if not context.args:
        await update.message.reply_text(
            "📢 *BROADCAST*\n\nUsage: `/broadcast Your message`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    message = " ".join(context.args)
    
    # Get all users
    conn = sqlite3.connect(config.DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    
    sent = 0
    failed = 0
    
    status = await update.message.reply_text(
        f"📢 *Broadcasting to {len(users)} users...*",
        parse_mode=ParseMode.MARKDOWN
    )
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user[0],
                text=f"📢 *BROADCAST*\n\n{message}",
                parse_mode=ParseMode.MARKDOWN
            )
            sent += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
        
        if (sent + failed) % 10 == 0:
            await status.edit_text(
                f"📢 *Broadcasting...*\n\n✅ Sent: {sent}\n❌ Failed: {failed}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    await status.edit_text(
        f"📢 *Broadcast Complete*\n\n✅ Sent: {sent}\n❌ Failed: {failed}",
        parse_mode=ParseMode.MARKDOWN
    )

# ===========================================================================
# AUTO PROOFS JOB
# ===========================================================================

async def auto_proofs(context: ContextTypes.DEFAULT_TYPE):
    """Send random proofs to channel"""
    try:
        names = [
            "👑 Raj", "💫 Arjun", "🌟 Kavya", "⚡ Veer", "🔥 Aryan",
            "💎 Neha", "🎯 Karan", "🚀 Riya", "⭐ Amit", "💥 Priya"
        ]
        
        cards = [
            "🟦 AMAZON", "🟩 PLAY STORE", "🎟️ BOOKMYSHOW", 
            "🛍️ MYNTRA", "📦 FLIPKART", "🍕 ZOMATO"
        ]
        
        amounts = [500, 1000, 2000, 5000]
        
        name = random.choice(names)
        card = random.choice(cards)
        amount = random.choice(amounts)
        
        message = (
            f"⚡ *NEW PURCHASE*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *{name}*\n"
            f"🎁 {card}\n"
            f"💰 ₹{amount}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📧 *Email Delivery*\n"
            f"✅ *Instant*"
        )
        
        await context.bot.send_message(
            chat_id=config.PROOF_CHANNEL,
            text=message,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"❌ Auto proof error: {e}")

# ===========================================================================
# CANCEL HANDLER
# ===========================================================================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current operation"""
    context.user_data.clear()
    
    keyboard = [[InlineKeyboardButton("🏠 MAIN MENU", callback_data="main_menu")]]
    
    await update.message.reply_text(
        "❌ *Cancelled*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ConversationHandler.END

# ===========================================================================
# ERROR HANDLER
# ===========================================================================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"❌ Error: {context.error}")

# ===========================================================================
# POST INIT
# ===========================================================================

async def post_init(application: Application):
    """Setup after bot initialization"""
    commands = [
        BotCommand("start", "🚀 Start the bot"),
        BotCommand("stats", "📊 Bot stats (admin)"),
        BotCommand("pending", "⏳ Pending (admin)"),
        BotCommand("broadcast", "📢 Broadcast (admin)")
    ]
    
    await application.bot.set_my_commands(commands)
    logger.info(f"✅ {config.BOT_NAME} v{config.BOT_VERSION} initialized")

# ===========================================================================
# MAIN FUNCTION
# ===========================================================================

def main():
    """Main function"""
    try:
        # Create application
        app = Application.builder()\
            .token(config.BOT_TOKEN)\
            .post_init(post_init)\
            .build()
        
        # ===== COMMAND HANDLERS =====
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("cancel", cancel))
        app.add_handler(CommandHandler("stats", admin_stats))
        app.add_handler(CommandHandler("pending", admin_pending))
        app.add_handler(CommandHandler("broadcast", admin_broadcast))
        
        # ===== BUTTON HANDLER =====
        app.add_handler(CallbackQueryHandler(button_handler))
        
        # ===== ADMIN CALLBACK HANDLER =====
        app.add_handler(CallbackQueryHandler(admin_handler, pattern="^(approve_|reject_)"))
        
        # ===== PAID BUTTON HANDLER =====
        app.add_handler(CallbackQueryHandler(handle_paid, pattern="^paid$"))
        
        # ===== AMOUNT CONVERSATION =====
        amount_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(button_handler, pattern="^upi$")],
            states={STATE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)]},
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        app.add_handler(amount_conv)
        
        # ===== PAYMENT CONVERSATION =====
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
        
        # ===== EMAIL CONVERSATION =====
        email_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(button_handler, pattern="^buy_")],
            states={STATE_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email)]},
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        app.add_handler(email_conv)
        
        # ===== SUPPORT CONVERSATION =====
        support_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(button_handler, pattern="^support$")],
            states={STATE_SUPPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_support)]},
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        app.add_handler(support_conv)
        
        # ===== ERROR HANDLER =====
        app.add_error_handler(error_handler)
        
        # ===== AUTO PROOFS =====
        if app.job_queue:
            app.job_queue.run_repeating(auto_proofs, interval=45, first=10)
        
        # ===== START BOT =====
        logger.info(f"🚀 Starting {config.BOT_NAME}...")
        
        print("\n" + "="*60)
        print(f"      {config.BOT_NAME} v{config.BOT_VERSION}")
        print("="*60)
        print(f"📢 Main Channel: {config.MAIN_CHANNEL}")
        print(f"📊 Proof Channel: {config.PROOF_CHANNEL}")
        print(f"👑 Admin ID: {config.ADMIN_ID}")
        print(f"💳 UPI ID: {config.UPI_ID}")
        print("="*60)
        print(f"✅ Bot is running...")
        print("="*60 + "\n")
        
        app.run_polling()
        
    except Exception as e:
        logger.critical(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
    
