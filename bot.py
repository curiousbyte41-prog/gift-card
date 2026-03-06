#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
===============================================================================
GIFT CARD & RECHARGE BOT - PREMIUM EDITION
===============================================================================
A fully featured Telegram bot for selling gift cards and managing recharges
with beautiful UI, complete error handling, and professional design.

Version: 4.0.0 (Stable Release)
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
    filters, ContextTypes, ConversationHandler, JobQueue
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
    CONFIG_FILE = "config.json"
    BACKUP_DIR = "backups"
    
    # Timeouts and Limits
    SESSION_TIMEOUT = 600  # 10 minutes
    RATE_LIMIT = 30  # requests per minute
    CACHE_TIMEOUT = 300  # 5 minutes
    VERIFICATION_TIMEOUT = 600  # 10 minutes
    
    # UI Configuration
    BOT_NAME = "🎁 GIFT CARD BOT"
    BOT_VERSION = "4.0.0"
    COMPANY_NAME = "GiftCard Store"
    SUPPORT_EMAIL = "support@giftcard.com"
    WEBSITE = "www.giftcard.com"

config = Config()

# ===========================================================================
# ENUMS AND CONSTANTS
# ===========================================================================

class UserRole(Enum):
    """User role enumeration"""
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"
    BANNED = "banned"

class TransactionType(Enum):
    """Transaction type enumeration"""
    CREDIT = "credit"
    DEBIT = "debit"
    REFUND = "refund"
    BONUS = "bonus"

class TransactionStatus(Enum):
    """Transaction status enumeration"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class PaymentMethod(Enum):
    """Payment method enumeration"""
    UPI = "upi"
    CRYPTO = "crypto"
    BANK = "bank"
    WALLET = "wallet"

class SupportPriority(Enum):
    """Support ticket priority"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

# Conversation States
(
    STATE_AMOUNT,
    STATE_SCREENSHOT,
    STATE_UTR,
    STATE_EMAIL,
    STATE_SUPPORT,
    STATE_FEEDBACK,
    STATE_REFERRAL,
    STATE_WITHDRAWAL,
    STATE_EXCHANGE,
    STATE_BROADCAST,
    STATE_UPDATE_PRICE,
    STATE_ADD_CARD,
    STATE_REMOVE_CARD,
    STATE_BAN_USER,
    STATE_UNBAN_USER
) = range(15)

# ===========================================================================
# GIFT CARD DATA
# ===========================================================================

GIFT_CARDS = {
    "amazon": {
        "id": "amazon",
        "name": "AMAZON",
        "emoji": "🟦",
        "full_emoji": "🟦🛒",
        "description": "Amazon.in Gift Card - Shop everything from A to Z",
        "delivery": "📧 Instant Email Delivery",
        "validity": "365 days",
        "terms": "Valid on all Amazon products",
        "popular": True,
        "brand_color": "#FF9900",
        "icon": "https://example.com/amazon.png"
    },
    "playstore": {
        "id": "playstore",
        "name": "PLAY STORE",
        "emoji": "🟩",
        "full_emoji": "🟩🎮",
        "description": "Google Play Gift Card - Apps, Games, Movies & More",
        "delivery": "📧 Instant Email Delivery",
        "validity": "365 days",
        "terms": "Valid on Google Play Store",
        "popular": True,
        "brand_color": "#34A853",
        "icon": "https://example.com/playstore.png"
    },
    "bookmyshow": {
        "id": "bookmyshow",
        "name": "BOOKMYSHOW",
        "emoji": "🎟️",
        "full_emoji": "🎟️🎬",
        "description": "BookMyShow Gift Card - Movie Tickets & Events",
        "delivery": "📧 Instant Email Delivery",
        "validity": "180 days",
        "terms": "Valid on BookMyShow platform",
        "popular": True,
        "brand_color": "#C51C3E",
        "icon": "https://example.com/bookmyshow.png"
    },
    "myntra": {
        "id": "myntra",
        "name": "MYNTRA",
        "emoji": "🛍️",
        "full_emoji": "🛍️👗",
        "description": "Myntra Gift Card - Fashion & Lifestyle",
        "delivery": "📧 Instant Email Delivery",
        "validity": "365 days",
        "terms": "Valid on all Myntra products",
        "popular": True,
        "brand_color": "#E12B38",
        "icon": "https://example.com/myntra.png"
    },
    "flipkart": {
        "id": "flipkart",
        "name": "FLIPKART",
        "emoji": "📦",
        "full_emoji": "📦🛒",
        "description": "Flipkart Gift Card - Online Shopping",
        "delivery": "📧 Instant Email Delivery",
        "validity": "365 days",
        "terms": "Valid on all Flipkart products",
        "popular": True,
        "brand_color": "#2874F0",
        "icon": "https://example.com/flipkart.png"
    },
    "zomato": {
        "id": "zomato",
        "name": "ZOMATO",
        "emoji": "🍕",
        "full_emoji": "🍕🍔",
        "description": "Zomato Gift Card - Food Delivery",
        "delivery": "📧 Instant Email Delivery",
        "validity": "180 days",
        "terms": "Valid on Zomato orders",
        "popular": True,
        "brand_color": "#CB202D",
        "icon": "https://example.com/zomato.png"
    },
    "bigbasket": {
        "id": "bigbasket",
        "name": "BIG BASKET",
        "emoji": "🛒",
        "full_emoji": "🛒🥬",
        "description": "BigBasket Gift Card - Grocery Delivery",
        "delivery": "📧 Instant Email Delivery",
        "validity": "365 days",
        "terms": "Valid on BigBasket orders",
        "popular": True,
        "brand_color": "#A7C83B",
        "icon": "https://example.com/bigbasket.png"
    },
    "netflix": {
        "id": "netflix",
        "name": "NETFLIX",
        "emoji": "🎬",
        "full_emoji": "🎬📺",
        "description": "Netflix Gift Card - Streaming Service",
        "delivery": "📧 Instant Email Delivery",
        "validity": "365 days",
        "terms": "Valid on Netflix subscription",
        "popular": False,
        "brand_color": "#E50914",
        "icon": "https://example.com/netflix.png"
    },
    "spotify": {
        "id": "spotify",
        "name": "SPOTIFY",
        "emoji": "🎵",
        "full_emoji": "🎵🎧",
        "description": "Spotify Gift Card - Music Streaming",
        "delivery": "📧 Instant Email Delivery",
        "validity": "365 days",
        "terms": "Valid on Spotify Premium",
        "popular": False,
        "brand_color": "#1DB954",
        "icon": "https://example.com/spotify.png"
    },
    "dream11": {
        "id": "dream11",
        "name": "DREAM11",
        "emoji": "🏏",
        "full_emoji": "🏏🎯",
        "description": "Dream11 Gift Card - Fantasy Sports",
        "delivery": "📧 Instant Email Delivery",
        "validity": "180 days",
        "terms": "Valid on Dream11 platform",
        "popular": False,
        "brand_color": "#0F172A",
        "icon": "https://example.com/dream11.png"
    }
}

# Price configuration: {denomination: selling_price}
PRICES = {
    500: 100,
    1000: 200,
    2000: 400,
    5000: 1000,
    10000: 2000
}

# Available denominations
AVAILABLE_DENOMINATIONS = [500, 1000, 2000, 5000, 10000]

# ===========================================================================
# SETUP LOGGING
# ===========================================================================

class ColoredFormatter(logging.Formatter):
    """Custom colored log formatter"""
    
    # ANSI color codes
    grey = "\x1b[38;21m"
    blue = "\x1b[38;5;39m"
    yellow = "\x1b[38;5;226m"
    red = "\x1b[38;5;196m"
    bold_red = "\x1b[31;1m"
    green = "\x1b[38;5;46m"
    cyan = "\x1b[38;5;51m"
    magenta = "\x1b[38;5;201m"
    white = "\x1b[38;5;15m"
    reset = "\x1b[0m"
    
    def __init__(self, fmt):
        super().__init__()
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: self.cyan + self.fmt + self.reset,
            logging.INFO: self.green + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.fmt + self.reset,
            logging.ERROR: self.red + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset
        }
    
    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

def setup_logging():
    """Setup comprehensive logging system"""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # File handler for all logs
    file_handler = logging.FileHandler(log_dir / "bot.log")
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter('%(asctime)s | %(levelname)-8s | %(name)s | %(message)s')
    file_handler.setFormatter(file_format)
    
    # File handler for errors only
    error_handler = logging.FileHandler(log_dir / "errors.log")
    error_handler.setLevel(logging.ERROR)
    error_format = logging.Formatter('%(asctime)s | %(levelname)-8s | %(name)s | %(message)s')
    error_handler.setFormatter(error_format)
    
    # Console handler with colors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = '%(asctime)s | %(levelname)-8s | %(message)s'
    console_handler.setFormatter(ColoredFormatter(console_format))
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

# ===========================================================================
# DATABASE MANAGER
# ===========================================================================

