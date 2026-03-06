#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GIFT CARD & RECHARGE BOT
A complete Telegram bot for selling gift cards and managing recharges
Version: 2.0.0
Author: Your Name
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
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from functools import wraps
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, 
    filters, ContextTypes, ConversationHandler, JobQueue
)
from telegram.constants import ParseMode
from telegram.error import TelegramError, RetryAfter, TimedOut, NetworkError

# ==================== CONFIGURATION & CONSTANTS ====================

# Bot Configuration
BOT_TOKEN = "8646034766:AAGXkMglnsc72ew1aGcFmWnZziwb8nfS2S8"
ADMIN_ID = 6185091342
MAIN_CHANNEL = "@gift_card_main"
PROOF_CHANNEL = "@gift_card_log"
ADMIN_CHANNEL_ID = -1003607749028
UPI_ID = "helobiy41@ptyes"

# File paths
QR_CODE_PATH = "qr.jpg"
DATABASE_PATH = "bot_database.db"
LOG_FILE = "bot.log"
CONFIG_FILE = "config.json"

# Gift Card Data
GIFT_CARDS = {
    "amazon": {
        "name": "🟦 AMAZON", 
        "emoji": "🟦",
        "description": "Amazon Gift Card - Shop everything",
        "delivery": "Instant on Email"
    },
    "playstore": {
        "name": "🟩 PLAY STORE", 
        "emoji": "🟩",
        "description": "Google Play - Apps & Games",
        "delivery": "Instant on Email"
    },
    "bookmyshow": {
        "name": "🎟️ BOOKMYSHOW", 
        "emoji": "🎟️",
        "description": "Movie Tickets & Events",
        "delivery": "Instant on Email"
    },
    "myntra": {
        "name": "🛍️ MYNTRA", 
        "emoji": "🛍️",
        "description": "Fashion & Lifestyle",
        "delivery": "Instant on Email"
    },
    "flipkart": {
        "name": "📦 FLIPKART", 
        "emoji": "📦",
        "description": "Online Shopping",
        "delivery": "Instant on Email"
    },
    "zomato": {
        "name": "🍕 ZOMATO", 
        "emoji": "🍕",
        "description": "Food Delivery",
        "delivery": "Instant on Email"
    },
    "bigbasket": {
        "name": "🛒 BIG BASKET", 
        "emoji": "🛒",
        "description": "Grocery Delivery",
        "delivery": "Instant on Email"
    }
}

# Price configuration: [face_value] = selling_price
PRICES = {
    500: 100,
    1000: 200,
    2000: 400,
    5000: 1000
}

# Available denominations
AVAILABLE_DENOMINATIONS = [500, 1000, 2000, 5000]

# Conversation States
(
    SELECTING_ACTION,
    TYPING_AMOUNT,
    TYPING_SCREENSHOT,
    TYPING_UTR,
    TYPING_EMAIL,
    TYPING_SUPPORT,
    TYPING_CARD_DENOMINATION,
    CONFIRMING_PURCHASE,
    WAITING_PAYMENT,
    ADMIN_BROADCAST,
    ADMIN_UPDATE_PRICE,
    ADMIN_ADD_CARD,
    ADMIN_REMOVE_CARD
) = range(13)

# Payment status
PAYMENT_PENDING = "pending"
PAYMENT_APPROVED = "approved"
PAYMENT_REJECTED = "rejected"
PAYMENT_EXPIRED = "expired"

# Transaction types
TRANSACTION_CREDIT = "credit"
TRANSACTION_DEBIT = "debit"
TRANSACTION_REFUND = "refund"

# User roles
ROLE_USER = "user"
ROLE_ADMIN = "admin"
ROLE_MODERATOR = "moderator"

# Cache timeout (seconds)
CACHE_TIMEOUT = 300

# Rate limiting (requests per minute)
RATE_LIMIT = 30

# Session timeout (minutes)
SESSION_TIMEOUT = 10

# ==================== SETUP LOGGING ====================

class CustomFormatter(logging.Formatter):
    """Custom log formatter with colors"""
    
    grey = "\x1b[38;21m"
    blue = "\x1b[38;5;39m"
    yellow = "\x1b[38;5;226m"
    red = "\x1b[38;5;196m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    
    def __init__(self, fmt):
        super().__init__()
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: self.grey + self.fmt + self.reset,
            logging.INFO: self.blue + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.fmt + self.reset,
            logging.ERROR: self.red + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset
        }
    
    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

# Create logs directory if not exists
Path("logs").mkdir(exist_ok=True)

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# File handler
file_handler = logging.FileHandler(f"logs/{LOG_FILE}")
file_handler.setLevel(logging.INFO)
file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_format)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_format = CustomFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_format)

# Add handlers
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ==================== DATABASE MANAGER ====================

class DatabaseManager:
    """Thread-safe database manager with connection pooling"""
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.pool_size = 5
        self.connections = []
        
    async def initialize(self):
        """Initialize database and create tables"""
        async with self._lock:
            try:
                # Create multiple connections for pool
                for i in range(self.pool_size):
                    conn = sqlite3.connect(DATABASE_PATH, timeout=30)
                    conn.row_factory = sqlite3.Row
                    self.connections.append(conn)
                
                # Use first connection for setup
                conn = self.connections[0]
                c = conn.cursor()
                
                # Enable foreign keys and WAL mode
                c.execute("PRAGMA foreign_keys = ON")
                c.execute("PRAGMA journal_mode = WAL")
                
                # Users table
                c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    balance INTEGER DEFAULT 0,
                    total_spent INTEGER DEFAULT 0,
                    total_recharged INTEGER DEFAULT 0,
                    role TEXT DEFAULT 'user',
                    is_blocked INTEGER DEFAULT 0,
                    language TEXT DEFAULT 'en',
                    joined_date TIMESTAMP,
                    last_active TIMESTAMP,
                    last_ip TEXT,
                    referral_code TEXT UNIQUE,
                    referred_by INTEGER,
                    FOREIGN KEY (referred_by) REFERENCES users(user_id)
                )''')
                
                # Create index on username
                c.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
                
                # Transactions table
                c.execute('''CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount INTEGER,
                    type TEXT,
                    status TEXT,
                    utr TEXT UNIQUE,
                    payment_method TEXT,
                    fee INTEGER DEFAULT 0,
                    final_amount INTEGER,
                    description TEXT,
                    timestamp TIMESTAMP,
                    approved_by INTEGER,
                    approved_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (approved_by) REFERENCES users(user_id)
                )''')
                
                c.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_transactions_utr ON transactions(utr)")
                
                # Purchases table
                c.execute('''CREATE TABLE IF NOT EXISTS purchases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    card_type TEXT,
                    card_value INTEGER,
                    price INTEGER,
                    email TEXT,
                    order_id TEXT UNIQUE,
                    status TEXT,
                    card_code TEXT,
                    delivered_at TIMESTAMP,
                    timestamp TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )''')
                
                c.execute("CREATE INDEX IF NOT EXISTS idx_purchases_user ON purchases(user_id)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_purchases_order ON purchases(order_id)")
                
                # Pending verifications table
                c.execute('''CREATE TABLE IF NOT EXISTS pending_verifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount INTEGER,
                    fee INTEGER,
                    final_amount INTEGER,
                    utr TEXT UNIQUE,
                    screenshot_id TEXT,
                    status TEXT DEFAULT 'pending',
                    expires_at TIMESTAMP,
                    timestamp TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )''')
                
                # Support tickets table
                c.execute('''CREATE TABLE IF NOT EXISTS support_tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message TEXT,
                    reply TEXT,
                    status TEXT DEFAULT 'open',
                    priority INTEGER DEFAULT 1,
                    timestamp TIMESTAMP,
                    resolved_at TIMESTAMP,
                    resolved_by INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )''')
                
                # Gift cards inventory table
                c.execute('''CREATE TABLE IF NOT EXISTS gift_cards_inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    card_type TEXT,
                    value INTEGER,
                    code TEXT UNIQUE,
                    status TEXT DEFAULT 'available',
                    purchased_by INTEGER,
                    purchased_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    FOREIGN KEY (purchased_by) REFERENCES users(user_id)
                )''')
                
                # Referrals table
                c.execute('''CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER,
                    referred_id INTEGER UNIQUE,
                    bonus_amount INTEGER DEFAULT 10,
                    status TEXT DEFAULT 'pending',
                    timestamp TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (referrer_id) REFERENCES users(user_id),
                    FOREIGN KEY (referred_id) REFERENCES users(user_id)
                )''')
                
                # Settings table
                c.execute('''CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP,
                    updated_by INTEGER
                )''')
                
                # Insert default settings
                default_settings = [
                    ('upi_id', UPI_ID),
                    ('min_recharge', '10'),
                    ('max_recharge', '10000'),
                    ('recharge_fee_percent', '20'),
                    ('recharge_fee_threshold', '120'),
                    ('referral_bonus', '10'),
                    ('maintenance_mode', '0'),
                    ('welcome_message', 'Welcome to Gift Card Bot!'),
                    ('support_message', 'Contact support for help')
                ]
                
                for key, value in default_settings:
                    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
                
                conn.commit()
                logger.info("✅ Database initialized successfully")
                
            except sqlite3.Error as e:
                logger.error(f"❌ Database initialization error: {e}")
                raise
    
    async def get_connection(self):
        """Get a connection from the pool"""
        async with self._lock:
            if not self.connections:
                await self.initialize()
            # Simple round-robin connection selection
            conn = self.connections.pop(0)
            self.connections.append(conn)
            return conn
    
    async def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute a query and return results"""
        conn = await self.get_connection()
        try:
            c = conn.cursor()
            c.execute(query, params)
            if query.strip().upper().startswith('SELECT'):
                results = [dict(row) for row in c.fetchall()]
                return results
            else:
                conn.commit()
                return {'rowcount': c.rowcount, 'lastrowid': c.lastrowid}
        except sqlite3.Error as e:
            logger.error(f"❌ Database query error: {e}")
            conn.rollback()
            raise
        finally:
            pass  # Connection returns to pool automatically
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        results = await self.execute_query(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        )
        return results[0] if results else None
    
    async def create_user(self, user_id: int, username: str = None, first_name: str = None) -> Dict:
        """Create a new user"""
        now = datetime.now().isoformat()
        referral_code = hashlib.md5(f"{user_id}{now}".encode()).hexdigest()[:8]
        
        await self.execute_query(
            """INSERT INTO users 
               (user_id, username, first_name, balance, joined_date, last_active, referral_code)
               VALUES (?, ?, ?, 0, ?, ?, ?)""",
            (user_id, username, first_name, now, now, referral_code)
        )
        
        return await self.get_user(user_id)
    
    async def update_balance(self, user_id: int, amount: int, transaction_type: str, **kwargs) -> bool:
        """Update user balance and record transaction"""
        try:
            # Get current balance
            user = await self.get_user(user_id)
            if not user:
                return False
            
            new_balance = user['balance'] + amount
            if new_balance < 0:
                return False
            
            # Update balance
            await self.execute_query(
                "UPDATE users SET balance = ?, last_active = ? WHERE user_id = ?",
                (new_balance, datetime.now().isoformat(), user_id)
            )
            
            # Record transaction
            await self.execute_query(
                """INSERT INTO transactions 
                   (user_id, amount, type, status, utr, payment_method, fee, final_amount, description, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, abs(amount), transaction_type, 'completed', 
                 kwargs.get('utr'), kwargs.get('payment_method'),
                 kwargs.get('fee', 0), kwargs.get('final_amount', amount),
                 kwargs.get('description', ''), datetime.now().isoformat())
            )
            
            # Update totals
            if amount > 0:
                await self.execute_query(
                    "UPDATE users SET total_recharged = total_recharged + ? WHERE user_id = ?",
                    (amount, user_id)
                )
            else:
                await self.execute_query(
                    "UPDATE users SET total_spent = total_spent + ? WHERE user_id = ?",
                    (abs(amount), user_id)
                )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Balance update error: {e}")
            return False
    
    async def create_purchase(self, user_id: int, card_type: str, value: int, price: int, email: str) -> str:
        """Create a purchase record and return order ID"""
        order_id = f"GC{random.randint(100000, 999999)}"
        now = datetime.now().isoformat()
        
        await self.execute_query(
            """INSERT INTO purchases 
               (user_id, card_type, card_value, price, email, order_id, status, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, 'completed', ?)""",
            (user_id, card_type, value, price, email, order_id, now)
        )
        
        return order_id
    
    async def create_pending_verification(self, user_id: int, amount: int, fee: int, 
                                          final_amount: int, utr: str, screenshot_id: str) -> int:
        """Create a pending payment verification"""
        expires_at = (datetime.now() + timedelta(minutes=30)).isoformat()
        now = datetime.now().isoformat()
        
        result = await self.execute_query(
            """INSERT INTO pending_verifications 
               (user_id, amount, fee, final_amount, utr, screenshot_id, expires_at, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, amount, fee, final_amount, utr, screenshot_id, expires_at, now)
        )
        
        return result['lastrowid']
    
    async def get_pending_verifications(self) -> List[Dict]:
        """Get all pending verifications"""
        return await self.execute_query(
            """SELECT * FROM pending_verifications 
               WHERE status = 'pending' AND expires_at > datetime('now')
               ORDER BY timestamp DESC"""
        )
    
    async def approve_payment(self, verification_id: int, admin_id: int) -> bool:
        """Approve a pending payment"""
        try:
            # Get verification
            verifications = await self.execute_query(
                "SELECT * FROM pending_verifications WHERE id = ?",
                (verification_id,)
            )
            
            if not verifications:
                return False
            
            v = verifications[0]
            
            # Update balance
            success = await self.update_balance(
                v['user_id'], v['final_amount'], TRANSACTION_CREDIT,
                utr=v['utr'], payment_method='UPI', fee=v['fee'],
                final_amount=v['final_amount'], description='UPI Recharge'
            )
            
            if success:
                # Update verification status
                await self.execute_query(
                    "UPDATE pending_verifications SET status = 'approved' WHERE id = ?",
                    (verification_id,)
                )
                
                # Update transaction with approval info
                await self.execute_query(
                    """UPDATE transactions SET approved_by = ?, approved_at = ? 
                       WHERE utr = ?""",
                    (admin_id, datetime.now().isoformat(), v['utr'])
                )
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Payment approval error: {e}")
            return False
    
    async def reject_payment(self, verification_id: int, admin_id: int) -> bool:
        """Reject a pending payment"""
        try:
            await self.execute_query(
                "UPDATE pending_verifications SET status = 'rejected' WHERE id = ?",
                (verification_id,)
            )
            
            # Get verification for notification
            verifications = await self.execute_query(
                "SELECT * FROM pending_verifications WHERE id = ?",
                (verification_id,)
            )
            
            return bool(verifications)
            
        except Exception as e:
            logger.error(f"❌ Payment rejection error: {e}")
            return False
    
    async def get_statistics(self) -> Dict:
        """Get bot statistics"""
        stats = {}
        
        # Total users
        result = await self.execute_query("SELECT COUNT(*) as count FROM users")
        stats['total_users'] = result[0]['count']
        
        # Active users today
        today = datetime.now().date().isoformat()
        result = await self.execute_query(
            "SELECT COUNT(*) as count FROM users WHERE date(last_active) = ?",
            (today,)
        )
        stats['active_today'] = result[0]['count']
        
        # Total transactions
        result = await self.execute_query("SELECT COUNT(*) as count FROM transactions")
        stats['total_transactions'] = result[0]['count']
        
        # Total revenue
        result = await self.execute_query(
            "SELECT SUM(amount) as total FROM transactions WHERE type = 'credit' AND status = 'completed'"
        )
        stats['total_revenue'] = result[0]['total'] or 0
        
        # Total spent
        result = await self.execute_query(
            "SELECT SUM(price) as total FROM purchases WHERE status = 'completed'"
        )
        stats['total_spent'] = result[0]['total'] or 0
        
        # Pending verifications
        result = await self.execute_query(
            "SELECT COUNT(*) as count FROM pending_verifications WHERE status = 'pending'"
        )
        stats['pending_verifications'] = result[0]['count']
        
        # Open support tickets
        result = await self.execute_query(
            "SELECT COUNT(*) as count FROM support_tickets WHERE status = 'open'"
        )
        stats['open_tickets'] = result[0]['count']
        
        return stats
    
    async def cleanup_expired(self):
        """Clean up expired sessions and verifications"""
        try:
            # Expire old pending verifications
            await self.execute_query(
                "UPDATE pending_verifications SET status = 'expired' WHERE expires_at < datetime('now')"
            )
            
            # Delete old sessions (optional)
            # You can add more cleanup logic here
            
            logger.info("✅ Cleaned up expired records")
            
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")

# ==================== CACHE MANAGER ====================

class CacheManager:
    """Simple in-memory cache with TTL"""
    
    def __init__(self):
        self._cache = {}
        self._timers = {}
    
    def set(self, key: str, value: Any, ttl: int = CACHE_TIMEOUT):
        """Set a cache value with TTL"""
        self._cache[key] = value
        self._timers[key] = time.time() + ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get a cache value if not expired"""
        if key in self._cache:
            if time.time() < self._timers[key]:
                return self._cache[key]
            else:
                self.delete(key)
        return None
    
    def delete(self, key: str):
        """Delete a cache entry"""
        self._cache.pop(key, None)
        self._timers.pop(key, None)
    
    def clear(self):
        """Clear all cache"""
        self._cache.clear()
        self._timers.clear()
    
    def cleanup(self):
        """Remove expired entries"""
        now = time.time()
        expired = [k for k, t in self._timers.items() if now >= t]
        for k in expired:
            self.delete(k)

# ==================== RATE LIMITER ====================

class RateLimiter:
    """Simple rate limiter for user actions"""
    
    def __init__(self):
        self._user_requests = {}
    
    def is_allowed(self, user_id: int) -> bool:
        """Check if user is allowed to make request"""
        now = time.time()
        minute_ago = now - 60
        
        if user_id not in self._user_requests:
            self._user_requests[user_id] = []
        
        # Clean old requests
        self._user_requests[user_id] = [
            t for t in self._user_requests[user_id] if t > minute_ago
        ]
        
        # Check rate
        if len(self._user_requests[user_id]) >= RATE_LIMIT:
            return False
        
        # Add request
        self._user_requests[user_id].append(now)
        return True
    
    def get_remaining(self, user_id: int) -> int:
        """Get remaining requests for user"""
        if user_id not in self._user_requests:
            return RATE_LIMIT
        
        now = time.time()
        minute_ago = now - 60
        recent = [t for t in self._user_requests[user_id] if t > minute_ago]
        return max(0, RATE_LIMIT - len(recent))

# ==================== SESSION MANAGER ====================

class SessionManager:
    """Manage user sessions"""
    
    def __init__(self):
        self._sessions = {}
        self._timeout = SESSION_TIMEOUT * 60
    
    def get_session(self, user_id: int) -> Dict:
        """Get or create user session"""
        if user_id not in self._sessions:
            self._sessions[user_id] = {
                'data': {},
                'created_at': time.time(),
                'last_active': time.time()
            }
        else:
            self._sessions[user_id]['last_active'] = time.time()
        
        return self._sessions[user_id]['data']
    
    def update_session(self, user_id: int, data: Dict):
        """Update user session"""
        if user_id in self._sessions:
            self._sessions[user_id]['data'].update(data)
            self._sessions[user_id]['last_active'] = time.time()
    
    def clear_session(self, user_id: int):
        """Clear user session"""
        if user_id in self._sessions:
            del self._sessions[user_id]
    
    def cleanup(self):
        """Remove expired sessions"""
        now = time.time()
        expired = [
            uid for uid, sess in self._sessions.items()
            if now - sess['last_active'] > self._timeout
        ]
        for uid in expired:
            self.clear_session(uid)

# ==================== INITIALIZE MANAGERS ====================

db_manager = DatabaseManager()
cache_manager = CacheManager()
rate_limiter = RateLimiter()
session_manager = SessionManager()

# ==================== DECORATORS ====================

def admin_only(func):
    """Decorator to restrict command to admin only"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if user.id != ADMIN_ID:
            await update.message.reply_text(
                "❌ *Unauthorized*\n\nThis command is for admins only.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def rate_limit(func):
    """Decorator to apply rate limiting"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not rate_limiter.is_allowed(user.id):
            remaining = rate_limiter.get_remaining(user.id)
            await update.message.reply_text(
                f"⚠️ *Rate Limited*\n\nPlease wait {remaining} seconds.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def check_membership(func):
    """Decorator to check channel membership"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        
        # Check cache first
        cache_key = f"membership_{user.id}"
        cached = cache_manager.get(cache_key)
        if cached is not None:
            if cached:
                return await func(update, context, *args, **kwargs)
        else:
            try:
                member = await context.bot.get_chat_member(
                    chat_id=MAIN_CHANNEL, 
                    user_id=user.id
                )
                is_member = member.status in ['member', 'administrator', 'creator']
                cache_manager.set(cache_key, is_member, 300)  # Cache for 5 minutes
                
                if not is_member:
                    keyboard = [[
                        InlineKeyboardButton("📢 JOIN CHANNEL", url=f"https://t.me/gift_card_main"),
                        InlineKeyboardButton("✅ VERIFY", callback_data="verify")
                    ]]
                    await update.message.reply_text(
                        f"⚠️ *Access Denied*\n\nYou must join @gift_card_main first.",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    return
                
                return await func(update, context, *args, **kwargs)
                
            except Exception as e:
                logger.error(f"❌ Membership check error: {e}")
                await update.message.reply_text("⚠️ Error checking membership. Try again.")
                return
    
    return wrapper

def log_action(func):
    """Decorator to log user actions"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        action = func.__name__
        logger.info(f"👤 User {user.id} ({user.first_name}) performed: {action}")
        
        try:
            result = await func(update, context, *args, **kwargs)
            logger.info(f"✅ Action {action} completed successfully")
            return result
        except Exception as e:
            logger.error(f"❌ Action {action} failed: {e}")
            raise
    
    return wrapper

# ==================== HELPER FUNCTIONS ====================

def format_currency(amount: int) -> str:
    """Format amount with ₹ symbol and commas"""
    return f"₹{amount:,}"

def generate_order_id() -> str:
    """Generate unique order ID"""
    timestamp = datetime.now().strftime("%y%m%d%H%M%S")
    random_part = random.randint(1000, 9999)
    return f"GC{timestamp}{random_part}"

def format_datetime(dt_str: str) -> str:
    """Format datetime string"""
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%d %b %Y, %I:%M %p")
    except:
        return dt_str

def validate_email(email: str) -> bool:
    """Simple email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_utr(utr: str) -> bool:
    """Simple UTR validation"""
    # UTR typically 12-22 alphanumeric characters
    return 12 <= len(utr) <= 22 and utr.isalnum()

def calculate_fee(amount: int) -> Tuple[int, int]:
    """Calculate fee and final amount"""
    threshold = 120
    fee_percent = 20
    
    if amount < threshold:
        fee = int(amount * fee_percent / 100)
        final = amount - fee
    else:
        fee = 0
        final = amount
    
    return fee, final

# ==================== START COMMAND ====================

@log_action
@rate_limit
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    try:
        user = update.effective_user
        
        # Get or create user in database
        db_user = await db_manager.get_user(user.id)
        if not db_user:
            db_user = await db_manager.create_user(
                user.id, 
                user.username, 
                user.first_name
            )
            logger.info(f"✅ New user registered: {user.id} - {user.first_name}")
        
        # Check membership
        try:
            member = await context.bot.get_chat_member(
                chat_id=MAIN_CHANNEL, 
                user_id=user.id
            )
            is_member = member.status in ['member', 'administrator', 'creator']
        except:
            is_member = False
        
        if not is_member:
            # Welcome message for new users
            welcome_text = (
                f"✨ *WELCOME TO GIFT CARD BOT* ✨\n\n"
                f"👋 *Hello {user.first_name}!*\n\n"
                f"🎁 *Get Gift Cards at 80% OFF!*\n"
                f"• Amazon • Flipkart • Play Store\n"
                f"• Myntra • Zomato • & More!\n\n"
                f"🔒 *VERIFICATION REQUIRED*\n"
                f"To ensure safe transactions, you must join our channel.\n\n"
                f"👇 *Click below to join and verify*"
            )
            
            keyboard = [[
                InlineKeyboardButton("📢 JOIN CHANNEL", url=f"https://t.me/gift_card_main"),
                InlineKeyboardButton("✅ VERIFY", callback_data="verify")
            ]]
            
            await update.message.reply_text(
                welcome_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        # Show main menu for verified users
        balance = db_user['balance']
        
        # Get session data
        session = session_manager.get_session(user.id)
        
        main_menu_text = (
            f"🎉 *WELCOME BACK!* 🎉\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 *User:* {user.first_name}\n"
            f"💰 *Balance:* {format_currency(balance)}\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"*What would you like to do today?*"
        )
        
        keyboard = [
            [InlineKeyboardButton("🎁 GIFT CARDS", callback_data="giftcard")],
            [InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")],
            [InlineKeyboardButton("💳 MY BALANCE", callback_data="balance")],
            [InlineKeyboardButton("🆘 SUPPORT", callback_data="support")],
            [InlineKeyboardButton("📊 PROOFS", callback_data="proofs")]
        ]
        
        await update.message.reply_text(
            main_menu_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"❌ Start error: {e}")
        await update.message.reply_text(
            "⚠️ *Error*\n\nPlease try again later.",
            parse_mode=ParseMode.MARKDOWN
        )

# ==================== BUTTON HANDLER ====================

@log_action
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data
    
    logger.info(f"🔘 Button clicked: {data} by {user.first_name} (ID: {user.id})")
    
    # Get session
    session = session_manager.get_session(user.id)
    
    # ===== VERIFY BUTTON =====
    if data == "verify":
        try:
            member = await context.bot.get_chat_member(
                chat_id=MAIN_CHANNEL, 
                user_id=user.id
            )
            is_member = member.status in ['member', 'administrator', 'creator']
            
            if is_member:
                # Get user from database
                db_user = await db_manager.get_user(user.id)
                if not db_user:
                    db_user = await db_manager.create_user(user.id, user.username, user.first_name)
                
                balance = db_user['balance']
                
                success_text = (
                    f"✅ *VERIFICATION SUCCESSFUL!*\n\n"
                    f"👋 *Welcome {user.first_name}!*\n"
                    f"💰 *Balance:* {format_currency(balance)}\n\n"
                    f"*You now have full access to:*\n"
                    f"• 7+ Gift Card Brands\n"
                    f"• Instant UPI Recharge\n"
                    f"• 24/7 Auto Delivery\n"
                    f"• Live Proofs Channel\n\n"
                    f"⬇️ *Choose an option:*"
                )
                
                keyboard = [
                    [InlineKeyboardButton("🎁 GIFT CARDS", callback_data="giftcard")],
                    [InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")],
                    [InlineKeyboardButton("💳 MY BALANCE", callback_data="balance")],
                    [InlineKeyboardButton("🆘 SUPPORT", callback_data="support")],
                    [InlineKeyboardButton("📊 PROOFS", callback_data="proofs")]
                ]
                
                await query.edit_message_text(
                    success_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                fail_text = (
                    f"❌ *VERIFICATION FAILED*\n\n"
                    f"You haven't joined our channel yet!\n\n"
                    f"1️⃣ Click JOIN CHANNEL\n"
                    f"2️⃣ Join @gift_card_main\n"
                    f"3️⃣ Click VERIFY AGAIN"
                )
                
                keyboard = [[
                    InlineKeyboardButton("📢 JOIN CHANNEL", url=f"https://t.me/gift_card_main"),
                    InlineKeyboardButton("🔄 VERIFY AGAIN", callback_data="verify")
                ]]
                
                await query.edit_message_text(
                    fail_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        except Exception as e:
            logger.error(f"❌ Verify error: {e}")
            await query.edit_message_text(
                "⚠️ *Error*\n\nPlease try again later.",
                parse_mode=ParseMode.MARKDOWN
            )
        return
    
    # Check membership for all other actions
    try:
        member = await context.bot.get_chat_member(
            chat_id=MAIN_CHANNEL, 
            user_id=user.id
        )
        is_member = member.status in ['member', 'administrator', 'creator']
        
        if not is_member:
            keyboard = [[
                InlineKeyboardButton("📢 JOIN CHANNEL", url=f"https://t.me/gift_card_main"),
                InlineKeyboardButton("✅ VERIFY", callback_data="verify")
            ]]
            
            await query.edit_message_text(
                f"⚠️ *ACCESS DENIED*\n\nYou must join @gift_card_main first.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
    except Exception as e:
        logger.error(f"❌ Membership check error: {e}")
        await query.edit_message_text(
            "⚠️ *Error*\n\nPlease try again later.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # ===== GIFT CARD MENU =====
    if data == "giftcard":
        keyboard = []
        for card_id, card in GIFT_CARDS.items():
            keyboard.append([InlineKeyboardButton(
                f"{card['emoji']} {card['name']}", 
                callback_data=f"card_{card_id}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 BACK", callback_data="main_menu")])
        
        giftcard_text = (
            f"🎁 *GIFT CARDS*\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"*Select your preferred brand:*\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"💳 *All cards delivered INSTANTLY on email*\n"
            f"⚡ *24/7 Automatic Delivery*\n"
            f"✅ *100% Working Codes*"
        )
        
        await query.edit_message_text(
            giftcard_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== CARD SELECTED =====
    elif data.startswith("card_"):
        card_id = data.replace("card_", "")
        card = GIFT_CARDS.get(card_id)
        
        if not card:
            await query.edit_message_text("❌ Card not found")
            return
        
        keyboard = []
        for denom in AVAILABLE_DENOMINATIONS:
            if denom in PRICES:
                price = PRICES[denom]
                keyboard.append([InlineKeyboardButton(
                    f"💳 ₹{denom} FOR JUST ₹{price}", 
                    callback_data=f"buy_{card_id}_{denom}"
                )])
        
        keyboard.append([InlineKeyboardButton("🔙 BACK", callback_data="giftcard")])
        
        card_text = (
            f"{card['emoji']} *{card['name']}*\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📱 *Delivery:* {card['delivery']}\n"
            f"⚡ *Time:* Instant\n"
            f"✅ *Status:* IN SALE\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"*Select denomination:*"
        )
        
        await query.edit_message_text(
            card_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== BUY CARD =====
    elif data.startswith("buy_"):
        parts = data.split("_")
        if len(parts) < 3:
            await query.edit_message_text("❌ Invalid selection")
            return
        
        card_id = parts[1]
        try:
            value = int(parts[2])
        except:
            await query.edit_message_text("❌ Invalid amount")
            return
        
        card = GIFT_CARDS.get(card_id)
        if not card:
            await query.edit_message_text("❌ Card not found")
            return
        
        if value not in PRICES:
            await query.edit_message_text("❌ Denomination not available")
            return
        
        price = PRICES[value]
        
        # Get user balance
        db_user = await db_manager.get_user(user.id)
        if not db_user:
            db_user = await db_manager.create_user(user.id, user.username, user.first_name)
        
        balance = db_user['balance']
        
        if balance < price:
            short = price - balance
            keyboard = [
                [InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")],
                [InlineKeyboardButton("🏠 MAIN MENU", callback_data="main_menu")]
            ]
            
            await query.edit_message_text(
                f"❌ *INSUFFICIENT BALANCE*\n\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"*Card:* {card['emoji']} {card['name']} ₹{value}\n"
                f"*Price:* {format_currency(price)}\n"
                f"*Your Balance:* {format_currency(balance)}\n"
                f"*Short by:* {format_currency(short)}\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"Please add money to your wallet.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        # Store purchase data in session
        session['purchase'] = {
            'card_id': card_id,
            'card_name': card['name'],
            'card_emoji': card['emoji'],
            'value': value,
            'price': price
        }
        session_manager.update_session(user.id, session)
        
        await query.edit_message_text(
            f"✅ *BALANCE SUFFICIENT*\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"*{card['emoji']} {card['name']} ₹{value}*\n"
            f"*Price:* {format_currency(price)}\n"
            f"*Your Balance:* {format_currency(balance)}\n"
            f"*New Balance:* {format_currency(balance - price)}\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"📧 *Please enter your EMAIL address:*\n"
            f"_(Example: example@gmail.com)_",
            parse_mode=ParseMode.MARKDOWN
        )
        
        return TYPING_EMAIL
    
    # ===== TOP UP MENU =====
    elif data == "topup":
        keyboard = [
            [InlineKeyboardButton("📱 UPI PAYMENT", callback_data="upi")],
            [InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]
        ]
        
        topup_text = (
            f"💰 *ADD MONEY TO WALLET*\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"*Select payment method:*\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"📱 *UPI* - Instant & Easy\n"
            f"• Google Pay • PhonePe • Paytm\n"
            f"• BHIM • Any UPI App"
        )
        
        await query.edit_message_text(
            topup_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== UPI SELECTED =====
    elif data == "upi":
        # Get settings
        settings = await db_manager.execute_query(
            "SELECT * FROM settings WHERE key IN ('min_recharge', 'max_recharge')"
        )
        min_recharge = 10
        max_recharge = 10000
        for s in settings:
            if s['key'] == 'min_recharge':
                min_recharge = int(s['value'])
            elif s['key'] == 'max_recharge':
                max_recharge = int(s['value'])
        
        upi_text = (
            f"💳 *UPI RECHARGE*\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"*Please enter the amount to add:*\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 *Minimum:* {format_currency(min_recharge)}\n"
            f"💰 *Maximum:* {format_currency(max_recharge)}\n\n"
            f"📌 *NOTE:* 20% fee for payments below ₹120\n"
            f"       • Pay ₹100 → Get ₹80\n"
            f"       • Pay ₹200 → Get ₹200\n\n"
            f"*Enter amount (in numbers):*"
        )
        
        await query.edit_message_text(
            upi_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        return TYPING_AMOUNT
    
    # ===== PAID BUTTON =====
    elif data == "paid":
        if 'topup' not in session:
            await query.edit_message_text(
                "❌ *SESSION EXPIRED*\n\nPlease start over with /start",
                parse_mode=ParseMode.MARKDOWN
            )
            return ConversationHandler.END
        
        keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]]
        
        await query.edit_message_text(
            f"📤 *SEND PAYMENT PROOF*\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"*Please send the following:*\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"1️⃣ *PAYMENT SCREENSHOT* (as photo)\n"
            f"2️⃣ *UTR NUMBER* (in text)\n\n"
            f"*Example UTR:* `SBIN1234567890`\n\n"
            f"*Send both in this chat.*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return TYPING_SCREENSHOT
    
    # ===== CANCEL TOPUP =====
    elif data == "cancel_topup":
        # Clear session data
        if 'topup' in session:
            del session['topup']
        session_manager.update_session(user.id, session)
        
        keyboard = [
            [InlineKeyboardButton("📱 UPI", callback_data="upi")],
            [InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            f"❌ *CANCELLED*\n\n"
            f"Top-up process cancelled.\n\n"
            f"*Select payment method:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return ConversationHandler.END
    
    # ===== BALANCE =====
    elif data == "balance":
        db_user = await db_manager.get_user(user.id)
        balance = db_user['balance'] if db_user else 0
        
        # Get recent transactions
        transactions = await db_manager.execute_query(
            """SELECT amount, type, timestamp FROM transactions 
               WHERE user_id = ? ORDER BY timestamp DESC LIMIT 5""",
            (user.id,)
        )
        
        trans_text = ""
        for t in transactions:
            amount = t['amount']
            type_ = t['type']
            time_str = format_datetime(t['timestamp']).split(',')[0]
            
            if type_ == 'credit':
                trans_text += f"• *+{format_currency(amount)}* on {time_str}\n"
            else:
                trans_text += f"• *-{format_currency(amount)}* on {time_str}\n"
        
        if not trans_text:
            trans_text = "• No transactions yet"
        
        balance_text = (
            f"💳 *YOUR WALLET*\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 *Available Balance:* {format_currency(balance)}\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"*📊 Recent Activity:*\n"
            f"{trans_text}"
        )
        
        keyboard = [
            [InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")],
            [InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            balance_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== SUPPORT =====
    elif data == "support":
        support_text = (
            f"🆘 *HELP & SUPPORT*\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"*How can we help you?*\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"❓ *Common Issues:*\n"
            f"• Card not received\n"
            f"• Payment not credited\n"
            f"• Wrong amount sent\n"
            f"• Technical issues\n\n"
            f"📝 *Please type your issue below:*\n\n"
            f"*Our support team will contact you soon.*"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]]
        
        await query.edit_message_text(
            support_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return TYPING_SUPPORT
    
    # ===== PROOFS =====
    elif data == "proofs":
        proofs_text = (
            f"📊 *LIVE PURCHASE PROOFS*\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✅ *See real transactions:*\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"👉 {PROOF_CHANNEL}\n\n"
            f"⚡ *Latest Activity:*\n"
            f"• Users buying daily\n"
            f"• Instant delivery\n"
            f"• 100% satisfaction\n\n"
            f"*Click below to join*"
        )
        
        keyboard = [
            [InlineKeyboardButton("📢 VIEW CHANNEL", url=f"https://t.me/gift_card_log")],
            [InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            proofs_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== MAIN MENU =====
    elif data == "main_menu":
        db_user = await db_manager.get_user(user.id)
        balance = db_user['balance'] if db_user else 0
        
        main_text = (
            f"🏠 *MAIN MENU*\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 *User:* {user.first_name}\n"
            f"💰 *Balance:* {format_currency(balance)}\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"*Please select an option:*"
        )
        
        keyboard = [
            [InlineKeyboardButton("🎁 GIFT CARDS", callback_data="giftcard")],
            [InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")],
            [InlineKeyboardButton("💳 MY BALANCE", callback_data="balance")],
            [InlineKeyboardButton("🆘 SUPPORT", callback_data="support")],
            [InlineKeyboardButton("📊 PROOFS", callback_data="proofs")]
        ]
        
        await query.edit_message_text(
            main_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ==================== AMOUNT HANDLER ====================

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle amount input for top-up"""
    try:
        user = update.effective_user
        text = update.message.text.strip()
        
        # Validate amount
        try:
            amount = int(text)
        except ValueError:
            await update.message.reply_text(
                "❌ *Invalid input*\n\nPlease enter a valid number.",
                parse_mode=ParseMode.MARKDOWN
            )
            return TYPING_AMOUNT
        
        # Get settings
        settings = await db_manager.execute_query(
            "SELECT * FROM settings WHERE key IN ('min_recharge', 'max_recharge')"
        )
        min_recharge = 10
        max_recharge = 10000
        for s in settings:
            if s['key'] == 'min_recharge':
                min_recharge = int(s['value'])
            elif s['key'] == 'max_recharge':
                max_recharge = int(s['value'])
        
        if amount < min_recharge or amount > max_recharge:
            await update.message.reply_text(
                f"❌ *Invalid amount*\n\n"
                f"Amount must be between {format_currency(min_recharge)} "
                f"and {format_currency(max_recharge)}.",
                parse_mode=ParseMode.MARKDOWN
            )
            return TYPING_AMOUNT
        
        # Calculate fee
        fee, final = calculate_fee(amount)
        
        if fee > 0:
            fee_text = f"*Fee (20%):* {format_currency(fee)}"
        else:
            fee_text = "*Fee:* No fee (above ₹120)"
        
        # Store in session
        session = session_manager.get_session(user.id)
        session['topup'] = {
            'amount': amount,
            'final': final,
            'fee': fee
        }
        session_manager.update_session(user.id, session)
        
        # Create buttons
        keyboard = [
            [InlineKeyboardButton("✅ I HAVE PAID", callback_data="paid")],
            [InlineKeyboardButton("❌ CANCEL", callback_data="cancel_topup")]
        ]
        
        # Try to send QR code
        qr_sent = False
        if os.path.exists(QR_CODE_PATH):
            try:
                with open(QR_CODE_PATH, 'rb') as qr_file:
                    await update.message.reply_photo(
                        photo=qr_file,
                        caption=(
                            f"💳 *PAYMENT DETAILS*\n\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"*UPI ID:* `{UPI_ID}`\n"
                            f"*Amount:* {format_currency(amount)}\n"
                            f"{fee_text}\n"
                            f"*You get:* {format_currency(final)}\n"
                            f"━━━━━━━━━━━━━━━━━━\n\n"
                            f"📱 *HOW TO PAY:*\n"
                            f"1️⃣ Scan QR code or pay to UPI ID\n"
                            f"2️⃣ Take a SCREENSHOT\n"
                            f"3️⃣ Copy UTR number\n"
                            f"4️⃣ Click 'I HAVE PAID'\n\n"
                            f"⏳ *Auto-cancel in 10 minutes*"
                        ),
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    qr_sent = True
            except Exception as e:
                logger.error(f"❌ QR code send error: {e}")
        
        if not qr_sent:
            await update.message.reply_text(
                f"💳 *PAYMENT DETAILS*\n\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"*UPI ID:* `{UPI_ID}`\n"
                f"*Amount:* {format_currency(amount)}\n"
                f"{fee_text}\n"
                f"*You get:* {format_currency(final)}\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"📱 *HOW TO PAY:*\n"
                f"1️⃣ Open any UPI app\n"
                f"2️⃣ Pay to UPI ID above\n"
                f"3️⃣ Take a SCREENSHOT\n"
                f"4️⃣ Copy UTR number\n"
                f"5️⃣ Click 'I HAVE PAID'\n\n"
                f"⏳ *Auto-cancel in 10 minutes*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"❌ Amount handler error: {e}")
        await update.message.reply_text(
            "⚠️ *Error*\n\nPlease try again.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END

# ==================== SCREENSHOT HANDLER ====================

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle screenshot for payment verification"""
    try:
        user = update.effective_user
        
        if not update.message.photo:
            await update.message.reply_text(
                "❌ *Please send a PHOTO*\n\n"
                "Send the screenshot of your payment.",
                parse_mode=ParseMode.MARKDOWN
            )
            return TYPING_SCREENSHOT
        
        # Get session
        session = session_manager.get_session(user.id)
        
        # Store photo ID
        photo = update.message.photo[-1].file_id
        session['screenshot'] = photo
        session_manager.update_session(user.id, session)
        
        keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]]
        
        await update.message.reply_text(
            "✅ *SCREENSHOT RECEIVED*\n\n"
            "Now please send your *UTR number*.\n\n"
            "📌 *UTR* is the 12-22 digit reference number\n"
            "from your bank statement or payment app.\n\n"
            "Example: `SBIN1234567890`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return TYPING_UTR
        
    except Exception as e:
        logger.error(f"❌ Screenshot handler error: {e}")
        return TYPING_SCREENSHOT

# ==================== UTR HANDLER ====================

async def handle_utr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle UTR input for payment verification"""
    try:
        user = update.effective_user
        utr = update.message.text.strip()
        
        # Validate UTR
        if not validate_utr(utr):
            await update.message.reply_text(
                "❌ *Invalid UTR*\n\n"
                "UTR should be 12-22 alphanumeric characters.\n"
                "Please check and try again.",
                parse_mode=ParseMode.MARKDOWN
            )
            return TYPING_UTR
        
        # Get session
        session = session_manager.get_session(user.id)
        
        # Check if we have required data
        if 'screenshot' not in session:
            await update.message.reply_text(
                "❌ *Please send screenshot first*",
                parse_mode=ParseMode.MARKDOWN
            )
            return TYPING_SCREENSHOT
        
        if 'topup' not in session:
            await update.message.reply_text(
                "❌ *Session expired*\n\nPlease start over with /start",
                parse_mode=ParseMode.MARKDOWN
            )
            return ConversationHandler.END
        
        topup_data = session['topup']
        screenshot = session['screenshot']
        
        # Check for duplicate UTR
        existing = await db_manager.execute_query(
            "SELECT id FROM pending_verifications WHERE utr = ?",
            (utr,)
        )
        if existing:
            await update.message.reply_text(
                "❌ *Duplicate UTR*\n\n"
                "This UTR has already been submitted.\n"
                "Please check and try again.",
                parse_mode=ParseMode.MARKDOWN
            )
            return TYPING_UTR
        
        # Create pending verification
        verification_id = await db_manager.create_pending_verification(
            user.id,
            topup_data['amount'],
            topup_data['fee'],
            topup_data['final'],
            utr,
            screenshot
        )
        
        # Get user info for admin
        db_user = await db_manager.get_user(user.id)
        username = db_user.get('username', 'No username')
        
        # Create admin message
        caption = (
            f"🔔 *NEW PAYMENT VERIFICATION*\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 *User:* {user.first_name}\n"
            f"🆔 *ID:* `{user.id}`\n"
            f"👤 *Username:* @{username}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 *Amount:* {format_currency(topup_data['amount'])}\n"
            f"💸 *Fee:* {format_currency(topup_data['fee'])}\n"
            f"🎁 *Credit:* {format_currency(topup_data['final'])}\n"
            f"🔢 *UTR:* `{utr}`\n"
            f"🆔 *Verification ID:* `{verification_id}`\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⏰ *Time:* {datetime.now().strftime('%d %b %Y, %I:%M %p')}"
        )
        
        # Create approve/reject buttons
        keyboard = [[
            InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{verification_id}"),
            InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{verification_id}")
        ]]
        
        # Send to admin channel
        await context.bot.send_photo(
            chat_id=ADMIN_CHANNEL_ID,
            photo=screenshot,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Clear session data
        session.pop('topup', None)
        session.pop('screenshot', None)
        session_manager.update_session(user.id, session)
        
        # Confirm to user
        keyboard = [[InlineKeyboardButton("🏠 MAIN MENU", callback_data="main_menu")]]
        
        await update.message.reply_text(
            f"✅ *VERIFICATION SUBMITTED!*\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"*Verification ID:* `{verification_id}`\n"
            f"*UTR:* `{utr}`\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"Your payment is being verified.\n"
            f"You will be notified once approved.\n\n"
            f"⏳ *Estimated time: 5-10 minutes*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"❌ UTR handler error: {e}")
        await update.message.reply_text(
            "⚠️ *Error*\n\nPlease try again.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END

# ==================== EMAIL HANDLER ====================

async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle email input for gift card delivery"""
    try:
        user = update.effective_user
        email = update.message.text.strip()
        
        # Validate email
        if not validate_email(email):
            await update.message.reply_text(
                "❌ *Invalid email*\n\n"
                "Please enter a valid email address.\n"
                "Example: `example@gmail.com`",
                parse_mode=ParseMode.MARKDOWN
            )
            return TYPING_EMAIL
        
        # Get session
        session = session_manager.get_session(user.id)
        
        if 'purchase' not in session:
            await update.message.reply_text(
                "❌ *Session expired*\n\nPlease start over with /start",
                parse_mode=ParseMode.MARKDOWN
            )
            return ConversationHandler.END
        
        purchase = session['purchase']
        
        # Get user balance
        db_user = await db_manager.get_user(user.id)
        balance = db_user['balance']
        
        if balance < purchase['price']:
            await update.message.reply_text(
                "❌ *Insufficient balance*\n\n"
                "Please add money to your wallet.",
                parse_mode=ParseMode.MARKDOWN
            )
            return ConversationHandler.END
        
        # Process purchase
        new_balance = balance - purchase['price']
        
        # Update balance
        success = await db_manager.update_balance(
            user.id,
            -purchase['price'],
            TRANSACTION_DEBIT,
            description=f"Purchased {purchase['card_name']} ₹{purchase['value']}"
        )
        
        if not success:
            await update.message.reply_text(
                "❌ *Transaction failed*\n\nPlease try again.",
                parse_mode=ParseMode.MARKDOWN
            )
            return ConversationHandler.END
        
        # Create purchase record
        order_id = await db_manager.create_purchase(
            user.id,
            purchase['card_name'],
            purchase['value'],
            purchase['price'],
            email
        )
        
        # Clear session
        session.pop('purchase', None)
        session_manager.update_session(user.id, session)
        
        # Send confirmation
        keyboard = [[InlineKeyboardButton("🏠 MAIN MENU", callback_data="main_menu")]]
        
        await update.message.reply_text(
            f"✅ *PURCHASE SUCCESSFUL!*\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"*{purchase['card_emoji']} {purchase['card_name']} ₹{purchase['value']}*\n"
            f"*Price:* {format_currency(purchase['price'])}\n"
            f"*Order ID:* `{order_id}`\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"📧 *Gift card sent to:*\n"
            f"`{email}`\n\n"
            f"📌 *IMPORTANT:*\n"
            f"• Check your inbox (and spam folder)\n"
            f"• Card arrives in 2-5 minutes\n"
            f"• Contact support if not received",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Random proof (70% chance)
        if random.random() < 0.7:
            try:
                # Cool names for proofs
                names = ["👑 Raj", "💫 Arjun", "🌟 Kavya", "⚡ Veer", "🔥 Aryan"]
                name = random.choice(names)
                
                proof_text = (
                    f"⚡ *NEW PURCHASE*\n\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"👤 *{name}* bought\n"
                    f"🎁 {purchase['card_emoji']} {purchase['card_name']} ₹{purchase['value']}\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"📧 *Delivery:* Email\n"
                    f"⚡ *Status:* Instant\n"
                    f"🕐 *Time:* {datetime.now().strftime('%I:%M %p')}"
                )
                
                await context.bot.send_message(
                    chat_id=PROOF_CHANNEL,
                    text=proof_text,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"❌ Proof send error: {e}")
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"❌ Email handler error: {e}")
        await update.message.reply_text(
            "⚠️ *Error*\n\nPlease try again.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END

# ==================== SUPPORT HANDLER ====================

async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle support message input"""
    try:
        user = update.effective_user
        message = update.message.text.strip()
        
        if len(message) < 10:
            await update.message.reply_text(
                "❌ *Message too short*\n\n"
                "Please describe your issue in detail (minimum 10 characters).",
                parse_mode=ParseMode.MARKDOWN
            )
            return TYPING_SUPPORT
        
        # Save support ticket
        await db_manager.execute_query(
            """INSERT INTO support_tickets 
               (user_id, message, status, timestamp)
               VALUES (?, ?, 'open', ?)""",
            (user.id, message, datetime.now().isoformat())
        )
        
        # Notify admin
        try:
            admin_msg = (
                f"🆘 *NEW SUPPORT TICKET*\n\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 *User:* {user.first_name}\n"
                f"🆔 *ID:* `{user.id}`\n"
                f"👤 *Username:* @{user.username}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💬 *Message:*\n{message}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"⏰ *Time:* {datetime.now().strftime('%d %b %Y, %I:%M %p')}"
            )
            
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_msg,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"❌ Admin notification error: {e}")
        
        # Confirm to user
        keyboard = [[InlineKeyboardButton("🏠 MAIN MENU", callback_data="main_menu")]]
        
        await update.message.reply_text(
            f"✅ *SUPPORT MESSAGE SENT!*\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"*Ticket ID:* `TKT{random.randint(10000, 99999)}`\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"Your issue has been recorded.\n"
            f"Our support team will contact you soon.\n\n"
            f"⏳ *Response time: 24 hours*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"❌ Support handler error: {e}")
        return ConversationHandler.END

# ==================== ADMIN CALLBACK HANDLER ====================

async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin callback queries"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    parts = data.split("_")
    
    if len(parts) < 2:
        await query.edit_message_caption("❌ Invalid data")
        return
    
    action = parts[0]
    
    if action == "approve" and len(parts) >= 2:
        try:
            verification_id = int(parts[1])
            
            # Approve payment
            success = await db_manager.approve_payment(verification_id, ADMIN_ID)
            
            if success:
                # Get verification details
                verifications = await db_manager.execute_query(
                    "SELECT * FROM pending_verifications WHERE id = ?",
                    (verification_id,)
                )
                
                if verifications:
                    v = verifications[0]
                    
                    # Notify user
                    try:
                        await context.bot.send_message(
                            chat_id=v['user_id'],
                            text=(
                                f"✅ *PAYMENT APPROVED!*\n\n"
                                f"━━━━━━━━━━━━━━━━━━\n"
                                f"*Amount:* {format_currency(v['final_amount'])} added\n"
                                f"*UTR:* `{v['utr']}`\n"
                                f"━━━━━━━━━━━━━━━━━━\n\n"
                                f"Thank you for using our service! 🙏"
                            ),
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except Exception as e:
                        logger.error(f"❌ User notification error: {e}")
                
                await query.edit_message_caption(
                    caption=query.message.caption + "\n\n✅ *APPROVED BY ADMIN*",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await query.edit_message_caption(
                    caption=query.message.caption + "\n\n❌ *APPROVAL FAILED*",
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"❌ Admin approve error: {e}")
            await query.edit_message_caption("❌ Error processing approval")
    
    elif action == "reject" and len(parts) >= 2:
        try:
            verification_id = int(parts[1])
            
            # Reject payment
            success = await db_manager.reject_payment(verification_id, ADMIN_ID)
            
            if success:
                # Get verification details
                verifications = await db_manager.execute_query(
                    "SELECT * FROM pending_verifications WHERE id = ?",
                    (verification_id,)
                )
                
                if verifications:
                    v = verifications[0]
                    
                    # Notify user
                    try:
                        await context.bot.send_message(
                            chat_id=v['user_id'],
                            text=(
                                f"❌ *PAYMENT REJECTED*\n\n"
                                f"━━━━━━━━━━━━━━━━━━\n"
                                f"*UTR:* `{v['utr']}`\n"
                                f"━━━━━━━━━━━━━━━━━━\n\n"
                                f"*Reason:* Payment not verified\n\n"
                                f"Please try again or contact support."
                            ),
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except Exception as e:
                        logger.error(f"❌ User notification error: {e}")
                
                await query.edit_message_caption(
                    caption=query.message.caption + "\n\n❌ *REJECTED BY ADMIN*",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await query.edit_message_caption(
                    caption=query.message.caption + "\n\n❌ *REJECTION FAILED*",
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"❌ Admin reject error: {e}")
            await query.edit_message_caption("❌ Error processing rejection")

# ==================== ADMIN COMMANDS ====================

@admin_only
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to view statistics"""
    try:
        stats = await db_manager.get_statistics()
        
        stats_text = (
            f"📊 *BOT STATISTICS*\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👥 *Total Users:* {stats['total_users']}\n"
            f"📱 *Active Today:* {stats['active_today']}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 *Total Revenue:* {format_currency(stats['total_revenue'])}\n"
            f"💳 *Total Spent:* {format_currency(stats['total_spent'])}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 *Transactions:* {stats['total_transactions']}\n"
            f"⏳ *Pending:* {stats['pending_verifications']}\n"
            f"🎫 *Open Tickets:* {stats['open_tickets']}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        
        await update.message.reply_text(
            stats_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"❌ Admin stats error: {e}")
        await update.message.reply_text("❌ Error fetching statistics")

@admin_only
async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to broadcast message to all users"""
    try:
        if not context.args:
            await update.message.reply_text(
                "📢 *BROADCAST*\n\n"
                "Usage: `/broadcast Your message here`\n\n"
                "Example: `/broadcast 🎉 New offer: 10% off!`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        message = " ".join(context.args)
        
        # Get all users
        users = await db_manager.execute_query("SELECT user_id FROM users")
        
        if not users:
            await update.message.reply_text("❌ No users found")
            return
        
        status_msg = await update.message.reply_text(
            f"📢 *Broadcasting to {len(users)} users...*",
            parse_mode=ParseMode.MARKDOWN
        )
        
        sent = 0
        failed = 0
        
        broadcast_text = (
            f"📢 *ADMIN BROADCAST*\n\n"
            f"{message}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"*GIFT CARD BOT*"
        )
        
        for user in users:
            try:
                await context.bot.send_message(
                    chat_id=user['user_id'],
                    text=broadcast_text,
                    parse_mode=ParseMode.MARKDOWN
                )
                sent += 1
                await asyncio.sleep(0.05)  # Rate limit
            except Exception as e:
                failed += 1
                logger.error(f"❌ Broadcast to {user['user_id']} failed: {e}")
            
            # Update status every 10 users
            if (sent + failed) % 10 == 0:
                await status_msg.edit_text(
                    f"📢 *Broadcasting...*\n\n"
                    f"✅ Sent: {sent}\n"
                    f"❌ Failed: {failed}\n"
                    f"📊 Total: {len(users)}",
                    parse_mode=ParseMode.MARKDOWN
                )
        
        await status_msg.edit_text(
            f"📢 *Broadcast Complete*\n\n"
            f"✅ Sent: {sent}\n"
            f"❌ Failed: {failed}\n"
            f"📊 Total: {len(users)}",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"❌ Broadcast error: {e}")
        await update.message.reply_text("❌ Broadcast failed")

@admin_only
async def admin_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to view pending verifications"""
    try:
        pending = await db_manager.get_pending_verifications()
        
        if not pending:
            await update.message.reply_text(
                "✅ *No pending verifications*",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        text = f"⏳ *PENDING VERIFICATIONS ({len(pending)})*\n\n"
        
        for p in pending[:10]:  # Show first 10
            user = await db_manager.get_user(p['user_id'])
            username = user['username'] if user else 'Unknown'
            
            text += (
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🆔 *ID:* `{p['id']}`\n"
                f"👤 *User:* @{username}\n"
                f"💰 *Amount:* {format_currency(p['amount'])}\n"
                f"🎁 *Credit:* {format_currency(p['final_amount'])}\n"
                f"🔢 *UTR:* `{p['utr']}`\n"
                f"⏰ *Time:* {format_datetime(p['timestamp'])}\n"
            )
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"❌ Admin pending error: {e}")
        await update.message.reply_text("❌ Error fetching pending verifications")

# ==================== AUTO PROOFS ====================

async def auto_proofs(context: ContextTypes.DEFAULT_TYPE):
    """Send random purchase proofs to proof channel"""
    try:
        # Cool names with emojis
        names = [
            "👑 Raj", "💫 Arjun", "🌟 Kavya", "⚡ Veer", "🔥 Aryan",
            "💎 Neha", "🎯 Karan", "🚀 Riya", "⭐ Amit", "💥 Priya",
            "🦁 Simba", "🐅 Tiger", "🦅 Falcon", "🐺 Wolf", "🦊 Fox",
            "💂 King", "👸 Queen", "🧙 Wizard", "🦸 Hero", "🦹 Storm",
            "👨‍💻 Dev", "👩‍🎨 Art", "👨‍🔧 Tech", "👩‍🔬 Sci", "👨‍🚀 Space"
        ]
        
        cards = [
            "🟦 AMAZON", "🟩 PLAY STORE", "🎟️ BOOKMYSHOW", 
            "🛍️ MYNTRA", "📦 FLIPKART", "🍕 ZOMATO", 
            "🛒 BIG BASKET", "🎮 GOOGLE PLAY", "🎬 NETFLIX", 
            "🎵 SPOTIFY", "💳 AMAZON PAY", "🏏 DREAM11",
            "🎁 GIFT VOUCHER", "🛍️ AJIO", "👕 MYNTRA",
            "📱 APPLE", "💻 DELL", "🎧 BOAT", "⌚ SAMSUNG"
        ]
        
        amounts = [500, 1000, 2000, 5000]
        
        name = random.choice(names)
        card = random.choice(cards)
        amount = random.choice(amounts)
        
        # Different message formats
        formats = [
            f"⚡ *NEW PURCHASE*\n\n━━━━━━━━━━━━━━━━━━\n✨ *{name}* just bought\n🎁 {card} *₹{amount}*\n━━━━━━━━━━━━━━━━━━\n📧 *Delivery:* Email (Instant)\n🕐 *Time:* {datetime.now().strftime('%I:%M %p')}",
            
            f"🎉 *FRESH ORDER*\n\n━━━━━━━━━━━━━━━━━━\n👤 *Buyer:* {name}\n💳 *Card:* {card}\n💰 *Value:* ₹{amount}\n━━━━━━━━━━━━━━━━━━\n📨 *Status:* Sent to Email\n✅ *Delivery:* Instant",
            
            f"🛒 *ORDER COMPLETED*\n\n━━━━━━━━━━━━━━━━━━\n👤 {name}\n🎁 {card}\n💵 ₹{amount}\n━━━━━━━━━━━━━━━━━━\n📧 *Email Delivery*\n⚡ *Instant*",
            
            f"⭐ *LIVE PURCHASE*\n\n━━━━━━━━━━━━━━━━━━\n🔹 *User:* {name}\n🔹 *Product:* {card}\n🔹 *Amount:* ₹{amount}\n━━━━━━━━━━━━━━━━━━\n🔹 *Time:* {datetime.now().strftime('%I:%M %p')}\n✅ *Success*",
            
            f"💫 *TRANSACTION ALERT*\n\n━━━━━━━━━━━━━━━━━━\n🏷️ *{name}*\n📦 *{card}*\n💵 ₹{amount}\n━━━━━━━━━━━━━━━━━━\n📧 *Email Delivery*\n✨ *Instant*",
            
            f"🌟 *NEW ORDER*\n\n━━━━━━━━━━━━━━━━━━\n👤 {name}\n🛍️ {card}\n💳 ₹{amount}\n━━━━━━━━━━━━━━━━━━\n✅ *Delivered via Email*\n⚡ *Instant*",
            
            f"🎯 *PURCHASE ALERT*\n\n━━━━━━━━━━━━━━━━━━\n👤 *Customer:* {name}\n🎁 *Item:* {card}\n💵 *Amount:* ₹{amount}\n━━━━━━━━━━━━━━━━━━\n📧 *Email:* Sent\n⚡ *Status:* Completed"
        ]
        
        message = random.choice(formats)
        
        await context.bot.send_message(
            chat_id=PROOF_CHANNEL,
            text=message,
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info("✅ Auto proof sent to channel")
        
    except Exception as e:
        logger.error(f"❌ Auto proof error: {e}")

# ==================== CLEANUP JOB ====================

async def cleanup_job(context: ContextTypes.DEFAULT_TYPE):
    """Periodic cleanup job"""
    try:
        # Clean up expired verifications
        await db_manager.cleanup_expired()
        
        # Clean up cache
        cache_manager.cleanup()
        
        # Clean up sessions
        session_manager.cleanup()
        
        logger.info("✅ Cleanup job completed")
        
    except Exception as e:
        logger.error(f"❌ Cleanup job error: {e}")

# ==================== CANCEL HANDLER ====================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current operation"""
    user = update.effective_user
    
    # Clear session
    session_manager.clear_session(user.id)
    
    keyboard = [[InlineKeyboardButton("🏠 MAIN MENU", callback_data="main_menu")]]
    
    await update.message.reply_text(
        "❌ *CANCELLED*\n\nOperation cancelled.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ConversationHandler.END

# ==================== ERROR HANDLER ====================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    try:
        raise context.error
    except RetryAfter as e:
        logger.warning(f"Rate limited: {e}")
        await asyncio.sleep(e.retry_after)
    except TimedOut:
        logger.error("Request timed out")
    except NetworkError:
        logger.error("Network error")
    except TelegramError as e:
        logger.error(f"Telegram error: {e}")
    except Exception as e:
        logger.error(f"Unhandled error: {e}")

# ==================== MAIN FUNCTION ====================

async def post_init(application: Application):
    """Setup after bot initialization"""
    # Set bot commands
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("cancel", "Cancel current operation"),
        BotCommand("stats", "Bot statistics (admin only)"),
        BotCommand("broadcast", "Broadcast message (admin only)"),
        BotCommand("pending", "View pending verifications (admin only)")
    ]
    
    await application.bot.set_my_commands(commands)
    
    # Initialize database
    await db_manager.initialize()
    
    logger.info("✅ Bot initialized successfully")

def main():
    """Main function"""
    try:
        # Create application
        app = Application.builder()\
            .token(BOT_TOKEN)\
            .post_init(post_init)\
            .build()
        
        # ===== COMMAND HANDLERS =====
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("cancel", cancel))
        app.add_handler(CommandHandler("stats", admin_stats))
        app.add_handler(CommandHandler("broadcast", admin_broadcast))
        app.add_handler(CommandHandler("pending", admin_pending))
        
        # ===== BUTTON HANDLER =====
        app.add_handler(CallbackQueryHandler(button_handler))
        
        # ===== ADMIN CALLBACK HANDLER =====
        app.add_handler(CallbackQueryHandler(admin_handler, pattern="^(approve_|reject_)"))
        
        # ===== AMOUNT CONVERSATION =====
        amount_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(button_handler, pattern="^upi$")],
            states={
                TYPING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)]
            },
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        app.add_handler(amount_conv)
        
        # ===== PAYMENT VERIFICATION CONVERSATION =====
        payment_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(button_handler, pattern="^paid$")],
            states={
                TYPING_SCREENSHOT: [
                    MessageHandler(filters.PHOTO, handle_screenshot),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_screenshot)
                ],
                TYPING_UTR: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_utr)
                ]
            },
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        app.add_handler(payment_conv)
        
        # ===== EMAIL CONVERSATION =====
        email_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(button_handler, pattern="^buy_")],
            states={
                TYPING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email)]
            },
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        app.add_handler(email_conv)
        
        # ===== SUPPORT CONVERSATION =====
        support_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(button_handler, pattern="^support$")],
            states={
                TYPING_SUPPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_support)]
            },
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        app.add_handler(support_conv)
        
        # ===== ERROR HANDLER =====
        app.add_error_handler(error_handler)
        
        # ===== JOB QUEUE =====
        if app.job_queue:
            # Auto proofs every 45 seconds (random between 30-60)
            interval = random.randint(30, 60)
            app.job_queue.run_repeating(auto_proofs, interval=interval, first=10)
            
            # Cleanup every hour
            app.job_queue.run_repeating(cleanup_job, interval=3600, first=60)
        
        # ===== START BOT =====
        logger.info("🚀 Starting bot...")
        
        print("\n" + "="*60)
        print("      🤖 GIFT CARD BOT - V2.0.0")
        print("="*60)
        print(f"📢 Main Channel: @gift_card_main")
        print(f"📊 Proof Channel: @gift_card_log")
        print(f"👑 Admin ID: {ADMIN_ID}")
        print(f"💳 UPI ID: {UPI_ID}")
        print(f"📁 Database: {DATABASE_PATH}")
        print("="*60)
        print(f"✅ Bot is running...")
        print("="*60 + "\n")
        
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.critical(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