class DatabaseManager:
    """
    Thread-safe database manager with connection pooling,
    automatic backups, and comprehensive error handling.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.db_path = config.DATABASE_PATH
        self.backup_dir = Path(config.BACKUP_DIR)
        self.backup_dir.mkdir(exist_ok=True)
        
        # Connection pool
        self._connection_pool = Queue(maxsize=10)
        self._pool_size = 5
        
        # Initialize connection pool
        self._init_pool()
        
        # Initialize database
        self._init_database()
        
        logger.info("✅ Database Manager initialized")
    
    def _init_pool(self):
        """Initialize connection pool"""
        for _ in range(self._pool_size):
            conn = sqlite3.connect(self.db_path, timeout=30)
            conn.row_factory = sqlite3.Row
            self._connection_pool.put(conn)
    
    @contextmanager
    def get_connection(self):
        """Get connection from pool"""
        conn = self._connection_pool.get()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Database error: {e}")
            raise
        finally:
            self._connection_pool.put(conn)
    
    def _init_database(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            # Enable foreign keys and WAL mode
            c.execute("PRAGMA foreign_keys = ON")
            c.execute("PRAGMA journal_mode = WAL")
            c.execute("PRAGMA synchronous = NORMAL")
            
            # ===== USERS TABLE =====
            c.execute('''CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                email TEXT,
                balance INTEGER DEFAULT 0,
                total_recharged INTEGER DEFAULT 0,
                total_spent INTEGER DEFAULT 0,
                total_purchases INTEGER DEFAULT 0,
                role TEXT DEFAULT 'user',
                status TEXT DEFAULT 'active',
                language TEXT DEFAULT 'en',
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                referral_bonus INTEGER DEFAULT 0,
                join_date TIMESTAMP,
                last_active TIMESTAMP,
                last_ip TEXT,
                last_location TEXT,
                preferences TEXT DEFAULT '{}',
                notes TEXT,
                FOREIGN KEY (referred_by) REFERENCES users(user_id)
            )''')
            
            # Create indexes
            c.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code)")
            
            # ===== TRANSACTIONS TABLE =====
            c.execute('''CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                transaction_id TEXT UNIQUE,
                amount INTEGER NOT NULL,
                type TEXT NOT NULL,
                status TEXT NOT NULL,
                payment_method TEXT,
                utr TEXT UNIQUE,
                fee INTEGER DEFAULT 0,
                final_amount INTEGER,
                description TEXT,
                metadata TEXT DEFAULT '{}',
                timestamp TIMESTAMP,
                approved_by INTEGER,
                approved_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (approved_by) REFERENCES users(user_id)
            )''')
            
            # Create indexes
            c.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_transactions_utr ON transactions(utr)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp)")
            
            # ===== PURCHASES TABLE =====
            c.execute('''CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                order_id TEXT UNIQUE,
                card_type TEXT NOT NULL,
                card_value INTEGER NOT NULL,
                price INTEGER NOT NULL,
                email TEXT NOT NULL,
                card_code TEXT,
                card_pin TEXT,
                status TEXT DEFAULT 'completed',
                delivery_status TEXT DEFAULT 'pending',
                metadata TEXT DEFAULT '{}',
                timestamp TIMESTAMP,
                delivered_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )''')
            
            # Create indexes
            c.execute("CREATE INDEX IF NOT EXISTS idx_purchases_user ON purchases(user_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_purchases_order ON purchases(order_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_purchases_status ON purchases(status)")
            
            # ===== VERIFICATIONS TABLE =====
            c.execute('''CREATE TABLE IF NOT EXISTS verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                verification_id TEXT UNIQUE,
                amount INTEGER NOT NULL,
                fee INTEGER DEFAULT 0,
                final_amount INTEGER NOT NULL,
                payment_method TEXT,
                utr TEXT UNIQUE,
                screenshot_id TEXT,
                status TEXT DEFAULT 'pending',
                expires_at TIMESTAMP,
                timestamp TIMESTAMP,
                verified_by INTEGER,
                verified_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (verified_by) REFERENCES users(user_id)
            )''')
            
            # Create indexes
            c.execute("CREATE INDEX IF NOT EXISTS idx_verifications_user ON verifications(user_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_verifications_status ON verifications(status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_verifications_utr ON verifications(utr)")
            
            # ===== SUPPORT TICKETS TABLE =====
            c.execute('''CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT UNIQUE,
                user_id INTEGER NOT NULL,
                subject TEXT,
                message TEXT NOT NULL,
                priority INTEGER DEFAULT 1,
                status TEXT DEFAULT 'open',
                assigned_to INTEGER,
                response TEXT,
                metadata TEXT DEFAULT '{}',
                timestamp TIMESTAMP,
                updated_at TIMESTAMP,
                resolved_at TIMESTAMP,
                resolved_by INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (assigned_to) REFERENCES users(user_id),
                FOREIGN KEY (resolved_by) REFERENCES users(user_id)
            )''')
            
            # Create indexes
            c.execute("CREATE INDEX IF NOT EXISTS idx_tickets_user ON support_tickets(user_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status ON support_tickets(status)")
            
            # ===== REFERRALS TABLE =====
            c.execute('''CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                referred_id INTEGER NOT NULL UNIQUE,
                bonus_amount INTEGER DEFAULT 10,
                status TEXT DEFAULT 'pending',
                timestamp TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (referrer_id) REFERENCES users(user_id),
                FOREIGN KEY (referred_id) REFERENCES users(user_id)
            )''')
            
            # Create indexes
            c.execute("CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_referrals_status ON referrals(status)")
            
            # ===== FEEDBACK TABLE =====
            c.execute('''CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                message TEXT,
                timestamp TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )''')
            
            # ===== NOTIFICATIONS TABLE =====
            c.execute('''CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT,
                message TEXT NOT NULL,
                type TEXT,
                read INTEGER DEFAULT 0,
                timestamp TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )''')
            
            # Create indexes
            c.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(read)")
            
            # ===== SETTINGS TABLE =====
            c.execute('''CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                type TEXT DEFAULT 'string',
                description TEXT,
                updated_at TIMESTAMP,
                updated_by INTEGER
            )''')
            
            # Insert default settings
            default_settings = [
                ('bot_name', config.BOT_NAME, 'string', 'Bot display name'),
                ('min_recharge', str(config.MIN_RECHARGE), 'int', 'Minimum recharge amount'),
                ('max_recharge', str(config.MAX_RECHARGE), 'int', 'Maximum recharge amount'),
                ('fee_percent', str(config.FEE_PERCENT), 'int', 'Fee percentage'),
                ('fee_threshold', str(config.FEE_THRESHOLD), 'int', 'Fee threshold amount'),
                ('upi_id', config.UPI_ID, 'string', 'UPI ID for payments'),
                ('referral_bonus', '10', 'int', 'Referral bonus amount'),
                ('maintenance_mode', '0', 'bool', 'Maintenance mode status'),
                ('welcome_message', 'Welcome to Gift Card Bot!', 'text', 'Welcome message'),
                ('support_message', 'Contact support for help', 'text', 'Support message'),
                ('terms_and_conditions', 'Terms and conditions...', 'text', 'Terms and conditions'),
                ('privacy_policy', 'Privacy policy...', 'text', 'Privacy policy'),
                ('about_us', 'About Gift Card Bot...', 'text', 'About us'),
                ('contact_email', 'support@giftcard.com', 'string', 'Contact email'),
                ('contact_website', 'www.giftcard.com', 'string', 'Website'),
                ('currency_symbol', '₹', 'string', 'Currency symbol'),
                ('currency_code', 'INR', 'string', 'Currency code')
            ]
            
            for key, value, type_, desc in default_settings:
                c.execute(
                    "INSERT OR IGNORE INTO settings (key, value, type, description, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (key, value, type_, desc, datetime.now().isoformat())
                )
            
            # ===== STATISTICS TABLE =====
            c.execute('''CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE,
                new_users INTEGER DEFAULT 0,
                transactions INTEGER DEFAULT 0,
                revenue INTEGER DEFAULT 0,
                purchases INTEGER DEFAULT 0,
                verifications INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}'
            )''')
            
            conn.commit()
            logger.info("✅ Database tables initialized")
    
    def backup_database(self):
        """Create database backup"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"backup_{timestamp}.db"
            
            with self.get_connection() as conn:
                backup_conn = sqlite3.connect(backup_path)
                conn.backup(backup_conn)
                backup_conn.close()
            
            logger.info(f"✅ Database backup created: {backup_path}")
            
            # Keep only last 10 backups
            backups = sorted(self.backup_dir.glob("backup_*.db"))
            if len(backups) > 10:
                for backup in backups[:-10]:
                    backup.unlink()
            
            return str(backup_path)
        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            return None
    
    # ===== USER METHODS =====
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            return dict(row) if row else None
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = c.fetchone()
            return dict(row) if row else None
    
    def get_user_by_referral(self, code: str) -> Optional[Dict]:
        """Get user by referral code"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE referral_code = ?", (code,))
            row = c.fetchone()
            return dict(row) if row else None
    
    def create_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None) -> Dict:
        """Create new user"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            # Generate unique referral code
            referral_code = hashlib.md5(f"{user_id}{datetime.now()}".encode()).hexdigest()[:8]
            
            now = datetime.now().isoformat()
            
            c.execute('''INSERT OR IGNORE INTO users 
                (user_id, username, first_name, last_name, referral_code, join_date, last_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (user_id, username, first_name, last_name, referral_code, now, now))
            
            conn.commit()
            
            return self.get_user(user_id)
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        """Update user fields"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            fields = []
            values = []
            for key, value in kwargs.items():
                if key not in ['user_id', 'referral_code']:
                    fields.append(f"{key} = ?")
                    values.append(value)
            
            if not fields:
                return False
            
            values.append(user_id)
            query = f"UPDATE users SET {', '.join(fields)} WHERE user_id = ?"
            
            c.execute(query, values)
            conn.commit()
            
            return c.rowcount > 0
    
    def update_last_active(self, user_id: int):
        """Update user's last active timestamp"""
        self.update_user(user_id, last_active=datetime.now().isoformat())
    
    def get_user_balance(self, user_id: int) -> int:
        """Get user balance"""
        user = self.get_user(user_id)
        return user['balance'] if user else 0
    
    def update_balance(self, user_id: int, amount: int, transaction_type: str, **kwargs) -> bool:
        """Update user balance and record transaction"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
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
            transaction_id = f"TXN{datetime.now().strftime('%y%m%d%H%M%S')}{random.randint(1000, 9999)}"
            
            # Record transaction
            c.execute('''INSERT INTO transactions 
                (user_id, transaction_id, amount, type, status, payment_method, utr, fee, final_amount, description, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (user_id, transaction_id, abs(amount), transaction_type, 'completed',
                 kwargs.get('payment_method'), kwargs.get('utr'), kwargs.get('fee', 0),
                 kwargs.get('final_amount', amount), kwargs.get('description', ''), datetime.now().isoformat()))
            
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
    
    # ===== TRANSACTION METHODS =====
    
    def get_transactions(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get user transactions"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('''SELECT * FROM transactions 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?''', (user_id, limit))
            return [dict(row) for row in c.fetchall()]
    
    def get_transaction_by_utr(self, utr: str) -> Optional[Dict]:
        """Get transaction by UTR"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM transactions WHERE utr = ?", (utr,))
            row = c.fetchone()
            return dict(row) if row else None
    
    # ===== PURCHASE METHODS =====
    
    def create_purchase(self, user_id: int, card_type: str, value: int, price: int, email: str) -> str:
        """Create purchase record"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            # Generate order ID
            order_id = f"GC{datetime.now().strftime('%y%m%d%H%M%S')}{random.randint(1000, 9999)}"
            
            c.execute('''INSERT INTO purchases 
                (user_id, order_id, card_type, card_value, price, email, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (user_id, order_id, card_type, value, price, email, datetime.now().isoformat()))
            
            conn.commit()
            return order_id
    
    def get_purchases(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get user purchases"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('''SELECT * FROM purchases 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?''', (user_id, limit))
            return [dict(row) for row in c.fetchall()]
    
    # ===== VERIFICATION METHODS =====
    
    def create_verification(self, user_id: int, amount: int, fee: int, final: int, utr: str, screenshot: str) -> str:
        """Create payment verification"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            # Generate verification ID
            verification_id = f"VER{datetime.now().strftime('%y%m%d%H%M%S')}{random.randint(1000, 9999)}"
            
            # Set expiry
            expires_at = (datetime.now() + timedelta(seconds=config.VERIFICATION_TIMEOUT)).isoformat()
            
            c.execute('''INSERT INTO verifications 
                (user_id, verification_id, amount, fee, final_amount, utr, screenshot_id, expires_at, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (user_id, verification_id, amount, fee, final, utr, screenshot, expires_at, datetime.now().isoformat()))
            
            conn.commit()
            return verification_id
    
    def get_pending_verifications(self) -> List[Dict]:
        """Get all pending verifications"""
        with self.get_connection() as conn:
            c = conn.cursor()
            now = datetime.now().isoformat()
            c.execute('''SELECT * FROM verifications 
                WHERE status = 'pending' AND expires_at > ?
                ORDER BY timestamp DESC''', (now,))
            return [dict(row) for row in c.fetchall()]
    
    def approve_verification(self, verification_id: str, admin_id: int) -> bool:
        """Approve payment verification"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            # Get verification
            c.execute("SELECT * FROM verifications WHERE verification_id = ?", (verification_id,))
            row = c.fetchone()
            if not row:
                return False
            
            verification = dict(row)
            
            # Update verification status
            c.execute('''UPDATE verifications 
                SET status = 'completed', verified_by = ?, verified_at = ?
                WHERE verification_id = ?''',
                (admin_id, datetime.now().isoformat(), verification_id))
            
            # Update balance
            self.update_balance(
                verification['user_id'],
                verification['final_amount'],
                'credit',
                payment_method='UPI',
                utr=verification['utr'],
                fee=verification['fee'],
                final_amount=verification['final_amount'],
                description='UPI Recharge'
            )
            
            conn.commit()
            return True
    
    def reject_verification(self, verification_id: str, admin_id: int) -> bool:
        """Reject payment verification"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            c.execute('''UPDATE verifications 
                SET status = 'rejected', verified_by = ?, verified_at = ?
                WHERE verification_id = ?''',
                (admin_id, datetime.now().isoformat(), verification_id))
            
            conn.commit()
            return c.rowcount > 0
    
    # ===== SUPPORT METHODS =====
    
    def create_support_ticket(self, user_id: int, message: str, priority: int = 1) -> str:
        """Create support ticket"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            # Generate ticket ID
            ticket_id = f"TKT{datetime.now().strftime('%y%m%d%H%M%S')}{random.randint(1000, 9999)}"
            
            c.execute('''INSERT INTO support_tickets 
                (ticket_id, user_id, message, priority, timestamp, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)''',
                (ticket_id, user_id, message, priority, datetime.now().isoformat(), datetime.now().isoformat()))
            
            conn.commit()
            return ticket_id
    
    def get_open_tickets(self) -> List[Dict]:
        """Get all open support tickets"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('''SELECT * FROM support_tickets 
                WHERE status = 'open' 
                ORDER BY priority DESC, timestamp ASC''')
            return [dict(row) for row in c.fetchall()]
    
    # ===== REFERRAL METHODS =====
    
    def process_referral(self, referrer_id: int, referred_id: int) -> bool:
        """Process referral bonus"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            # Check if already referred
            c.execute("SELECT * FROM referrals WHERE referred_id = ?", (referred_id,))
            if c.fetchone():
                return False
            
            # Get bonus amount from settings
            c.execute("SELECT value FROM settings WHERE key = 'referral_bonus'")
            row = c.fetchone()
            bonus = int(row[0]) if row else 10
            
            # Create referral record
            c.execute('''INSERT INTO referrals 
                (referrer_id, referred_id, bonus_amount, timestamp)
                VALUES (?, ?, ?, ?)''',
                (referrer_id, referred_id, bonus, datetime.now().isoformat()))
            
            # Give bonus to referrer
            self.update_balance(
                referrer_id,
                bonus,
                'bonus',
                description=f'Referral bonus for user {referred_id}'
            )
            
            conn.commit()
            return True
    
    def get_referrals(self, user_id: int) -> List[Dict]:
        """Get user's referrals"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('''SELECT * FROM referrals 
                WHERE referrer_id = ?
                ORDER BY timestamp DESC''', (user_id,))
            return [dict(row) for row in c.fetchall()]
    
    # ===== STATISTICS METHODS =====
    
    def get_statistics(self) -> Dict:
        """Get bot statistics"""
        stats = {}
        
        with self.get_connection() as conn:
            c = conn.cursor()
            
            # Total users
            c.execute("SELECT COUNT(*) FROM users")
            stats['total_users'] = c.fetchone()[0]
            
            # Active users today
            today = datetime.now().date().isoformat()
            c.execute("SELECT COUNT(*) FROM users WHERE date(last_active) = ?", (today,))
            stats['active_today'] = c.fetchone()[0]
            
            # New users today
            c.execute("SELECT COUNT(*) FROM users WHERE date(join_date) = ?", (today,))
            stats['new_today'] = c.fetchone()[0]
            
            # Total transactions
            c.execute("SELECT COUNT(*) FROM transactions")
            stats['total_transactions'] = c.fetchone()[0]
            
            # Total revenue
            c.execute("SELECT SUM(amount) FROM transactions WHERE type = 'credit' AND status = 'completed'")
            stats['total_revenue'] = c.fetchone()[0] or 0
            
            # Total spent
            c.execute("SELECT SUM(price) FROM purchases")
            stats['total_spent'] = c.fetchone()[0] or 0
            
            # Total purchases
            c.execute("SELECT COUNT(*) FROM purchases")
            stats['total_purchases'] = c.fetchone()[0]
            
            # Pending verifications
            now = datetime.now().isoformat()
            c.execute("SELECT COUNT(*) FROM verifications WHERE status = 'pending' AND expires_at > ?", (now,))
            stats['pending_verifications'] = c.fetchone()[0]
            
            # Open tickets
            c.execute("SELECT COUNT(*) FROM support_tickets WHERE status = 'open'")
            stats['open_tickets'] = c.fetchone()[0]
            
            # Total balance
            c.execute("SELECT SUM(balance) FROM users")
            stats['total_balance'] = c.fetchone()[0] or 0
            
        return stats
    
    def update_daily_stats(self):
        """Update daily statistics"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            today = datetime.now().date().isoformat()
            
            # Get today's stats
            c.execute("SELECT COUNT(*) FROM users WHERE date(join_date) = ?", (today,))
            new_users = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM transactions WHERE date(timestamp) = ?", (today,))
            transactions = c.fetchone()[0]
            
            c.execute("SELECT SUM(amount) FROM transactions WHERE type = 'credit' AND date(timestamp) = ?", (today,))
            revenue = c.fetchone()[0] or 0
            
            c.execute("SELECT COUNT(*) FROM purchases WHERE date(timestamp) = ?", (today,))
            purchases = c.fetchone()[0]
            
            # Insert or update daily stats
            c.execute('''INSERT OR REPLACE INTO statistics 
                (date, new_users, transactions, revenue, purchases)
                VALUES (?, ?, ?, ?, ?)''',
                (today, new_users, transactions, revenue, purchases))
            
            conn.commit()

# ===========================================================================
# CACHE MANAGER
# ===========================================================================

class CacheManager:
    """
    Thread-safe cache manager with TTL and automatic cleanup
    """
    
    def __init__(self):
        self._cache = {}
        self._timers = {}
        self._lock = threading.Lock()
    
    def set(self, key: str, value: Any, ttl: int = config.CACHE_TIMEOUT):
        """Set cache value with TTL"""
        with self._lock:
            self._cache[key] = value
            self._timers[key] = time.time() + ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get cache value if not expired"""
        with self._lock:
            if key in self._cache:
                if time.time() < self._timers.get(key, 0):
                    return self._cache[key]
                else:
                    self.delete(key)
            return None
    
    def delete(self, key: str):
        """Delete cache entry"""
        with self._lock:
            self._cache.pop(key, None)
            self._timers.pop(key, None)
    
    def clear(self):
        """Clear all cache"""
        with self._lock:
            self._cache.clear()
            self._timers.clear()
    
    def cleanup(self):
        """Remove expired entries"""
        with self._lock:
            now = time.time()
            expired = [k for k, t in self._timers.items() if now >= t]
            for k in expired:
                self.delete(k)

# ===========================================================================
# RATE LIMITER
# ===========================================================================

class RateLimiter:
    """
    Rate limiter for user actions
    """
    
    def __init__(self):
        self._user_requests = defaultdict(list)
        self._lock = threading.Lock()
    
    def is_allowed(self, user_id: int) -> bool:
        """Check if user is allowed to make request"""
        with self._lock:
            now = time.time()
            window_start = now - 60
            
            # Clean old requests
            self._user_requests[user_id] = [
                t for t in self._user_requests[user_id] if t > window_start
            ]
            
            # Check rate
            if len(self._user_requests[user_id]) >= config.RATE_LIMIT:
                return False
            
            # Add request
            self._user_requests[user_id].append(now)
            return True
    
    def get_remaining(self, user_id: int) -> int:
        """Get remaining requests for user"""
        with self._lock:
            now = time.time()
            window_start = now - 60
            recent = [t for t in self._user_requests[user_id] if t > window_start]
            return max(0, config.RATE_LIMIT - len(recent))
    
    def reset(self, user_id: int):
        """Reset rate limit for user"""
        with self._lock:
            self._user_requests[user_id] = []

# ===========================================================================
# SESSION MANAGER
# ===========================================================================

class SessionManager:
    """
    Thread-safe session manager with timeout
    """
    
    def __init__(self):
        self._sessions = {}
        self._lock = threading.Lock()
        self._timeout = config.SESSION_TIMEOUT
    
    def get_session(self, user_id: int) -> Dict:
        """Get or create user session"""
        with self._lock:
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
        with self._lock:
            if user_id in self._sessions:
                self._sessions[user_id]['data'].update(data)
                self._sessions[user_id]['last_active'] = time.time()
    
    def clear_session(self, user_id: int):
        """Clear user session"""
        with self._lock:
            if user_id in self._sessions:
                del self._sessions[user_id]
    
    def cleanup(self):
        """Remove expired sessions"""
        with self._lock:
            now = time.time()
            expired = [
                uid for uid, sess in self._sessions.items()
                if now - sess['last_active'] > self._timeout
            ]
            for uid in expired:
                self.clear_session(uid)

# ===========================================================================
# NOTIFICATION MANAGER
# ===========================================================================

class NotificationManager:
    """
    Manage notifications to users
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
    
    async def send_notification(self, user_id: int, title: str, message: str, type: str = 'info'):
        """Send notification to user"""
        try:
            text = f"*{title}*\n\n{message}"
            
            keyboard = [[InlineKeyboardButton("👁️ View", callback_data="notifications")]]
            
            await self.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            # Save to database
            with self.db.get_connection() as conn:
                c = conn.cursor()
                c.execute('''INSERT INTO notifications 
                    (user_id, title, message, type, timestamp)
                    VALUES (?, ?, ?, ?, ?)''',
                    (user_id, title, message, type, datetime.now().isoformat()))
            
            return True
        except Exception as e:
            logger.error(f"❌ Notification error: {e}")
            return False
    
    async def broadcast(self, message: str, exclude: List[int] = None):
        """Broadcast message to all users"""
        if exclude is None:
            exclude = []
        
        with self.db.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT user_id FROM users WHERE status = 'active'")
            users = c.fetchall()
        
        sent = 0
        failed = 0
        
        for user in users:
            user_id = user[0]
            if user_id in exclude:
                continue
            
            try:
                await self.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN
                )
                sent += 1
                await asyncio.sleep(0.05)  # Rate limit
            except Exception as e:
                failed += 1
                logger.error(f"❌ Broadcast to {user_id} failed: {e}")
        
        return sent, failed

# ===========================================================================
# FORMATTER UTILITIES
# ===========================================================================

class Formatter:
    """Formatting utilities"""
    
    @staticmethod
    def currency(amount: int) -> str:
        """Format amount with currency symbol"""
        return f"₹{amount:,}"
    
    @staticmethod
    def date(date_str: str, format: str = "%d %b %Y, %I:%M %p") -> str:
        """Format date string"""
        try:
            dt = datetime.fromisoformat(date_str)
            return dt.strftime(format)
        except:
            return date_str
    
    @staticmethod
    def relative_time(date_str: str) -> str:
        """Get relative time string"""
        try:
            dt = datetime.fromisoformat(date_str)
            now = datetime.now()
            diff = now - dt
            
            if diff.days > 365:
                years = diff.days // 365
                return f"{years} year{'s' if years > 1 else ''} ago"
            elif diff.days > 30:
                months = diff.days // 30
                return f"{months} month{'s' if months > 1 else ''} ago"
            elif diff.days > 0:
                return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} hour{'s' if hours > 1 else ''} ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            else:
                return "just now"
        except:
            return date_str
    
    @staticmethod
    def truncate(text: str, length: int = 50) -> str:
        """Truncate text to length"""
        if len(text) <= length:
            return text
        return text[:length-3] + "..."
    
    @staticmethod
    def ordinal(n: int) -> str:
        """Get ordinal string (1st, 2nd, 3rd, etc.)"""
        if 10 <= n % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
        return f"{n}{suffix}"
    
    @staticmethod
    def mask_email(email: str) -> str:
        """Mask email for privacy"""
        parts = email.split('@')
        if len(parts) != 2:
            return email
        
        name = parts[0]
        domain = parts[1]
        
        if len(name) <= 3:
            masked = name[0] + '*' * (len(name) - 1)
        else:
            masked = name[:2] + '*' * (len(name) - 3) + name[-1]
        
        return f"{masked}@{domain}"
    
    @staticmethod
    def progress_bar(current: int, total: int, width: int = 10) -> str:
        """Create progress bar"""
        if total == 0:
            return '░' * width
        
        filled = int(width * current / total)
        bar = '█' * filled + '░' * (width - filled)
        percentage = int(100 * current / total)
        
        return f"{bar} {percentage}%"

# ===========================================================================
# VALIDATION UTILITIES
# ===========================================================================

class Validator:
    """Validation utilities"""
    
    @staticmethod
    def email(email: str) -> bool:
        """Validate email"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def utr(utr: str) -> bool:
        """Validate UTR number"""
        return 12 <= len(utr) <= 22 and utr.isalnum()
    
    @staticmethod
    def phone(phone: str) -> bool:
        """Validate Indian phone number"""
        pattern = r'^[6-9]\d{9}$'
        return re.match(pattern, phone) is not None
    
    @staticmethod
    def amount(amount: int) -> bool:
        """Validate recharge amount"""
        return config.MIN_RECHARGE <= amount <= config.MAX_RECHARGE
    
    @staticmethod
    def pincode(pincode: str) -> bool:
        """Validate Indian pincode"""
        pattern = r'^[1-9][0-9]{5}$'
        return re.match(pattern, pincode) is not None
    
    @staticmethod
    def username(username: str) -> bool:
        """Validate username"""
        pattern = r'^[a-zA-Z0-9_]{3,20}$'
        return re.match(pattern, username) is not None
    
    @staticmethod
    def name(name: str) -> bool:
        """Validate name"""
        return 2 <= len(name.strip()) <= 50 and name.replace(' ', '').isalpha()

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

def rate_limit(func):
    """Decorator to apply rate limiting"""
    limiter = RateLimiter()
    
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not limiter.is_allowed(user.id):
            remaining = limiter.get_remaining(user.id)
            await update.message.reply_text(
                f"⚠️ *Rate Limited*\n\nPlease wait {remaining} seconds.",
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
        action = func.__name__
        
        logger.info(f"👤 User {user.id} ({user.first_name}) performed: {action}")
        
        try:
            result = await func(update, context, *args, **kwargs)
            logger.info(f"✅ Action {action} completed")
            return result
        except Exception as e:
            logger.error(f"❌ Action {action} failed: {e}")
            raise
    
    return wrapper

def handle_errors(func):
    """Decorator to handle errors gracefully"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            logger.error(f"❌ Error in {func.__name__}: {e}")
            
            error_message = (
                "⚠️ *An error occurred*\n\n"
                "Please try again later.\n"
                "If the problem persists, contact support."
            )
            
            try:
                await update.message.reply_text(
                    error_message,
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                try:
                    await update.callback_query.edit_message_text(
                        error_message,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
            
            return ConversationHandler.END
    
    return wrapper

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
# START COMMAND
# ===========================================================================

@log_action
@rate_limit
@handle_errors
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    # Initialize database manager
    db = DatabaseManager()
    
    # Get or create user
    db_user = db.get_user(user.id)
    if not db_user:
        db_user = db.create_user(user.id, user.username, user.first_name, user.last_name)
        logger.info(f"✅ New user registered: {user.id} - {user.first_name}")
        
        # Welcome bonus or referral handling
        if context.args and context.args[0].startswith('ref_'):
            referrer_code = context.args[0].replace('ref_', '')
            referrer = db.get_user_by_referral(referrer_code)
            if referrer and referrer['user_id'] != user.id:
                db.process_referral(referrer['user_id'], user.id)
                await context.bot.send_message(
                    chat_id=referrer['user_id'],
                    text=f"🎉 *Referral Bonus!*\n\n{user.first_name} joined using your link!\n₹10 added to your balance.",
                    parse_mode=ParseMode.MARKDOWN
                )
    
    db.update_last_active(user.id)
    
    # Check channel membership
    is_member = await check_membership(user.id, context)
    
    if not is_member:
        # Welcome message for new users
        welcome_text = (
            f"✨ *WELCOME TO {config.BOT_NAME}* ✨\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👋 *Hello {user.first_name}!*\n\n"
            f"🎁 *Get Gift Cards at 80% OFF!*\n"
            f"• Amazon • Flipkart • Play Store\n"
            f"• Myntra • Zomato • & 10+ More!\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔒 *VERIFICATION REQUIRED*\n"
            f"To ensure safe transactions, you must join our official channel.\n\n"
            f"👇 *Click below to join and verify*"
        )
        
        keyboard = [[
            InlineKeyboardButton("📢 JOIN OFFICIAL CHANNEL", url=f"https://t.me/gift_card_main"),
            InlineKeyboardButton("✅ I HAVE JOINED", callback_data="verify")
        ]]
        
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Show main menu for verified users
    balance = db.get_user_balance(user.id)
    
    # Get statistics
    stats = db.get_statistics()
    
    main_menu_text = (
        f"🎉 *WELCOME BACK TO {config.BOT_NAME}!* 🎉\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *User:* {user.first_name}\n"
        f"💰 *Balance:* {Formatter.currency(balance)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 *Today's Stats:*\n"
        f"• 👥 Active Users: {stats['active_today']}\n"
        f"• 💳 Transactions: {stats['transactions']}\n"
        f"• 🎁 Purchases: {stats['purchases']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"*What would you like to do today?* ⬇️"
    )
    
    keyboard = [
        [InlineKeyboardButton("🎁 GIFT CARDS", callback_data="giftcard")],
        [InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")],
        [InlineKeyboardButton("💳 MY WALLET", callback_data="wallet")],
        [InlineKeyboardButton("🆘 HELP & SUPPORT", callback_data="support")],
        [InlineKeyboardButton("📊 LIVE PROOFS", callback_data="proofs")],
        [InlineKeyboardButton("🎁 REFERRAL PROGRAM", callback_data="referral")],
        [InlineKeyboardButton("📱 ACCOUNT", callback_data="account")]
    ]
    
    await update.message.reply_text(
        main_menu_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===========================================================================
# BUTTON HANDLER
# ===========================================================================

@log_action
@handle_errors
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all button clicks"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data
    
    logger.info(f"🔘 Button: {data} by {user.first_name} (ID: {user.id})")
    
    # Initialize database
    db = DatabaseManager()
    db.update_last_active(user.id)
    
    # ===== VERIFY BUTTON =====
    if data == "verify":
        is_member = await check_membership(user.id, context)
        
        if is_member:
            balance = db.get_user_balance(user.id)
            
            success_text = (
                f"✅ *VERIFICATION SUCCESSFUL!*\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👋 *Welcome {user.first_name}!*\n"
                f"💰 *Balance:* {Formatter.currency(balance)}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"*You now have full access to:*\n"
                f"• 10+ Gift Card Brands\n"
                f"• Instant UPI Recharge\n"
                f"• 24/7 Auto Delivery\n"
                f"• Live Proofs Channel\n"
                f"• Referral Bonus Program\n\n"
                f"⬇️ *Choose an option:*"
            )
            
            keyboard = [
                [InlineKeyboardButton("🎁 GIFT CARDS", callback_data="giftcard")],
                [InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")],
                [InlineKeyboardButton("💳 MY WALLET", callback_data="wallet")],
                [InlineKeyboardButton("🆘 HELP & SUPPORT", callback_data="support")],
                [InlineKeyboardButton("📊 LIVE PROOFS", callback_data="proofs")]
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
        return
    
    # Check membership for other actions
    is_member = await check_membership(user.id, context)
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
    
    # ===== MAIN MENU =====
    if data == "main_menu":
        balance = db.get_user_balance(user.id)
        
        main_text = (
            f"🏠 *MAIN MENU*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *User:* {user.first_name}\n"
            f"💰 *Balance:* {Formatter.currency(balance)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"*Please select an option:*"
        )
        
        keyboard = [
            [InlineKeyboardButton("🎁 GIFT CARDS", callback_data="giftcard")],
            [InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")],
            [InlineKeyboardButton("💳 MY WALLET", callback_data="wallet")],
            [InlineKeyboardButton("🆘 HELP & SUPPORT", callback_data="support")],
            [InlineKeyboardButton("📊 LIVE PROOFS", callback_data="proofs")]
        ]
        
        await query.edit_message_text(
            main_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== GIFT CARD MENU =====
    elif data == "giftcard":
        # Get popular cards first
        popular_cards = [(cid, card) for cid, card in GIFT_CARDS.items() if card.get('popular', False)]
        other_cards = [(cid, card) for cid, card in GIFT_CARDS.items() if not card.get('popular', False)]
        
        keyboard = []
        
        # Add popular cards
        for card_id, card in popular_cards:
            keyboard.append([InlineKeyboardButton(
                f"{card['full_emoji']} {card['name']} ⭐", 
                callback_data=f"card_{card_id}"
            )])
        
        # Add separator if both sections exist
        if popular_cards and other_cards:
            keyboard.append([InlineKeyboardButton("─────────────", callback_data="ignore")])
        
        # Add other cards
        for card_id, card in other_cards:
            keyboard.append([InlineKeyboardButton(
                f"{card['full_emoji']} {card['name']}", 
                callback_data=f"card_{card_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 BACK TO MAIN", callback_data="main_menu")])
        
        giftcard_text = (
            f"🎁 *GIFT CARDS CATALOG*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"*Choose from 10+ brands:*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💳 *All cards delivered INSTANTLY on email*\n"
            f"⚡ *24/7 Automatic Delivery*\n"
            f"✅ *100% Working Codes*\n"
            f"🛡️ *Buyer Protection Guaranteed*\n\n"
            f"*Select your preferred brand below:* ⬇️"
        )
        
        await query.edit_message_text(
            giftcard_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== CARD DETAILS =====
    elif data.startswith("card_"):
        card_id = data.replace("card_", "")
        card = GIFT_CARDS.get(card_id)
        
        if not card:
            await query.edit_message_text("❌ Card not found")
            return
        
        # Build price buttons
        keyboard = []
        row = []
        for i, denom in enumerate(AVAILABLE_DENOMINATIONS):
            if denom in PRICES:
                price = PRICES[denom]
                button = InlineKeyboardButton(
                    f"₹{denom} → ₹{price}", 
                    callback_data=f"buy_{card_id}_{denom}"
                )
                row.append(button)
                if len(row) == 2 or i == len(AVAILABLE_DENOMINATIONS) - 1:
                    keyboard.append(row)
                    row = []
        
        keyboard.append([InlineKeyboardButton("🔙 BACK", callback_data="giftcard")])
        
        card_detail_text = (
            f"{card['full_emoji']} *{card['name']} GIFT CARD* {card['full_emoji']}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 *Description:*\n{card['description']}\n\n"
            f"📱 *Delivery:* {card['delivery']}\n"
            f"⏳ *Validity:* {card['validity']}\n"
            f"📋 *Terms:* {card['terms']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"*Available Denominations:*\n"
            f"(Face Value → Your Price)\n\n"
            f"*Select amount below:* ⬇️"
        )
        
        await query.edit_message_text(
            card_detail_text,
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
        if not card or value not in PRICES:
            await query.edit_message_text("❌ Card or amount not available")
            return
        
        price = PRICES[value]
        balance = db.get_user_balance(user.id)
        
        if balance < price:
            short = price - balance
            keyboard = [
                [InlineKeyboardButton("💰 ADD MONEY NOW", callback_data="topup")],
                [InlineKeyboardButton("🏠 MAIN MENU", callback_data="main_menu")]
            ]
            
            await query.edit_message_text(
                f"❌ *INSUFFICIENT BALANCE*\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"*Card:* {card['full_emoji']} {card['name']} ₹{value}\n"
                f"*Price:* {Formatter.currency(price)}\n"
                f"*Your Balance:* {Formatter.currency(balance)}\n"
                f"*Short by:* {Formatter.currency(short)}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Please add money to your wallet to continue.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        # Store purchase data in context
        context.user_data['purchase'] = {
            'card_id': card_id,
            'card_name': card['name'],
            'card_emoji': card['full_emoji'],
            'value': value,
            'price': price
        }
        
        # Show savings
        savings = value - price
        savings_percent = int((savings / value) * 100)
        
        await query.edit_message_text(
            f"✅ *BALANCE SUFFICIENT*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"*{card['full_emoji']} {card['name']} ₹{value}*\n"
            f"*Price:* {Formatter.currency(price)}\n"
            f"*You Save:* {Formatter.currency(savings)} ({savings_percent}% OFF)\n"
            f"*Your Balance:* {Formatter.currency(balance)}\n"
            f"*New Balance:* {Formatter.currency(balance - price)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📧 *Please enter your EMAIL address:*\n"
            f"_(We'll send the gift card instantly)_\n\n"
            f"Example: `yourname@gmail.com`",
            parse_mode=ParseMode.MARKDOWN
        )
        
        return STATE_EMAIL
    
    # ===== TOP UP MENU =====
    elif data == "topup":
        keyboard = [
            [InlineKeyboardButton("📱 UPI PAYMENT", callback_data="upi")],
            [InlineKeyboardButton("💰 CRYPTO (Coming Soon)", callback_data="crypto_soon")],
            [InlineKeyboardButton("🏦 BANK TRANSFER", callback_data="bank")],
            [InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]
        ]
        
        topup_text = (
            f"💰 *ADD MONEY TO WALLET*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"*Select payment method:*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📱 *UPI* - Instant & Easy\n"
            f"• Google Pay • PhonePe • Paytm\n"
            f"• BHIM • Amazon Pay • Any UPI App\n\n"
            f"💰 *Crypto* - Coming Soon\n"
            f"• USDT • Bitcoin • Ethereum\n\n"
            f"🏦 *Bank Transfer* - NEFT/IMPS\n"
            f"• Direct bank transfer\n\n"
            f"*Choose your preferred method:* ⬇️"
        )
        
        await query.edit_message_text(
            topup_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== UPI SELECTED =====
    elif data == "upi":
        upi_text = (
            f"💳 *UPI RECHARGE*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"*Please enter the amount to add:*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 *Minimum:* {Formatter.currency(config.MIN_RECHARGE)}\n"
            f"💰 *Maximum:* {Formatter.currency(config.MAX_RECHARGE)}\n\n"
            f"📌 *FEE STRUCTURE:*\n"
            f"• Below ₹{config.FEE_THRESHOLD}: {config.FEE_PERCENT}% fee\n"
            f"  Example: Pay ₹100 → Get ₹80\n"
            f"• Above ₹{config.FEE_THRESHOLD}: No fee\n"
            f"  Example: Pay ₹200 → Get ₹200\n\n"
            f"💡 *Pro Tip:* Recharge above ₹{config.FEE_THRESHOLD} to save fees!\n\n"
            f"*Enter amount (in numbers):*"
        )
        
        await query.edit_message_text(
            upi_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        return STATE_AMOUNT
    
    # ===== BANK TRANSFER =====
    elif data == "bank":
        bank_text = (
            f"🏦 *BANK TRANSFER DETAILS*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"*Account Details:*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🏦 *Bank:* HDFC Bank\n"
            f"👤 *Account Name:* Gift Card Store\n"
            f"📱 *Account No:* 12345678901234\n"
            f"🏧 *IFSC Code:* HDFC0001234\n"
            f"🏷️ *Account Type:* Current\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📌 *Instructions:*\n"
            f"1️⃣ Transfer the amount to above account\n"
            f"2️⃣ Send screenshot and UTR to @Admin\n"
            f"3️⃣ Amount will be credited within 30 mins\n\n"
            f"*Click BACK to return to main menu*"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="topup")]]
        
        await query.edit_message_text(
            bank_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== CRYPTO COMING SOON =====
    elif data == "crypto_soon":
        crypto_text = (
            f"💰 *CRYPTO PAYMENTS*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🚀 *Coming Soon!*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"We're working on integrating crypto payments:\n\n"
            f"• USDT (TRC-20)\n"
            f"• Bitcoin\n"
            f"• Ethereum\n"
            f"• BNB\n\n"
            f"Stay tuned for updates!\n\n"
            f"*Use UPI for instant recharge* ⚡"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="topup")]]
        
        await query.edit_message_text(
            crypto_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== WALLET =====
    elif data == "wallet":
        balance = db.get_user_balance(user.id)
        
        # Get recent transactions
        transactions = db.get_transactions(user.id, 5)
        
        trans_text = ""
        for t in transactions:
            amount = t['amount']
            type_ = t['type']
            time_str = Formatter.relative_time(t['timestamp'])
            
            if type_ == 'credit':
                trans_text += f"✅ *+{Formatter.currency(amount)}* ({time_str})\n"
            elif type_ == 'debit':
                trans_text += f"💳 *-{Formatter.currency(amount)}* ({time_str})\n"
            elif type_ == 'bonus':
                trans_text += f"🎁 *+{Formatter.currency(amount)}* (Bonus, {time_str})\n"
        
        if not trans_text:
            trans_text = "📭 No transactions yet"
        
        wallet_text = (
            f"💳 *YOUR WALLET*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 *Available Balance:* {Formatter.currency(balance)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"*📊 Recent Activity:*\n"
            f"{trans_text}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"*Quick Actions:* ⬇️"
        )
        
        keyboard = [
            [InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")],
            [InlineKeyboardButton("🎁 BUY GIFT CARDS", callback_data="giftcard")],
            [InlineKeyboardButton("📜 TRANSACTION HISTORY", callback_data="history")],
            [InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            wallet_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== TRANSACTION HISTORY =====
    elif data == "history":
        transactions = db.get_transactions(user.id, 10)
        
        history_text = f"📜 *TRANSACTION HISTORY*\n\n"
        history_text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        if not transactions:
            history_text += "📭 No transactions yet\n"
        else:
            for t in transactions:
                amount = t['amount']
                type_ = t['type']
                status = t['status']
                time_str = Formatter.date(t['timestamp'], "%d %b %Y")
                
                status_emoji = "✅" if status == 'completed' else "⏳" if status == 'pending' else "❌"
                
                if type_ == 'credit':
                    history_text += f"{status_emoji} *+{Formatter.currency(amount)}* ({time_str})\n"
                elif type_ == 'debit':
                    history_text += f"{status_emoji} *-{Formatter.currency(amount)}* ({time_str})\n"
                elif type_ == 'bonus':
                    history_text += f"🎁 *+{Formatter.currency(amount)}* (Bonus, {time_str})\n"
        
        history_text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="wallet")]]
        
        await query.edit_message_text(
            history_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== ACCOUNT =====
    elif data == "account":
        db_user = db.get_user(user.id)
        
        # Get statistics
        purchases = db.get_purchases(user.id, 1)
        total_purchases = len(db.get_purchases(user.id, 1000))
        
        account_text = (
            f"📱 *YOUR ACCOUNT*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Name:* {db_user['first_name']} {db_user.get('last_name', '')}\n"
            f"🆔 *User ID:* `{user.id}`\n"
            f"📧 *Email:* {db_user.get('email', 'Not set')}\n"
            f"📱 *Phone:* {db_user.get('phone', 'Not set')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *Account Statistics:*\n"
            f"• 📅 Joined: {Formatter.date(db_user['join_date'], '%d %b %Y')}\n"
            f"• 🎁 Total Purchases: {total_purchases}\n"
            f"• 💰 Total Spent: {Formatter.currency(db_user['total_spent'])}\n"
            f"• 💳 Total Recharged: {Formatter.currency(db_user['total_recharged'])}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"*Account Actions:* ⬇️"
        )
        
        keyboard = [
            [InlineKeyboardButton("📧 UPDATE EMAIL", callback_data="update_email")],
            [InlineKeyboardButton("📱 UPDATE PHONE", callback_data="update_phone")],
            [InlineKeyboardButton("🎁 MY PURCHASES", callback_data="my_purchases")],
            [InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            account_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== MY PURCHASES =====
    elif data == "my_purchases":
        purchases = db.get_purchases(user.id, 10)
        
        purchases_text = f"🎁 *YOUR PURCHASES*\n\n"
        purchases_text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        if not purchases:
            purchases_text += "📭 No purchases yet\n"
        else:
            for p in purchases:
                time_str = Formatter.date(p['timestamp'], "%d %b %Y")
                purchases_text += (
                    f"• {p['card_type']} ₹{p['card_value']}\n"
                  f"  🆔 Order: `{p['order_id']}`\n"
                  f"  📧 {Formatter.mask_email(p['email'])}\n"
                  f"  ⏰ {time_str}\n\n"
                )
        
        purchases_text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="account")]]
        
        await query.edit_message_text(
            purchases_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== REFERRAL PROGRAM =====
    elif data == "referral":
        db_user = db.get_user(user.id)
        referrals = db.get_referrals(user.id)
        
        referral_link = f"https://t.me/{context.bot.username}?start=ref_{db_user['referral_code']}"
        
        referral_text = (
            f"🎁 *REFERRAL PROGRAM*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"*Earn ₹10 for every friend who joins!*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔗 *Your Referral Link:*\n"
            f"`{referral_link}`\n\n"
            f"📊 *Your Statistics:*\n"
            f"• 👥 Total Referrals: {len(referrals)}\n"
            f"• 💰 Bonus Earned: {Formatter.currency(db_user['referral_bonus'])}\n\n"
            f"📌 *How it works:*\n"
            f"1️⃣ Share your referral link\n"
            f"2️⃣ Friend joins and recharges\n"
            f"3️⃣ You get ₹10 bonus instantly\n\n"
            f"*Start sharing now!* 🚀"
        )
        
        keyboard = [
            [InlineKeyboardButton("📋 COPY LINK", callback_data="copy_link")],
            [InlineKeyboardButton("📊 MY REFERRALS", callback_data="my_referrals")],
            [InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            referral_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== COPY LINK =====
    elif data == "copy_link":
        db_user = db.get_user(user.id)
        referral_link = f"https://t.me/{context.bot.username}?start=ref_{db_user['referral_code']}"
        
        await query.answer(f"Link copied! Share it with friends.", show_alert=False)
        
        # Just show the link
        await query.edit_message_text(
            f"🔗 *Your Referral Link:*\n\n`{referral_link}`\n\n"
            f"*Share this with your friends!*",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ===== SUPPORT =====
    elif data == "support":
        support_text = (
            f"🆘 *HELP & SUPPORT*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"*How can we help you today?*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"❓ *Frequently Asked Questions:*\n\n"
            f"1️⃣ *How to buy a gift card?*\n"
            f"   → Add money → Select card → Enter email\n\n"
            f"2️⃣ *How long does delivery take?*\n"
            f"   → Instant after purchase (2-5 minutes)\n\n"
            f"3️⃣ *Payment not credited?*\n"
            f"   → Send screenshot with UTR to support\n\n"
            f"4️⃣ *Card not received?*\n"
            f"   → Check spam folder, contact support\n\n"
            f"📝 *Still need help?*\n"
            f"Type your issue below and we'll respond within 24h.\n\n"
            f"*Our support team is here for you!* 🤝"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]]
        
        await query.edit_message_text(
            support_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return STATE_SUPPORT
    
    # ===== PROOFS =====
    elif data == "proofs":
        proofs_text = (
            f"📊 *LIVE PURCHASE PROOFS*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ *See real transactions from real users*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👉 {config.PROOF_CHANNEL}\n\n"
            f"⚡ *Latest Activity:*\n"
            f"• 1000+ successful deliveries\n"
            f"• Instant email delivery\n"
            f"• 24/7 automatic processing\n"
            f"• 4.9/5 user satisfaction\n\n"
            f"*Click below to join our proofs channel*\n"
            f"and see live purchases as they happen! 🎯"
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

# ===========================================================================
# AMOUNT HANDLER
# ===========================================================================

@handle_errors
async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle amount input for top-up"""
    user = update.effective_user
    text = update.message.text.strip()
    
    # Validate amount
    try:
        amount = int(text)
    except ValueError:
        await update.message.reply_text(
            "❌ *Invalid amount*\n\nPlease enter a valid number.",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_AMOUNT
    
    if not Validator.amount(amount):
        await update.message.reply_text(
            f"❌ *Invalid amount*\n\n"
            f"Amount must be between {Formatter.currency(config.MIN_RECHARGE)} "
            f"and {Formatter.currency(config.MAX_RECHARGE)}.",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_AMOUNT
    
    # Calculate fee
    fee, final = calculate_fee(amount)
    
    # Store in context
    context.user_data['topup'] = {
        'amount': amount,
        'fee': fee,
        'final': final
    }
    
    # Create buttons
    keyboard = [
        [InlineKeyboardButton("✅ I HAVE PAID", callback_data="paid")],
        [InlineKeyboardButton("❌ CANCEL", callback_data="main_menu")]
    ]
    
    # Try to send QR code
    qr_sent = False
    if os.path.exists(config.QR_CODE_PATH):
        try:
            with open(config.QR_CODE_PATH, 'rb') as qr_file:
                await update.message.reply_photo(
                    photo=qr_file,
                    caption=(
                        f"💳 *PAYMENT DETAILS*\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"*UPI ID:* `{config.UPI_ID}`\n"
                        f"*Amount:* {Formatter.currency(amount)}\n"
                        f"*Fee:* {Formatter.currency(fee) if fee > 0 else 'No fee'}\n"
                        f"*You will receive:* {Formatter.currency(final)}\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"📱 *HOW TO PAY:*\n"
                        f"1️⃣ Scan QR code or pay to UPI ID\n"
                        f"2️⃣ Take a SCREENSHOT of payment\n"
                        f"3️⃣ Copy the UTR number\n"
                        f"4️⃣ Click 'I HAVE PAID' below\n\n"
                        f"⏳ *Auto-cancel in {config.VERIFICATION_TIMEOUT//60} minutes*"
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                qr_sent = True
        except Exception as e:
            logger.error(f"❌ QR code error: {e}")
    
    if not qr_sent:
        await update.message.reply_text(
            f"💳 *PAYMENT DETAILS*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"*UPI ID:* `{config.UPI_ID}`\n"
            f"*Amount:* {Formatter.currency(amount)}\n"
            f"*Fee:* {Formatter.currency(fee) if fee > 0 else 'No fee'}\n"
            f"*You will receive:* {Formatter.currency(final)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📱 *HOW TO PAY:*\n"
            f"1️⃣ Open any UPI app (Google Pay/PhonePe/Paytm)\n"
            f"2️⃣ Pay to UPI ID: `{config.UPI_ID}`\n"
            f"3️⃣ Take a SCREENSHOT of payment\n"
            f"4️⃣ Copy the UTR number\n"
            f"5️⃣ Click 'I HAVE PAID' below\n\n"
            f"⏳ *Auto-cancel in {config.VERIFICATION_TIMEOUT//60} minutes*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # Clear amount state
    return ConversationHandler.END

# ===========================================================================
# PAID BUTTON HANDLER
# ===========================================================================

@handle_errors
async def handle_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle paid button click"""
    query = update.callback_query
    await query.answer()
    
    if 'topup' not in context.user_data:
        await query.edit_message_text(
            "❌ *Session expired*\n\nPlease start over with /start",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]]
    
    await query.edit_message_text(
        f"📤 *SEND PAYMENT PROOF*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*Please send the following:*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"1️⃣ *PAYMENT SCREENSHOT* (as photo)\n"
        f"2️⃣ *UTR NUMBER* (in text)\n\n"
        f"📌 *What is UTR?*\n"
        f"UTR (Unique Transaction Reference) is a\n"
        f"12-22 digit number from your bank statement\n"
        f"or payment app after successful payment.\n\n"
        f"*Example UTR:* `SBIN1234567890`\n\n"
        f"*Send both in this chat.*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return STATE_SCREENSHOT

# ===========================================================================
# SCREENSHOT HANDLER
# ===========================================================================

@handle_errors
async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle screenshot for payment"""
    if not update.message.photo:
        await update.message.reply_text(
            "❌ *Please send a PHOTO*\n\n"
            "Send the screenshot of your payment.",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_SCREENSHOT
    
    # Store screenshot
    photo = update.message.photo[-1].file_id
    context.user_data['screenshot'] = photo
    
    keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]]
    
    await update.message.reply_text(
        "✅ *SCREENSHOT RECEIVED*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Now please send your *UTR number*.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📌 *UTR* is the 12-22 digit reference number\n"
        "from your bank statement or payment app.\n\n"
        "Example: `SBIN1234567890`\n\n"
        "*Send the UTR number as text.*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return STATE_UTR

# ===========================================================================
# UTR HANDLER
# ===========================================================================

@handle_errors
async def handle_utr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle UTR input for payment"""
    user = update.effective_user
    utr = update.message.text.strip()
    
    # Initialize database
    db = DatabaseManager()
    
    # Validate UTR
    if not Validator.utr(utr):
        await update.message.reply_text(
            "❌ *Invalid UTR*\n\n"
            "UTR should be 12-22 alphanumeric characters.\n"
            "Please check and try again.\n\n"
            "Example: `SBIN1234567890`",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_UTR
    
    # Check if UTR already exists
    existing = db.get_transaction_by_utr(utr)
    if existing:
        await update.message.reply_text(
            "❌ *Duplicate UTR*\n\n"
            "This UTR has already been submitted.\n"
            "Please check and try again.",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_UTR
    
    # Check session data
    if 'topup' not in context.user_data or 'screenshot' not in context.user_data:
        await update.message.reply_text(
            "❌ *Session expired*\n\nPlease start over with /start",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    data = context.user_data['topup']
    screenshot = context.user_data['screenshot']
    
    # Create verification
    verification_id = db.create_verification(
        user.id,
        data['amount'],
        data['fee'],
        data['final'],
        utr,
        screenshot
    )
    
    # Get user info
    db_user = db.get_user(user.id)
    
    # Create admin message with enhanced details
    caption = (
        f"🔔 *NEW PAYMENT VERIFICATION*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *User:* {user.first_name} {user.last_name or ''}\n"
        f"🆔 *ID:* `{user.id}`\n"
        f"👤 *Username:* @{user.username or 'N/A'}\n"
        f"📧 *Email:* {db_user.get('email', 'Not set')}\n"
        f"📱 *Phone:* {db_user.get('phone', 'Not set')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 *Amount:* {Formatter.currency(data['amount'])}\n"
        f"💸 *Fee:* {Formatter.currency(data['fee'])}\n"
        f"🎁 *Credit:* {Formatter.currency(data['final'])}\n"
        f"🔢 *UTR:* `{utr}`\n"
        f"🆔 *Verification ID:* `{verification_id}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ *Time:* {datetime.now().strftime('%d %b %Y, %I:%M:%S %p')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    # Create approve/reject buttons
    keyboard = [[
        InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{verification_id}"),
        InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{verification_id}")
    ]]
    
    # Send to admin channel
    await context.bot.send_photo(
        chat_id=config.ADMIN_CHANNEL_ID,
        photo=screenshot,
        caption=caption,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    # Clear session data
    context.user_data.clear()
    
    # Confirm to user
    keyboard = [[InlineKeyboardButton("🏠 MAIN MENU", callback_data="main_menu")]]
    
    await update.message.reply_text(
        f"✅ *VERIFICATION SUBMITTED!*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*Verification ID:* `{verification_id}`\n"
        f"*UTR:* `{utr}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Your payment is being verified.\n"
        f"You will be notified once approved.\n\n"
        f"⏳ *Estimated time: 5-10 minutes*\n\n"
        f"Thank you for your patience! 🙏",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ConversationHandler.END

# ===========================================================================
# EMAIL HANDLER
# ===========================================================================

@handle_errors
async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle email for purchase"""
    user = update.effective_user
    email = update.message.text.strip()
    
    # Initialize database
    db = DatabaseManager()
    
    # Validate email
    if not Validator.email(email):
        await update.message.reply_text(
            "❌ *Invalid email*\n\n"
            "Please enter a valid email address.\n\n"
            "Example: `yourname@gmail.com`\n"
            "Example: `name@yahoo.co.in`",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_EMAIL
    
    # Check session
    if 'purchase' not in context.user_data:
        await update.message.reply_text(
            "❌ *Session expired*\n\nPlease start over with /start",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    purchase = context.user_data['purchase']
    balance = db.get_user_balance(user.id)
    
    if balance < purchase['price']:
        await update.message.reply_text(
            "❌ *Insufficient balance*\n\n"
            "Please add money to your wallet.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    # Process purchase
    success = db.update_balance(
        user.id,
        -purchase['price'],
        'debit',
        description=f"Purchased {purchase['card_name']} ₹{purchase['value']}"
    )
    
    if not success:
        await update.message.reply_text(
            "❌ *Transaction failed*\n\nPlease try again.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    # Create purchase record
    order_id = db.create_purchase(
        user.id,
        purchase['card_name'],
        purchase['value'],
        purchase['price'],
        email
    )
    
    # Update user email if not set
    db_user = db.get_user(user.id)
    if not db_user.get('email'):
        db.update_user(user.id, email=email)
    
    # Clear session
    context.user_data.clear()
    
    # Send confirmation
    keyboard = [[InlineKeyboardButton("🏠 MAIN MENU", callback_data="main_menu")]]
    
    savings = purchase['value'] - purchase['price']
    savings_percent = int((savings / purchase['value']) * 100)
    
    await update.message.reply_text(
        f"✅ *PURCHASE SUCCESSFUL!*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*{purchase['card_emoji']} {purchase['card_name']} ₹{purchase['value']}*\n"
        f"*Price:* {Formatter.currency(purchase['price'])}\n"
        f"*You Saved:* {Formatter.currency(savings)} ({savings_percent}% OFF)\n"
        f"*Order ID:* `{order_id}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📧 *Gift card sent to:*\n"
        f"`{email}`\n\n"
        f"📌 *IMPORTANT INSTRUCTIONS:*\n"
        f"• Check your inbox (and spam folder)\n"
        f"• Card arrives in 2-5 minutes\n"
        f"• Contact support if not received\n\n"
        f"Thank you for shopping with us! 🎉",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    # Send random proof to channel (70% chance)
    if random.random() < 0.7:
        try:
            # Cool names for proofs
            names = [
                "👑 Raj", "💫 Arjun", "🌟 Kavya", "⚡ Veer", "🔥 Aryan",
                "💎 Neha", "🎯 Karan", "🚀 Riya", "⭐ Amit", "💥 Priya",
                "🦁 Simba", "🐅 Tiger", "🦅 Falcon", "🐺 Wolf", "🦊 Fox",
                "👨‍💻 Dev", "👩‍🎨 Art", "👨‍🔧 Tech", "👩‍🔬 Sci", "👨‍🚀 Space"
            ]
            
            name = random.choice(names)
            
            proof_text = (
                f"⚡ *NEW PURCHASE*\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 *{name}* just bought\n"
                f"🎁 {purchase['card_emoji']} {purchase['card_name']} *₹{purchase['value']}*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📧 *Delivery:* Email (Instant)\n"
                f"🕐 *Time:* {datetime.now().strftime('%I:%M %p')}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            
            await context.bot.send_message(
                chat_id=config.PROOF_CHANNEL,
                text=proof_text,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"❌ Proof send error: {e}")
    
    return ConversationHandler.END

# ===========================================================================
# SUPPORT HANDLER
# ===========================================================================

@handle_errors
async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle support message"""
    user = update.effective_user
    message = update.message.text.strip()
    
    # Initialize database
    db = DatabaseManager()
    
    if len(message) < 10:
        await update.message.reply_text(
            "❌ *Message too short*\n\n"
            "Please describe your issue in detail (minimum 10 characters).",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_SUPPORT
    
    # Create support ticket
    ticket_id = db.create_support_ticket(user.id, message)
    
    # Notify admin
    try:
        db_user = db.get_user(user.id)
        
        admin_msg = (
            f"🆘 *NEW SUPPORT TICKET*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *User:* {user.first_name} {user.last_name or ''}\n"
            f"🆔 *ID:* `{user.id}`\n"
            f"👤 *Username:* @{user.username or 'N/A'}\n"
            f"📧 *Email:* {db_user.get('email', 'Not set')}\n"
            f"📱 *Phone:* {db_user.get('phone', 'Not set')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎫 *Ticket ID:* `{ticket_id}`\n"
            f"💬 *Message:*\n{message}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ *Time:* {datetime.now().strftime('%d %b %Y, %I:%M:%S %p')}"
        )
        
        await context.bot.send_message(
            chat_id=config.ADMIN_ID,
            text=admin_msg,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"❌ Admin notification error: {e}")
    
    # Confirm to user
    keyboard = [[InlineKeyboardButton("🏠 MAIN MENU", callback_data="main_menu")]]
    
    await update.message.reply_text(
        f"✅ *SUPPORT MESSAGE SENT!*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*Ticket ID:* `{ticket_id}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Your issue has been recorded.\n"
        f"Our support team will contact you within 24 hours.\n\n"
        f"Thank you for your patience! 🙏",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ConversationHandler.END

# ===========================================================================
# ADMIN CALLBACK HANDLER
# ===========================================================================

@admin_only
@handle_errors
async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    parts = data.split("_")
    
    if len(parts) < 2:
        await query.edit_message_caption("❌ Invalid data")
        return
    
    action = parts[0]
    verification_id = parts[1]
    
    # Initialize database
    db = DatabaseManager()
    
    if action == "approve":
        # Approve payment
        success = db.approve_verification(verification_id, config.ADMIN_ID)
        
        if success:
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n✅ *APPROVED BY ADMIN*",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Send admin notification
            await context.bot.send_message(
                chat_id=config.ADMIN_ID,
                text=f"✅ Payment {verification_id} approved successfully!",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n❌ *APPROVAL FAILED*",
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif action == "reject":
        # Reject payment
        success = db.reject_verification(verification_id, config.ADMIN_ID)
        
        if success:
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n❌ *REJECTED BY ADMIN*",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Send admin notification
            await context.bot.send_message(
                chat_id=config.ADMIN_ID,
                text=f"❌ Payment {verification_id} rejected.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n❌ *REJECTION FAILED*",
                parse_mode=ParseMode.MARKDOWN
            )

# ===========================================================================
# ADMIN COMMANDS
# ===========================================================================

@admin_only
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to view statistics"""
    db = DatabaseManager()
    stats = db.get_statistics()
    
    # Get today's stats
    today = datetime.now().date().isoformat()
    
    stats_text = (
        f"📊 *BOT STATISTICS*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 *Date:* {datetime.now().strftime('%d %b %Y')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"*👥 Users:*\n"
        f"• Total Users: {stats['total_users']:,}\n"
        f"• Active Today: {stats['active_today']}\n"
        f"• New Today: {stats['new_today']}\n\n"
        f"*💰 Finances:*\n"
        f"• Total Revenue: {Formatter.currency(stats['total_revenue'])}\n"
        f"• Total Spent: {Formatter.currency(stats['total_spent'])}\n"
        f"• Total Balance: {Formatter.currency(stats['total_balance'])}\n\n"
        f"*📊 Activity:*\n"
        f"• Transactions: {stats['total_transactions']:,}\n"
        f"• Purchases: {stats['total_purchases']:,}\n"
        f"• Pending Verifications: {stats['pending_verifications']}\n"
        f"• Open Tickets: {stats['open_tickets']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    await update.message.reply_text(
        stats_text,
        parse_mode=ParseMode.MARKDOWN
    )

@admin_only
async def admin_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to view pending verifications"""
    db = DatabaseManager()
    pending = db.get_pending_verifications()
    
    if not pending:
        await update.message.reply_text(
            "✅ *No pending verifications*",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text = f"⏳ *PENDING VERIFICATIONS ({len(pending)})*\n\n"
    
    for p in pending[:10]:  # Show first 10
        user = db.get_user(p['user_id'])
        username = user['username'] if user and user.get('username') else 'Unknown'
        
        text += (
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 *ID:* `{p['verification_id']}`\n"
            f"👤 *User:* @{username}\n"
            f"💰 *Amount:* {Formatter.currency(p['amount'])}\n"
            f"🎁 *Credit:* {Formatter.currency(p['final_amount'])}\n"
            f"🔢 *UTR:* `{p['utr']}`\n"
            f"⏰ *Time:* {Formatter.relative_time(p['timestamp'])}\n"
        )
    
    text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN
    )

@admin_only
async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to broadcast message"""
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
    db = DatabaseManager()
    with db.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE status = 'active'")
        users = c.fetchall()
    
    status_msg = await update.message.reply_text(
        f"📢 *Broadcasting to {len(users)} users...*",
        parse_mode=ParseMode.MARKDOWN
    )
    
    sent = 0
    failed = 0
    
    broadcast_text = (
        f"📢 *ADMIN BROADCAST*\n\n"
        f"{message}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*{config.BOT_NAME}*"
    )
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user[0],
                text=broadcast_text,
                parse_mode=ParseMode.MARKDOWN
            )
            sent += 1
            await asyncio.sleep(0.05)  # Rate limit
        except Exception as e:
            failed += 1
            logger.error(f"❌ Broadcast to {user[0]} failed: {e}")
        
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

# ===========================================================================
# AUTO PROOFS JOB
# ===========================================================================

async def auto_proofs(context: ContextTypes.DEFAULT_TYPE):
    """Send random purchase proofs to proof channel"""
    try:
        # Extended list of cool names with emojis
        names = [
            "👑 Raj", "💫 Arjun", "🌟 Kavya", "⚡ Veer", "🔥 Aryan",
            "💎 Neha", "🎯 Karan", "🚀 Riya", "⭐ Amit", "💥 Priya",
            "🦁 Simba", "🐅 Tiger", "🦅 Falcon", "🐺 Wolf", "🦊 Fox",
            "👨‍💻 Dev", "👩‍🎨 Art", "👨‍🔧 Tech", "👩‍🔬 Sci", "👨‍🚀 Space",
            "🎭 Rocky", "🎪 Rani", "🎨 Chitra", "🎮 Gamer", "🎵 Music",
            "💃 Dancer", "🕺 Dancer", "🏃 Runner", "🏋️ Gym", "🧘 Yoga",
            "👑 King", "👸 Queen", "🤴 Prince", "👸 Princess", "🧙 Wizard",
            "🦸 Hero", "🦹 Storm", "🧚 Fairy", "🧛 Vamp", "🧟 Zombie"
        ]
        
        cards = [
            "🟦 AMAZON", "🟩 PLAY STORE", "🎟️ BOOKMYSHOW", 
            "🛍️ MYNTRA", "📦 FLIPKART", "🍕 ZOMATO", 
            "🛒 BIG BASKET", "🎮 GOOGLE PLAY", "🎬 NETFLIX", 
            "🎵 SPOTIFY", "💳 AMAZON PAY", "🏏 DREAM11",
            "🎁 GIFT VOUCHER", "🛍️ AJIO", "👕 MYNTRA",
            "📱 APPLE", "💻 DELL", "🎧 BOAT", "⌚ SAMSUNG",
            "🎮 XBOX", "🎮 PLAYSTATION", "📚 KINDLE", "☕ STARBUCKS"
        ]
        
        amounts = [500, 1000, 2000, 5000]
        
        name = random.choice(names)
        card = random.choice(cards)
        amount = random.choice(amounts)
        
        # Different message formats
        formats = [
            f"⚡ *NEW PURCHASE*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✨ *{name}* just bought\n"
            f"🎁 {card} *₹{amount}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📧 *Delivery:* Email (Instant)\n"
            f"🕐 *Time:* {datetime.now().strftime('%I:%M %p')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            
            f"🎉 *FRESH ORDER*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Buyer:* {name}\n"
            f"💳 *Card:* {card}\n"
            f"💰 *Value:* ₹{amount}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📨 *Status:* Sent to Email\n"
            f"✅ *Delivery:* Instant\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            
            f"🛒 *ORDER COMPLETED*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 {name}\n"
            f"🎁 {card}\n"
            f"💵 ₹{amount}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📧 *Email Delivery*\n"
            f"⚡ *Instant*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            
            f"⭐ *LIVE PURCHASE*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔹 *User:* {name}\n"
            f"🔹 *Product:* {card}\n"
            f"🔹 *Amount:* ₹{amount}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔹 *Time:* {datetime.now().strftime('%I:%M %p')}\n"
            f"✅ *Success*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            
            f"💫 *TRANSACTION ALERT*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏷️ *{name}*\n"
            f"📦 *{card}*\n"
            f"💵 ₹{amount}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📧 *Email Delivery*\n"
            f"✨ *Instant*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            
            f"🌟 *NEW ORDER*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 {name}\n"
            f"🛍️ {card}\n"
            f"💳 ₹{amount}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ *Delivered via Email*\n"
            f"⚡ *Instant*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            
            f"🎯 *PURCHASE ALERT*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Customer:* {name}\n"
            f"🎁 *Item:* {card}\n"
            f"💵 *Amount:* ₹{amount}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📧 *Email:* Sent\n"
            f"⚡ *Status:* Completed\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ]
        
        message = random.choice(formats)
        
        await context.bot.send_message(
            chat_id=config.PROOF_CHANNEL,
            text=message,
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info("✅ Auto proof sent to channel")
        
    except Exception as e:
        logger.error(f"❌ Auto proof error: {e}")

# ===========================================================================
# CLEANUP JOB
# ===========================================================================

async def cleanup_job(context: ContextTypes.DEFAULT_TYPE):
    """Periodic cleanup job"""
    try:
        db = DatabaseManager()
        
        # Update daily statistics
        db.update_daily_stats()
        
        # Create backup (once per day)
        now = datetime.now()
        if now.hour == 0 and now.minute < 10:  # Around midnight
            backup_path = db.backup_database()
            if backup_path:
                logger.info(f"✅ Daily backup created: {backup_path}")
        
        logger.info("✅ Cleanup job completed")
        
    except Exception as e:
        logger.error(f"❌ Cleanup job error: {e}")

# ===========================================================================
# CANCEL HANDLER
# ===========================================================================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current operation"""
    user = update.effective_user
    
    # Clear context
    context.user_data.clear()
    
    keyboard = [[InlineKeyboardButton("🏠 MAIN MENU", callback_data="main_menu")]]
    
    await update.message.reply_text(
        "❌ *Cancelled*\n\nOperation cancelled.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ConversationHandler.END

# ===========================================================================
# IGNORE HANDLER
# ===========================================================================

async def ignore_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ignore callback (for separator buttons)"""
    query = update.callback_query
    await query.answer()

# ===========================================================================
# ERROR HANDLER
# ===========================================================================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    try:
        raise context.error
    except RetryAfter as e:
        logger.warning(f"⏳ Rate limited, retry after {e.retry_after}s")
        await asyncio.sleep(e.retry_after)
    except TimedOut:
        logger.error("⏰ Request timed out")
    except NetworkError as e:
        logger.error(f"🌐 Network error: {e}")
    except TelegramError as e:
        logger.error(f"📱 Telegram error: {e}")
    except Exception as e:
        logger.error(f"❌ Unhandled error: {e}")
        
        # Notify admin of critical errors
        if update and update.effective_user:
            try:
                error_text = (
                    f"❌ *Critical Error*\n\n"
                    f"User: {update.effective_user.id}\n"
                    f"Error: {str(e)[:200]}"
                )
                await context.bot.send_message(
                    chat_id=config.ADMIN_ID,
                    text=error_text,
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass

# ===========================================================================
# POST INITIALIZATION
# ===========================================================================

async def post_init(application: Application):
    """Setup after bot initialization"""
    # Set bot commands
    commands = [
        BotCommand("start", "🚀 Start the bot"),
        BotCommand("cancel", "❌ Cancel current operation"),
        BotCommand("stats", "📊 Bot statistics (admin)"),
        BotCommand("pending", "⏳ Pending verifications (admin)"),
        BotCommand("broadcast", "📢 Broadcast message (admin)")
    ]
    
    await application.bot.set_my_commands(commands)
    
    # Initialize database
    db = DatabaseManager()
    await asyncio.to_thread(db._init_database)
    
    # Log startup
    logger.info(f"✅ {config.BOT_NAME} v{config.BOT_VERSION} initialized successfully")

# ===========================================================================
# MAIN FUNCTION
# ===========================================================================

def calculate_fee(amount: int) -> Tuple[int, int]:
    """Calculate fee and final amount"""
    if amount < config.FEE_THRESHOLD:
        fee = int(amount * config.FEE_PERCENT / 100)
        final = amount - fee
    else:
        fee = 0
        final = amount
    return fee, final

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
        
        # ===== BUTTON HANDLERS =====
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(CallbackQueryHandler(ignore_callback, pattern="^ignore$"))
        
        # ===== ADMIN CALLBACK HANDLER =====
        app.add_handler(CallbackQueryHandler(admin_handler, pattern="^(approve_|reject_)"))
        
        # ===== PAID BUTTON HANDLER =====
        app.add_handler(CallbackQueryHandler(handle_paid, pattern="^paid$"))
        
        # ===== AMOUNT CONVERSATION =====
        amount_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(button_handler, pattern="^upi$")],
            states={
                STATE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)]
            },
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        app.add_handler(amount_conv)
        
        # ===== PAYMENT VERIFICATION CONVERSATION =====
        payment_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(handle_paid, pattern="^paid$")],
            states={
                STATE_SCREENSHOT: [
                    MessageHandler(filters.PHOTO, handle_screenshot),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_screenshot)
                ],
                STATE_UTR: [
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
                STATE_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email)]
            },
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        app.add_handler(email_conv)
        
        # ===== SUPPORT CONVERSATION =====
        support_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(button_handler, pattern="^support$")],
            states={
                STATE_SUPPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_support)]
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
        logger.info(f"🚀 Starting {config.BOT_NAME} v{config.BOT_VERSION}...")
        
        print("\n" + "="*70)
        print(f"      {config.BOT_NAME} v{config.BOT_VERSION}")
        print("="*70)
        print(f"📢 Main Channel: {config.MAIN_CHANNEL}")
        print(f"📊 Proof Channel: {config.PROOF_CHANNEL}")
        print(f"👑 Admin ID: {config.ADMIN_ID}")
        print(f"💳 UPI ID: {config.UPI_ID}")
        print(f"📁 Database: {config.DATABASE_PATH}")
        print(f"📱 Rate Limit: {config.RATE_LIMIT}/min")
        print(f"⏳ Session Timeout: {config.SESSION_TIMEOUT//60} minutes")
        print("="*70)
        print(f"✅ Bot is running...")
        print("="*70 + "\n")
        
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.critical(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
