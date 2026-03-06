#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
================================================================================
🎁 GIFT CARD & RECHARGE BOT - ULTIMATE PREMIUM EDITION 🎁
================================================================================
A fully featured Telegram bot for selling gift cards and managing recharges
with beautiful UI, complete error handling, professional design, and smooth performance.

Version: 6.0.0 (Ultimate Production Release)
Author: Professional Bot Developer
Last Updated: 2024
================================================================================
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
from collections import defaultdict, OrderedDict
from contextlib import contextmanager
import threading
from queue import Queue, PriorityQueue
from enum import Enum
import signal
import traceback
import secrets
import string

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
    """Centralized configuration management with validation"""
    
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
    REFERRAL_BONUS = 10
    WELCOME_BONUS = 5
    
    # File Paths
    QR_CODE_PATH = "qr.jpg"
    DATABASE_PATH = "bot_database.db"
    LOG_FILE = "bot.log"
    ERROR_LOG = "errors.log"
    BACKUP_DIR = "backups"
    
    # Timeouts and Limits
    SESSION_TIMEOUT = 600  # 10 minutes
    RATE_LIMIT = 30  # requests per minute
    VERIFICATION_TIMEOUT = 600  # 10 minutes
    CACHE_TIMEOUT = 300  # 5 minutes
    BACKUP_INTERVAL = 3600  # 1 hour
    
    # UI Configuration
    BOT_NAME = "🎁 GIFT CARD BOT"
    BOT_VERSION = "6.0.0"
    COMPANY_NAME = "GiftCard Store"
    SUPPORT_EMAIL = "support@giftcardstore.com"
    WEBSITE = "www.giftcardstore.com"
    
    # Feature Flags
    ENABLE_REFERRAL = True
    ENABLE_WELCOME_BONUS = True
    ENABLE_MAINTENANCE_MODE = False
    ENABLE_AUTO_BACKUP = True
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        if not cls.BOT_TOKEN:
            raise ValueError("❌ BOT_TOKEN is required")
        if not cls.ADMIN_ID:
            raise ValueError("❌ ADMIN_ID is required")
        if cls.MIN_RECHARGE >= cls.MAX_RECHARGE:
            raise ValueError("❌ MIN_RECHARGE must be less than MAX_RECHARGE")
        return True

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
    VIP = "vip"

class TransactionType(Enum):
    """Transaction type enumeration"""
    CREDIT = "credit"
    DEBIT = "debit"
    BONUS = "bonus"
    REFUND = "refund"
    REFERRAL = "referral"

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
    BANK = "bank"
    CRYPTO = "crypto"
    WALLET = "wallet"

class SupportPriority(Enum):
    """Support ticket priority"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

class NotificationType(Enum):
    """Notification type enumeration"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    PROMOTION = "promotion"

# Conversation States
(
    STATE_AMOUNT,
    STATE_SCREENSHOT,
    STATE_UTR,
    STATE_EMAIL,
    STATE_SUPPORT,
    STATE_FEEDBACK,
    STATE_REFERRAL,
    STATE_WITHDRAW,
    STATE_EXCHANGE,
    STATE_BANK_DETAILS,
    STATE_UPDATE_PROFILE,
    STATE_UPDATE_EMAIL,
    STATE_UPDATE_PHONE,
    STATE_VERIFY_OTP
) = range(15)

# ===========================================================================
# GIFT CARD DATA - EXTENSIVE COLLECTION
# ===========================================================================

GIFT_CARDS = OrderedDict({
    # Popular Cards
    "amazon": {
        "id": "amazon",
        "name": "AMAZON",
        "emoji": "🟦",
        "full_emoji": "🟦🛒",
        "description": "🌐 *Amazon.in Gift Card*\n\n✅ Shop millions of products\n✅ Instant delivery on email\n✅ Valid on all Amazon services\n✅ No expiry date\n\n🎯 *Best for:* Shopping, Electronics, Books",
        "long_description": "Amazon Gift Cards can be used to purchase millions of items on Amazon.in including electronics, fashion, books, movies, and more. They never expire and have no fees.",
        "delivery": "📧 *Instant Email Delivery*",
        "validity": "📅 *No Expiry*",
        "terms": "📋 Valid on all Amazon.in products and services",
        "popular": True,
        "featured": True,
        "discount": "80% OFF",
        "brand_color": "#FF9900",
        "icon": "🛒",
        "category": "Shopping",
        "rating": 4.9,
        "reviews": 15234
    },
    "flipkart": {
        "id": "flipkart",
        "name": "FLIPKART",
        "emoji": "📦",
        "full_emoji": "📦🛍️",
        "description": "📦 *Flipkart Gift Card*\n\n✅ Shop everything from A to Z\n✅ Instant email delivery\n✅ Valid on all Flipkart products\n✅ Great for gifting\n\n🎯 *Best for:* Shopping, Electronics, Fashion",
        "long_description": "Flipkart Gift Cards can be used to purchase products on Flipkart.com including electronics, fashion, home appliances, books, and more.",
        "delivery": "📧 *Instant Email Delivery*",
        "validity": "📅 *1 Year*",
        "terms": "📋 Valid on all Flipkart products",
        "popular": True,
        "featured": True,
        "discount": "80% OFF",
        "brand_color": "#2874F0",
        "icon": "🛍️",
        "category": "Shopping",
        "rating": 4.8,
        "reviews": 12456
    },
    "playstore": {
        "id": "playstore",
        "name": "PLAY STORE",
        "emoji": "🟩",
        "full_emoji": "🟩🎮",
        "description": "🎮 *Google Play Gift Card*\n\n✅ Apps, Games, Movies & More\n✅ Instant email delivery\n✅ Use on Play Store\n✅ Perfect for Android users\n\n🎯 *Best for:* Apps, Games, Movies",
        "long_description": "Google Play Gift Cards can be used to purchase apps, games, movies, books, and more on the Google Play Store.",
        "delivery": "📧 *Instant Email Delivery*",
        "validity": "📅 *1 Year*",
        "terms": "📋 Valid on Google Play Store",
        "popular": True,
        "featured": True,
        "discount": "80% OFF",
        "brand_color": "#34A853",
        "icon": "🎮",
        "category": "Digital",
        "rating": 4.9,
        "reviews": 18345
    },
    "bookmyshow": {
        "id": "bookmyshow",
        "name": "BOOKMYSHOW",
        "emoji": "🎟️",
        "full_emoji": "🎟️🎬",
        "description": "🎬 *BookMyShow Gift Card*\n\n✅ Movie Tickets & Events\n✅ Instant email delivery\n✅ Book any show anytime\n✅ Great for movie lovers\n\n🎯 *Best for:* Movies, Events, Concerts",
        "long_description": "BookMyShow Gift Cards can be used to book movie tickets, live events, plays, and sports events across India.",
        "delivery": "📧 *Instant Email Delivery*",
        "validity": "📅 *6 Months*",
        "terms": "📋 Valid on BookMyShow platform",
        "popular": True,
        "featured": True,
        "discount": "80% OFF",
        "brand_color": "#C51C3E",
        "icon": "🎬",
        "category": "Entertainment",
        "rating": 4.7,
        "reviews": 8934
    },
    "myntra": {
        "id": "myntra",
        "name": "MYNTRA",
        "emoji": "🛍️",
        "full_emoji": "🛍️👗",
        "description": "👗 *Myntra Gift Card*\n\n✅ Fashion & Lifestyle\n✅ Instant email delivery\n✅ 1000+ brands available\n✅ Free shipping on app\n\n🎯 *Best for:* Fashion, Clothing, Accessories",
        "long_description": "Myntra Gift Cards can be used to purchase fashion and lifestyle products from 1000+ brands on Myntra.",
        "delivery": "📧 *Instant Email Delivery*",
        "validity": "📅 *1 Year*",
        "terms": "📋 Valid on all Myntra products",
        "popular": True,
        "featured": False,
        "discount": "80% OFF",
        "brand_color": "#E12B38",
        "icon": "👗",
        "category": "Fashion",
        "rating": 4.6,
        "reviews": 7234
    },
    "zomato": {
        "id": "zomato",
        "name": "ZOMATO",
        "emoji": "🍕",
        "full_emoji": "🍕🍔",
        "description": "🍔 *Zomato Gift Card*\n\n✅ Food Delivery\n✅ Instant email delivery\n✅ Valid on all restaurants\n✅ Great for foodies\n\n🎯 *Best for:* Food, Dining, Delivery",
        "long_description": "Zomato Gift Cards can be used to order food from thousands of restaurants across India on Zomato.",
        "delivery": "📧 *Instant Email Delivery*",
        "validity": "📅 *6 Months*",
        "terms": "📋 Valid on Zomato orders",
        "popular": True,
        "featured": False,
        "discount": "80% OFF",
        "brand_color": "#CB202D",
        "icon": "🍔",
        "category": "Food",
        "rating": 4.8,
        "reviews": 10234
    },
    "bigbasket": {
        "id": "bigbasket",
        "name": "BIG BASKET",
        "emoji": "🛒",
        "full_emoji": "🛒🥬",
        "description": "🥬 *BigBasket Gift Card*\n\n✅ Grocery Delivery\n✅ Instant email delivery\n✅ Fresh vegetables & fruits\n✅ Daily essentials\n\n🎯 *Best for:* Grocery, Daily needs",
        "long_description": "BigBasket Gift Cards can be used to purchase groceries, fresh fruits, vegetables, and daily essentials on BigBasket.",
        "delivery": "📧 *Instant Email Delivery*",
        "validity": "📅 *1 Year*",
        "terms": "📋 Valid on BigBasket orders",
        "popular": True,
        "featured": False,
        "discount": "80% OFF",
        "brand_color": "#A7C83B",
        "icon": "🥬",
        "category": "Grocery",
        "rating": 4.5,
        "reviews": 5678
    },
    # Premium Cards
    "netflix": {
        "id": "netflix",
        "name": "NETFLIX",
        "emoji": "🎬",
        "full_emoji": "🎬📺",
        "description": "📺 *Netflix Gift Card*\n\n✅ Streaming Service\n✅ Instant email delivery\n✅ HD & 4K streaming\n✅ Watch anywhere\n\n🎯 *Best for:* Movies, TV Shows",
        "long_description": "Netflix Gift Cards can be used to subscribe to Netflix plans and enjoy unlimited movies and TV shows.",
        "delivery": "📧 *Instant Email Delivery*",
        "validity": "📅 *1 Year*",
        "terms": "📋 Valid on Netflix subscription",
        "popular": False,
        "featured": True,
        "discount": "70% OFF",
        "brand_color": "#E50914",
        "icon": "📺",
        "category": "Entertainment",
        "rating": 4.9,
        "reviews": 15234
    },
    "spotify": {
        "id": "spotify",
        "name": "SPOTIFY",
        "emoji": "🎵",
        "full_emoji": "🎵🎧",
        "description": "🎧 *Spotify Gift Card*\n\n✅ Music Streaming\n✅ Instant email delivery\n✅ Ad-free music\n✅ Download songs\n\n🎯 *Best for:* Music, Podcasts",
        "long_description": "Spotify Gift Cards can be used to get Spotify Premium and enjoy ad-free music with offline downloads.",
        "delivery": "📧 *Instant Email Delivery*",
        "validity": "📅 *1 Year*",
        "terms": "📋 Valid on Spotify Premium",
        "popular": False,
        "featured": True,
        "discount": "70% OFF",
        "brand_color": "#1DB954",
        "icon": "🎧",
        "category": "Music",
        "rating": 4.8,
        "reviews": 11234
    },
    "dream11": {
        "id": "dream11",
        "name": "DREAM11",
        "emoji": "🏏",
        "full_emoji": "🏏🎯",
        "description": "🎯 *Dream11 Gift Card*\n\n✅ Fantasy Sports\n✅ Instant email delivery\n✅ Cricket, Football & more\n✅ Win real cash\n\n🎯 *Best for:* Sports, Fantasy Games",
        "long_description": "Dream11 Gift Cards can be used to join fantasy leagues and win real cash prizes in cricket, football, and more.",
        "delivery": "📧 *Instant Email Delivery*",
        "validity": "📅 *6 Months*",
        "terms": "📋 Valid on Dream11 platform",
        "popular": False,
        "featured": False,
        "discount": "70% OFF",
        "brand_color": "#0F172A",
        "icon": "🎯",
        "category": "Gaming",
        "rating": 4.6,
        "reviews": 8234
    },
    # Add more cards
    "ajio": {
        "id": "ajio",
        "name": "AJIO",
        "emoji": "👕",
        "full_emoji": "👕🛍️",
        "description": "👕 *AJIO Gift Card*\n\n✅ Fashion & Lifestyle\n✅ Instant email delivery\n✅ Latest trends\n✅ Great discounts\n\n🎯 *Best for:* Fashion, Clothing",
        "long_description": "AJIO Gift Cards can be used to purchase fashion and lifestyle products from top brands.",
        "delivery": "📧 *Instant Email Delivery*",
        "validity": "📅 *1 Year*",
        "terms": "📋 Valid on AJIO products",
        "popular": False,
        "featured": False,
        "discount": "80% OFF",
        "brand_color": "#E65F5F",
        "icon": "👕",
        "category": "Fashion",
        "rating": 4.4,
        "reviews": 3456
    },
    "croma": {
        "id": "croma",
        "name": "CROMA",
        "emoji": "💻",
        "full_emoji": "💻🖥️",
        "description": "💻 *Croma Gift Card*\n\n✅ Electronics & Appliances\n✅ Instant email delivery\n✅ Latest gadgets\n✅ Trusted brand\n\n🎯 *Best for:* Electronics, Gadgets",
        "long_description": "Croma Gift Cards can be used to purchase electronics, appliances, and gadgets from Croma stores.",
        "delivery": "📧 *Instant Email Delivery*",
        "validity": "📅 *1 Year*",
        "terms": "📋 Valid on Croma products",
        "popular": False,
        "featured": False,
        "discount": "75% OFF",
        "brand_color": "#E31837",
        "icon": "💻",
        "category": "Electronics",
        "rating": 4.5,
        "reviews": 4567
    },
    "pvr": {
        "id": "pvr",
        "name": "PVR",
        "emoji": "🎥",
        "full_emoji": "🎥🍿",
        "description": "🍿 *PVR Gift Card*\n\n✅ Movie Tickets\n✅ Instant email delivery\n✅ Book any movie\n✅ Premium experience\n\n🎯 *Best for:* Movies, Entertainment",
        "long_description": "PVR Gift Cards can be used to book movie tickets at any PVR Cinemas across India.",
        "delivery": "📧 *Instant Email Delivery*",
        "validity": "📅 *6 Months*",
        "terms": "📋 Valid on PVR tickets",
        "popular": False,
        "featured": False,
        "discount": "70% OFF",
        "brand_color": "#E31B23",
        "icon": "🎥",
        "category": "Entertainment",
        "rating": 4.7,
        "reviews": 6789
    },
    "uber": {
        "id": "uber",
        "name": "UBER",
        "emoji": "🚗",
        "full_emoji": "🚗🌆",
        "description": "🚗 *Uber Gift Card*\n\n✅ Rides & Travel\n✅ Instant email delivery\n✅ Valid across India\n✅ Easy to use\n\n🎯 *Best for:* Travel, Commute",
        "long_description": "Uber Gift Cards can be used for Uber rides across India. Perfect for daily commute and travel.",
        "delivery": "📧 *Instant Email Delivery*",
        "validity": "📅 *1 Year*",
        "terms": "📋 Valid on Uber rides",
        "popular": False,
        "featured": False,
        "discount": "75% OFF",
        "brand_color": "#000000",
        "icon": "🚗",
        "category": "Travel",
        "rating": 4.6,
        "reviews": 7890
    },
    "swiggy": {
        "id": "swiggy",
        "name": "SWIGGY",
        "emoji": "🍴",
        "full_emoji": "🍴🍛",
        "description": "🍛 *Swiggy Gift Card*\n\n✅ Food Delivery\n✅ Instant email delivery\n✅ 1000+ restaurants\n✅ Fast delivery\n\n🎯 *Best for:* Food, Dining",
        "long_description": "Swiggy Gift Cards can be used to order food from thousands of restaurants across India.",
        "delivery": "📧 *Instant Email Delivery*",
        "validity": "📅 *6 Months*",
        "terms": "📋 Valid on Swiggy orders",
        "popular": False,
        "featured": False,
        "discount": "80% OFF",
        "brand_color": "#FC8019",
        "icon": "🍛",
        "category": "Food",
        "rating": 4.8,
        "reviews": 9234
    }
})

# Price configuration with multiple denominations
PRICES = {
    500: 100,
    1000: 200,
    2000: 400,
    3000: 600,
    5000: 1000,
    10000: 2000
}

AVAILABLE_DENOMINATIONS = [500, 1000, 2000, 3000, 5000, 10000]

# ===========================================================================
# SETUP LOGGING WITH COLORS AND ROTATION
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
    logger.setLevel(logging.DEBUG)
    
    # File handler for all logs with rotation
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        log_dir / config.LOG_FILE,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter('%(asctime)s | %(levelname)-8s | %(name)s | %(message)s')
    file_handler.setFormatter(file_format)
    
    # File handler for errors only
    error_handler = RotatingFileHandler(
        log_dir / config.ERROR_LOG,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
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
# DATABASE MANAGER - ULTIMATE THREAD-SAFE VERSION
# ===========================================================================

class DatabaseManager:
    """Ultimate thread-safe database manager with connection pooling and automatic backups"""
    
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
        self._connection_pool = Queue(maxsize=20)
        self._pool_size = 10
        self._init_pool()
        
        # Initialize database
        self._init_database()
        
        # Start auto-backup thread
        if config.ENABLE_AUTO_BACKUP:
            self._start_auto_backup()
        
        logger.info("✅ Database Manager initialized with connection pooling")
    
    def _init_pool(self):
        """Initialize connection pool"""
        for i in range(self._pool_size):
            conn = sqlite3.connect(self.db_path, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA cache_size = 10000")
            conn.execute("PRAGMA temp_store = MEMORY")
            self._connection_pool.put(conn)
    
    @contextmanager
    def get_connection(self):
        """Get connection from pool with automatic return"""
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
        """Initialize database with all tables and indexes"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            # ===== USERS TABLE =====
            c.execute('''CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                email TEXT,
                balance INTEGER DEFAULT 0,
                bonus_balance INTEGER DEFAULT 0,
                total_recharged INTEGER DEFAULT 0,
                total_spent INTEGER DEFAULT 0,
                total_purchases INTEGER DEFAULT 0,
                total_referrals INTEGER DEFAULT 0,
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
                notifications TEXT DEFAULT '{}',
                notes TEXT,
                is_verified INTEGER DEFAULT 0,
                verification_token TEXT,
                FOREIGN KEY (referred_by) REFERENCES users(user_id)
            )''')
            
            # Create indexes for performance
            c.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_users_last_active ON users(last_active)")
            
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
            
            # Indexes
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
                card_name TEXT NOT NULL,
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
            
            # Indexes
            c.execute("CREATE INDEX IF NOT EXISTS idx_purchases_user ON purchases(user_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_purchases_order ON purchases(order_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_purchases_status ON purchases(status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_purchases_timestamp ON purchases(timestamp)")
            
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
                notes TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (verified_by) REFERENCES users(user_id)
            )''')
            
            # Indexes
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
                category TEXT,
                status TEXT DEFAULT 'open',
                assigned_to INTEGER,
                response TEXT,
                response_time TIMESTAMP,
                metadata TEXT DEFAULT '{}',
                timestamp TIMESTAMP,
                updated_at TIMESTAMP,
                resolved_at TIMESTAMP,
                resolved_by INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (assigned_to) REFERENCES users(user_id),
                FOREIGN KEY (resolved_by) REFERENCES users(user_id)
            )''')
            
            # Indexes
            c.execute("CREATE INDEX IF NOT EXISTS idx_tickets_user ON support_tickets(user_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status ON support_tickets(status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_tickets_priority ON support_tickets(priority)")
            
            # ===== REFERRALS TABLE =====
            c.execute('''CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                referred_id INTEGER NOT NULL UNIQUE,
                referred_username TEXT,
                referred_name TEXT,
                bonus_amount INTEGER DEFAULT 10,
                status TEXT DEFAULT 'pending',
                timestamp TIMESTAMP,
                completed_at TIMESTAMP,
                bonus_paid INTEGER DEFAULT 0,
                FOREIGN KEY (referrer_id) REFERENCES users(user_id),
                FOREIGN KEY (referred_id) REFERENCES users(user_id)
            )''')
            
            # Indexes
            c.execute("CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_referrals_status ON referrals(status)")
            
            # ===== FEEDBACK TABLE =====
            c.execute('''CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                message TEXT,
                category TEXT,
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
                priority INTEGER DEFAULT 1,
                read INTEGER DEFAULT 0,
                read_at TIMESTAMP,
                action_url TEXT,
                image_url TEXT,
                timestamp TIMESTAMP,
                expiry TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )''')
            
            # Indexes
            c.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(read)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_notifications_expiry ON notifications(expiry)")
            
            # ===== BANNED_USERS TABLE =====
            c.execute('''CREATE TABLE IF NOT EXISTS banned_users (
                user_id INTEGER PRIMARY KEY,
                reason TEXT,
                banned_by INTEGER,
                banned_at TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (banned_by) REFERENCES users(user_id)
            )''')
            
            # ===== SETTINGS TABLE =====
            c.execute('''CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                type TEXT DEFAULT 'string',
                description TEXT,
                updated_at TIMESTAMP,
                updated_by INTEGER
            )''')
            
            # ===== STATISTICS TABLE =====
            c.execute('''CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE,
                new_users INTEGER DEFAULT 0,
                active_users INTEGER DEFAULT 0,
                transactions INTEGER DEFAULT 0,
                revenue INTEGER DEFAULT 0,
                purchases INTEGER DEFAULT 0,
                verifications INTEGER DEFAULT 0,
                support_tickets INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}'
            )''')
            
            # Insert default settings
            default_settings = [
                ('bot_name', config.BOT_NAME, 'string', 'Bot display name'),
                ('min_recharge', str(config.MIN_RECHARGE), 'int', 'Minimum recharge amount'),
                ('max_recharge', str(config.MAX_RECHARGE), 'int', 'Maximum recharge amount'),
                ('fee_percent', str(config.FEE_PERCENT), 'int', 'Fee percentage'),
                ('fee_threshold', str(config.FEE_THRESHOLD), 'int', 'Fee threshold amount'),
                ('upi_id', config.UPI_ID, 'string', 'UPI ID for payments'),
                ('referral_bonus', str(config.REFERRAL_BONUS), 'int', 'Referral bonus amount'),
                ('welcome_bonus', str(config.WELCOME_BONUS), 'int', 'Welcome bonus amount'),
                ('maintenance_mode', '0', 'bool', 'Maintenance mode status'),
                ('maintenance_message', 'Bot under maintenance', 'text', 'Maintenance message'),
                ('welcome_message', 'Welcome to Gift Card Bot!', 'text', 'Welcome message'),
                ('support_message', 'Contact support for help', 'text', 'Support message'),
                ('terms_and_conditions', 'Terms and conditions...', 'text', 'Terms and conditions'),
                ('privacy_policy', 'Privacy policy...', 'text', 'Privacy policy'),
                ('about_us', 'About Gift Card Bot...', 'text', 'About us'),
                ('contact_email', config.SUPPORT_EMAIL, 'string', 'Contact email'),
                ('contact_website', config.WEBSITE, 'string', 'Website'),
                ('currency_symbol', '₹', 'string', 'Currency symbol'),
                ('currency_code', 'INR', 'string', 'Currency code'),
                ('timezone', 'Asia/Kolkata', 'string', 'Timezone')
            ]
            
            for key, value, type_, desc in default_settings:
                c.execute(
                    "INSERT OR IGNORE INTO settings (key, value, type, description, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (key, value, type_, desc, datetime.now().isoformat())
                )
            
            conn.commit()
            logger.info("✅ Database tables initialized with all indexes")
    
    def _start_auto_backup(self):
        """Start automatic backup thread"""
        def backup_worker():
            while True:
                time.sleep(config.BACKUP_INTERVAL)
                try:
                    self.backup_database()
                except Exception as e:
                    logger.error(f"❌ Auto backup error: {e}")
        
        thread = threading.Thread(target=backup_worker, daemon=True)
        thread.start()
        logger.info("✅ Auto backup thread started")
    
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
                    logger.info(f"🗑️ Removed old backup: {backup}")
            
            return str(backup_path)
        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            return None
    
    def optimize_database(self):
        """Optimize database (VACUUM, ANALYZE)"""
        try:
            with self.get_connection() as conn:
                conn.execute("VACUUM")
                conn.execute("ANALYZE")
            logger.info("✅ Database optimized")
            return True
        except Exception as e:
            logger.error(f"❌ Database optimization failed: {e}")
            return False
    
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
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = c.fetchone()
            return dict(row) if row else None
    
    def get_user_by_referral(self, code: str) -> Optional[Dict]:
        """Get user by referral code"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE referral_code = ?", (code,))
            row = c.fetchone()
            return dict(row) if row else None
    
    def create_user(self, user_id: int, username: str = None, first_name: str = None, 
                   last_name: str = None, referred_by: int = None) -> Dict:
        """Create new user with optional referral"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            # Generate unique referral code
            referral_code = hashlib.md5(f"{user_id}{datetime.now()}{secrets.token_hex(4)}".encode()).hexdigest()[:10]
            
            now = datetime.now().isoformat()
            
            c.execute('''INSERT OR IGNORE INTO users 
                (user_id, username, first_name, last_name, referral_code, referred_by, join_date, last_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (user_id, username, first_name, last_name, referral_code, referred_by, now, now))
            
            # Add welcome bonus if enabled
            if config.ENABLE_WELCOME_BONUS and config.WELCOME_BONUS > 0:
                c.execute('''UPDATE users SET balance = balance + ? WHERE user_id = ?''',
                         (config.WELCOME_BONUS, user_id))
                
                # Record welcome bonus transaction
                tx_id = f"WEL{datetime.now().strftime('%y%m%d%H%M%S')}{random.randint(1000, 9999)}"
                c.execute('''INSERT INTO transactions 
                    (user_id, transaction_id, amount, type, status, description, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (user_id, tx_id, config.WELCOME_BONUS, 'bonus', 'completed', 
                     'Welcome bonus', now))
            
            conn.commit()
            
            return self.get_user(user_id)
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        """Update user fields"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            fields = []
            values = []
            for key, value in kwargs.items():
                if key not in ['user_id', 'referral_code', 'join_date']:
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
    
    def get_balance(self, user_id: int) -> int:
        """Get user balance"""
        user = self.get_user(user_id)
        return user['balance'] if user else 0
    
    def get_total_balance(self) -> int:
        """Get total balance of all users"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT SUM(balance) FROM users")
            return c.fetchone()[0] or 0
    
    def update_balance(self, user_id: int, amount: int, transaction_type: str, **kwargs) -> bool:
        """Update user balance and record transaction"""
        with self.get_connection() as conn:
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
                    c.execute("UPDATE users SET total_purchases = total_purchases + 1 WHERE user_id = ?",
                             (user_id,))
                
                conn.commit()
                return True
                
            except Exception as e:
                logger.error(f"❌ Balance update error: {e}")
                conn.rollback()
                return False
    
    # ===== TRANSACTION METHODS =====
    
    def get_transactions(self, user_id: int, limit: int = 10, offset: int = 0) -> List[Dict]:
        """Get user transactions with pagination"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('''SELECT * FROM transactions 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ? OFFSET ?''', (user_id, limit, offset))
            return [dict(row) for row in c.fetchall()]
    
    def get_transaction_by_utr(self, utr: str) -> Optional[Dict]:
        """Get transaction by UTR"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM transactions WHERE utr = ?", (utr,))
            row = c.fetchone()
            return dict(row) if row else None
    
    def get_transaction_by_id(self, tx_id: str) -> Optional[Dict]:
        """Get transaction by transaction ID"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM transactions WHERE transaction_id = ?", (tx_id,))
            row = c.fetchone()
            return dict(row) if row else None
    
    # ===== PURCHASE METHODS =====
    
    def create_purchase(self, user_id: int, card_type: str, card_name: str, 
                       value: int, price: int, email: str) -> str:
        """Create purchase record"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            # Generate order ID
            order_id = f"GC{datetime.now().strftime('%y%m%d%H%M%S')}{random.randint(1000, 9999)}"
            
            c.execute('''INSERT INTO purchases 
                (user_id, order_id, card_type, card_name, card_value, price, email, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (user_id, order_id, card_type, card_name, value, price, email, datetime.now().isoformat()))
            
            conn.commit()
            return order_id
    
    def get_purchases(self, user_id: int, limit: int = 10, offset: int = 0) -> List[Dict]:
        """Get user purchases with pagination"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('''SELECT * FROM purchases 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ? OFFSET ?''', (user_id, limit, offset))
            return [dict(row) for row in c.fetchall()]
    
    def get_purchase_by_order(self, order_id: str) -> Optional[Dict]:
        """Get purchase by order ID"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM purchases WHERE order_id = ?", (order_id,))
            row = c.fetchone()
            return dict(row) if row else None
    
    # ===== VERIFICATION METHODS =====
    
    def create_verification(self, user_id: int, amount: int, fee: int, final: int, 
                           utr: str, screenshot: str) -> str:
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
    
    def get_pending_verifications(self, limit: int = 50) -> List[Dict]:
        """Get all pending verifications"""
        with self.get_connection() as conn:
            c = conn.cursor()
            now = datetime.now().isoformat()
            c.execute('''SELECT * FROM verifications 
                WHERE status = 'pending' AND expires_at > ?
                ORDER BY timestamp DESC
                LIMIT ?''', (now, limit))
            return [dict(row) for row in c.fetchall()]
    
    def get_verification(self, verification_id: str) -> Optional[Dict]:
        """Get verification by ID"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM verifications WHERE verification_id = ?", (verification_id,))
            row = c.fetchone()
            return dict(row) if row else None
    
    def approve_verification(self, verification_id: str, admin_id: int, notes: str = None) -> bool:
        """Approve payment verification"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            try:
                # Get verification
                c.execute("SELECT * FROM verifications WHERE verification_id = ?", (verification_id,))
                row = c.fetchone()
                if not row:
                    return False
                
                verification = dict(row)
                
                # Update verification status
                c.execute('''UPDATE verifications 
                    SET status = 'approved', verified_by = ?, verified_at = ?, notes = ?
                    WHERE verification_id = ?''',
                    (admin_id, datetime.now().isoformat(), notes, verification_id))
                
                # Update user balance
                self.update_balance(
                    verification['user_id'],
                    verification['final_amount'],
                    'credit',
                    payment_method='UPI',
                    utr=verification['utr'],
                    fee=verification['fee'],
                    final_amount=verification['final_amount'],
                    description='UPI Recharge Approved'
                )
                
                conn.commit()
                return True
                
            except Exception as e:
                logger.error(f"❌ Approval error: {e}")
                conn.rollback()
                return False
    
    def reject_verification(self, verification_id: str, admin_id: int, reason: str = None) -> bool:
        """Reject payment verification"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            try:
                c.execute('''UPDATE verifications 
                    SET status = 'rejected', verified_by = ?, verified_at = ?, notes = ?
                    WHERE verification_id = ?''',
                    (admin_id, datetime.now().isoformat(), reason, verification_id))
                
                conn.commit()
                return c.rowcount > 0
                
            except Exception as e:
                logger.error(f"❌ Rejection error: {e}")
                return False
    
    # ===== SUPPORT METHODS =====
    
    def create_support_ticket(self, user_id: int, message: str, subject: str = None, 
                             priority: int = 1, category: str = None) -> str:
        """Create support ticket"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            # Generate ticket ID
            ticket_id = f"TKT{datetime.now().strftime('%y%m%d%H%M%S')}{random.randint(1000, 9999)}"
            
            now = datetime.now().isoformat()
            
            c.execute('''INSERT INTO support_tickets 
                (ticket_id, user_id, subject, message, priority, category, timestamp, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (ticket_id, user_id, subject, message, priority, category, now, now))
            
            conn.commit()
            return ticket_id
    
    def get_open_tickets(self, limit: int = 50) -> List[Dict]:
        """Get all open support tickets"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('''SELECT * FROM support_tickets 
                WHERE status = 'open' 
                ORDER BY priority DESC, timestamp ASC
                LIMIT ?''', (limit,))
            return [dict(row) for row in c.fetchall()]
    
    def get_user_tickets(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get user's support tickets"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('''SELECT * FROM support_tickets 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?''', (user_id, limit))
            return [dict(row) for row in c.fetchall()]
    
    def update_ticket(self, ticket_id: str, **kwargs) -> bool:
        """Update support ticket"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            fields = []
            values = []
            for key, value in kwargs.items():
                fields.append(f"{key} = ?")
                values.append(value)
            
            fields.append("updated_at = ?")
            values.append(datetime.now().isoformat())
            values.append(ticket_id)
            
            query = f"UPDATE support_tickets SET {', '.join(fields)} WHERE ticket_id = ?"
            
            c.execute(query, values)
            conn.commit()
            
            return c.rowcount > 0
    
    # ===== REFERRAL METHODS =====
    
    def process_referral(self, referrer_id: int, referred_id: int, referred_name: str = None) -> bool:
        """Process referral bonus"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            try:
                # Check if already referred
                c.execute("SELECT * FROM referrals WHERE referred_id = ?", (referred_id,))
                if c.fetchone():
                    return False
                
                # Get referred user's username
                referred = self.get_user(referred_id)
                referred_username = referred.get('username') if referred else None
                
                now = datetime.now().isoformat()
                
                # Create referral record
                c.execute('''INSERT INTO referrals 
                    (referrer_id, referred_id, referred_username, referred_name, timestamp)
                    VALUES (?, ?, ?, ?, ?)''',
                    (referrer_id, referred_id, referred_username, referred_name, now))
                
                # Give bonus to referrer
                bonus = config.REFERRAL_BONUS
                self.update_balance(
                    referrer_id,
                    bonus,
                    'referral',
                    description=f'Referral bonus for user {referred_id}'
                )
                
                # Update referrer's total referrals
                c.execute("UPDATE users SET total_referrals = total_referrals + 1 WHERE user_id = ?",
                         (referrer_id,))
                
                conn.commit()
                return True
                
            except Exception as e:
                logger.error(f"❌ Referral error: {e}")
                return False
    
    def get_referrals(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Get user's referrals"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('''SELECT * FROM referrals 
                WHERE referrer_id = ?
                ORDER BY timestamp DESC 
                LIMIT ?''', (user_id, limit))
            return [dict(row) for row in c.fetchall()]
    
    def get_referral_stats(self, user_id: int) -> Dict:
        """Get referral statistics"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            # Total referrals
            c.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
            total = c.fetchone()[0]
            
            # Completed referrals (where referred user has made a purchase)
            c.execute('''SELECT COUNT(*) FROM referrals r
                JOIN purchases p ON r.referred_id = p.user_id
                WHERE r.referrer_id = ?''', (user_id,))
            completed = c.fetchone()[0]
            
            # Total bonus earned
            c.execute("SELECT SUM(bonus_amount) FROM referrals WHERE referrer_id = ? AND bonus_paid = 1",
                     (user_id,))
            bonus = c.fetchone()[0] or 0
            
            return {
                'total': total,
                'completed': completed,
                'pending': total - completed,
                'bonus': bonus
            }
    
    # ===== NOTIFICATION METHODS =====
    
    def add_notification(self, user_id: int, title: str, message: str, 
                        type: str = 'info', priority: int = 1, expiry: datetime = None) -> int:
        """Add notification for user"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            expiry_str = expiry.isoformat() if expiry else None
            
            c.execute('''INSERT INTO notifications 
                (user_id, title, message, type, priority, expiry, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (user_id, title, message, type, priority, expiry_str, datetime.now().isoformat()))
            
            conn.commit()
            return c.lastrowid
    
    def get_user_notifications(self, user_id: int, unread_only: bool = True, limit: int = 20) -> List[Dict]:
        """Get user notifications"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            query = "SELECT * FROM notifications WHERE user_id = ?"
            params = [user_id]
            
            if unread_only:
                query += " AND read = 0"
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            c.execute(query, params)
            return [dict(row) for row in c.fetchall()]
    
    def mark_notification_read(self, notification_id: int) -> bool:
        """Mark notification as read"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('''UPDATE notifications 
                SET read = 1, read_at = ? 
                WHERE id = ?''',
                (datetime.now().isoformat(), notification_id))
            conn.commit()
            return c.rowcount > 0
    
    def mark_all_read(self, user_id: int) -> int:
        """Mark all notifications as read for user"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('''UPDATE notifications 
                SET read = 1, read_at = ? 
                WHERE user_id = ? AND read = 0''',
                (datetime.now().isoformat(), user_id))
            conn.commit()
            return c.rowcount
    
    # ===== STATISTICS METHODS =====
    
    def get_statistics(self) -> Dict:
        """Get comprehensive bot statistics"""
        with self.get_connection() as conn:
            c = conn.cursor()
            stats = {}
            
            # User statistics
            c.execute("SELECT COUNT(*) FROM users")
            stats['total_users'] = c.fetchone()[0]
            
            today = datetime.now().date().isoformat()
            c.execute("SELECT COUNT(*) FROM users WHERE date(last_active) = ?", (today,))
            stats['active_today'] = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM users WHERE date(join_date) = ?", (today,))
            stats['new_today'] = c.fetchone()[0]
            
            # Transaction statistics
            c.execute("SELECT COUNT(*) FROM transactions")
            stats['total_transactions'] = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM transactions WHERE date(timestamp) = ?", (today,))
            stats['transactions_today'] = c.fetchone()[0]
            
            c.execute("SELECT SUM(amount) FROM transactions WHERE type = 'credit'")
            stats['total_revenue'] = c.fetchone()[0] or 0
            
            c.execute("SELECT SUM(amount) FROM transactions WHERE type = 'credit' AND date(timestamp) = ?", (today,))
            stats['revenue_today'] = c.fetchone()[0] or 0
            
            # Purchase statistics
            c.execute("SELECT COUNT(*) FROM purchases")
            stats['total_purchases'] = c.fetchone()[0]
            
            c.execute("SELECT SUM(price) FROM purchases")
            stats['total_spent'] = c.fetchone()[0] or 0
            
            c.execute("SELECT COUNT(*) FROM purchases WHERE date(timestamp) = ?", (today,))
            stats['purchases_today'] = c.fetchone()[0]
            
            # Verification statistics
            c.execute("SELECT COUNT(*) FROM verifications WHERE status = 'pending'")
            stats['pending_verifications'] = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM verifications WHERE status = 'approved' AND date(verified_at) = ?", (today,))
            stats['approved_today'] = c.fetchone()[0]
            
            # Support statistics
            c.execute("SELECT COUNT(*) FROM support_tickets WHERE status = 'open'")
            stats['open_tickets'] = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM support_tickets WHERE date(timestamp) = ?", (today,))
            stats['new_tickets'] = c.fetchone()[0]
            
            # Financial statistics
            c.execute("SELECT SUM(balance) FROM users")
            stats['total_balance'] = c.fetchone()[0] or 0
            
            c.execute("SELECT AVG(balance) FROM users")
            stats['avg_balance'] = c.fetchone()[0] or 0
            
            # Referral statistics
            c.execute("SELECT COUNT(*) FROM referrals")
            stats['total_referrals'] = c.fetchone()[0]
            
            c.execute("SELECT SUM(bonus_amount) FROM referrals WHERE bonus_paid = 1")
            stats['total_bonus_paid'] = c.fetchone()[0] or 0
            
            return stats
    
    def update_daily_stats(self):
        """Update daily statistics"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            today = datetime.now().date().isoformat()
            
            # Get today's stats
            c.execute("SELECT COUNT(*) FROM users WHERE date(join_date) = ?", (today,))
            new_users = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM users WHERE date(last_active) = ?", (today,))
            active_users = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM transactions WHERE date(timestamp) = ?", (today,))
            transactions = c.fetchone()[0]
            
            c.execute("SELECT SUM(amount) FROM transactions WHERE type = 'credit' AND date(timestamp) = ?", (today,))
            revenue = c.fetchone()[0] or 0
            
            c.execute("SELECT COUNT(*) FROM purchases WHERE date(timestamp) = ?", (today,))
            purchases = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM verifications WHERE date(timestamp) = ?", (today,))
            verifications = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM support_tickets WHERE date(timestamp) = ?", (today,))
            support_tickets = c.fetchone()[0]
            
            # Insert or update daily stats
            c.execute('''INSERT OR REPLACE INTO statistics 
                (date, new_users, active_users, transactions, revenue, purchases, verifications, support_tickets)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (today, new_users, active_users, transactions, revenue, purchases, verifications, support_tickets))
            
            conn.commit()

# ===========================================================================
# CACHE MANAGER
# ===========================================================================

class CacheManager:
    """Thread-safe cache manager with TTL and LRU eviction"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self._cache = OrderedDict()
        self._timers = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
    
    def set(self, key: str, value: Any, ttl: int = None):
        """Set cache value with TTL"""
        with self._lock:
            # Evict oldest if at max size
            if len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
                self._evictions += 1
            
            self._cache[key] = value
            self._timers[key] = time.time() + (ttl or self._default_ttl)
    
    def get(self, key: str) -> Optional[Any]:
        """Get cache value if not expired"""
        with self._lock:
            if key in self._cache:
                if time.time() < self._timers.get(key, 0):
                    self._cache.move_to_end(key)
                    self._hits += 1
                    return self._cache[key]
                else:
                    self.delete(key)
                    self._evictions += 1
            self._misses += 1
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
            self._hits = 0
            self._misses = 0
            self._evictions = 0
    
    def cleanup(self):
        """Remove expired entries"""
        with self._lock:
            now = time.time()
            expired = [k for k, t in self._timers.items() if now >= t]
            for k in expired:
                self.delete(k)
                self._evictions += 1
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            return {
                'size': len(self._cache),
                'max_size': self._max_size,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': f"{hit_rate:.1f}%",
                'evictions': self._evictions
            }

# ===========================================================================
# RATE LIMITER
# ===========================================================================

class RateLimiter:
    """Advanced rate limiter with per-user limits and burst handling"""
    
    def __init__(self):
        self._user_requests = defaultdict(list)
        self._user_burst = defaultdict(int)
        self._lock = threading.Lock()
        self._limit = config.RATE_LIMIT
        self._burst_limit = 5
        self._window = 60  # 1 minute
    
    def is_allowed(self, user_id: int) -> bool:
        """Check if user is allowed to make request"""
        with self._lock:
            now = time.time()
            window_start = now - self._window
            
            # Clean old requests
            self._user_requests[user_id] = [
                t for t in self._user_requests[user_id] if t > window_start
            ]
            
            # Check rate limit
            if len(self._user_requests[user_id]) >= self._limit:
                return False
            
            # Check burst limit (requests in last 10 seconds)
            burst_start = now - 10
            burst_count = len([t for t in self._user_requests[user_id] if t > burst_start])
            if burst_count >= self._burst_limit:
                return False
            
            # Add request
            self._user_requests[user_id].append(now)
            return True
    
    def get_remaining(self, user_id: int) -> int:
        """Get remaining requests for user"""
        with self._lock:
            now = time.time()
            window_start = now - self._window
            recent = [t for t in self._user_requests[user_id] if t > window_start]
            return max(0, self._limit - len(recent))
    
    def get_reset_time(self, user_id: int) -> int:
        """Get time until rate limit resets"""
        with self._lock:
            if not self._user_requests[user_id]:
                return 0
            oldest = min(self._user_requests[user_id])
            reset_time = max(0, int(oldest + self._window - time.time()))
            return reset_time
    
    def reset(self, user_id: int):
        """Reset rate limit for user"""
        with self._lock:
            self._user_requests[user_id] = []
            self._user_burst[user_id] = 0

# ===========================================================================
# SESSION MANAGER
# ===========================================================================

class SessionManager:
    """Advanced session manager with timeout and persistence"""
    
    def __init__(self):
        self._sessions = {}
        self._lock = threading.Lock()
        self._timeout = config.SESSION_TIMEOUT
        self._cleanup_interval = 60
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start automatic cleanup thread"""
        def cleanup_worker():
            while True:
                time.sleep(self._cleanup_interval)
                self.cleanup()
        
        thread = threading.Thread(target=cleanup_worker, daemon=True)
        thread.start()
    
    def get_session(self, user_id: int) -> Dict:
        """Get or create user session"""
        with self._lock:
            if user_id not in self._sessions:
                self._sessions[user_id] = {
                    'data': {},
                    'created_at': time.time(),
                    'last_active': time.time(),
                    'expires_at': time.time() + self._timeout
                }
            else:
                self._sessions[user_id]['last_active'] = time.time()
                self._sessions[user_id]['expires_at'] = time.time() + self._timeout
            
            return self._sessions[user_id]['data']
    
    def update_session(self, user_id: int, data: Dict):
        """Update user session"""
        with self._lock:
            if user_id in self._sessions:
                self._sessions[user_id]['data'].update(data)
                self._sessions[user_id]['last_active'] = time.time()
                self._sessions[user_id]['expires_at'] = time.time() + self._timeout
    
    def clear_session(self, user_id: int):
        """Clear user session"""
        with self._lock:
            if user_id in self._sessions:
                del self._sessions[user_id]
    
    def get_session_data(self, user_id: int, key: str, default: Any = None) -> Any:
        """Get specific session data"""
        session = self.get_session(user_id)
        return session.get(key, default)
    
    def set_session_data(self, user_id: int, key: str, value: Any):
        """Set specific session data"""
        session = self.get_session(user_id)
        session[key] = value
        self.update_session(user_id, session)
    
    def cleanup(self):
        """Remove expired sessions"""
        with self._lock:
            now = time.time()
            expired = [
                uid for uid, sess in self._sessions.items()
                if now > sess['expires_at']
            ]
            for uid in expired:
                del self._sessions[uid]
            if expired:
                logger.info(f"🧹 Cleaned up {len(expired)} expired sessions")
    
    def get_stats(self) -> Dict:
        """Get session statistics"""
        with self._lock:
            return {
                'active_sessions': len(self._sessions),
                'timeout': self._timeout
            }

# ===========================================================================
# NOTIFICATION MANAGER
# ===========================================================================

class NotificationManager:
    """Manage user notifications"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
    
    async def send(self, user_id: int, title: str, message: str, 
                  type: str = 'info', priority: int = 1, buttons: List = None) -> bool:
        """Send notification to user"""
        try:
            # Format message
            emoji_map = {
                'info': 'ℹ️',
                'success': '✅',
                'warning': '⚠️',
                'error': '❌',
                'promotion': '🎁'
            }
            emoji = emoji_map.get(type, '📢')
            
            text = f"{emoji} *{title}*\n\n{message}"
            
            # Add buttons if provided
            reply_markup = None
            if buttons:
                keyboard = []
                for btn_text, callback in buttons:
                    keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback)])
                reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send message
            await self.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
            # Save to database
            self.db.add_notification(user_id, title, message, type, priority)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Notification error for user {user_id}: {e}")
            return False
    
    async def broadcast(self, title: str, message: str, type: str = 'info',
                       exclude: List[int] = None, delay: float = 0.05) -> Tuple[int, int]:
        """Broadcast to all users"""
        if exclude is None:
            exclude = []
        
        with self.db.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT user_id FROM users WHERE status = 'active'")
            users = [row[0] for row in c.fetchall()]
        
        sent = 0
        failed = 0
        
        for user_id in users:
            if user_id in exclude:
                continue
            
            if await self.send(user_id, title, message, type):
                sent += 1
            else:
                failed += 1
            
            await asyncio.sleep(delay)  # Rate limiting
        
        logger.info(f"📢 Broadcast complete: {sent} sent, {failed} failed")
        return sent, failed
    
    async def send_payment_approved(self, user_id: int, amount: int):
        """Send payment approved notification"""
        await self.send(
            user_id,
            "Payment Approved! ✅",
            f"Your payment of ₹{amount:,} has been approved and added to your balance.",
            'success'
        )
    
    async def send_payment_rejected(self, user_id: int, reason: str = None):
        """Send payment rejected notification"""
        message = "Your payment has been rejected."
        if reason:
            message += f"\n\nReason: {reason}"
        
        await self.send(
            user_id,
            "Payment Rejected ❌",
            message,
            'error'
        )
    
    async def send_purchase_success(self, user_id: int, card_name: str, amount: int, order_id: str):
        """Send purchase success notification"""
        await self.send(
            user_id,
            "Purchase Successful! 🎉",
            f"Your {card_name} gift card of ₹{amount:,} has been delivered.\n\nOrder ID: `{order_id}`",
            'success'
        )
    
    async def send_welcome_bonus(self, user_id: int, amount: int):
        """Send welcome bonus notification"""
        await self.send(
            user_id,
            "Welcome Bonus! 🎁",
            f"Thank you for joining! You've received a welcome bonus of ₹{amount:,}.",
            'promotion'
        )
    
    async def send_referral_bonus(self, user_id: int, amount: int, friend_name: str):
        """Send referral bonus notification"""
        await self.send(
            user_id,
            "Referral Bonus! 🎉",
            f"You've earned ₹{amount:,} because {friend_name} joined using your link!",
            'success'
        )

# ===========================================================================
# FORMATTER UTILITIES
# ===========================================================================

class Formatter:
    """Advanced formatting utilities"""
    
    @staticmethod
    def currency(amount: int) -> str:
        """Format amount with currency symbol and commas"""
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
        """Get human-readable relative time"""
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
            elif diff.days > 7:
                weeks = diff.days // 7
                return f"{weeks} week{'s' if weeks > 1 else ''} ago"
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
        """Truncate text to length with ellipsis"""
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
    def mask_phone(phone: str) -> str:
        """Mask phone number for privacy"""
        if len(phone) >= 10:
            return phone[:2] + '*' * (len(phone) - 4) + phone[-2:]
        return phone
    
    @staticmethod
    def progress_bar(current: int, total: int, width: int = 10) -> str:
        """Create progress bar"""
        if total == 0:
            return '░' * width
        
        filled = int(width * current / total)
        bar = '█' * filled + '░' * (width - filled)
        percentage = int(100 * current / total)
        
        return f"{bar} {percentage}%"
    
    @staticmethod
    def format_number(num: int) -> str:
        """Format number with K, M, B suffixes"""
        if num < 1000:
            return str(num)
        elif num < 1000000:
            return f"{num/1000:.1f}K"
        elif num < 1000000000:
            return f"{num/1000000:.1f}M"
        else:
            return f"{num/1000000000:.1f}B"
    
    @staticmethod
    def format_seconds(seconds: int) -> str:
        """Format seconds to human readable"""
        if seconds < 60:
            return f"{seconds} sec"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} min"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''}"
        else:
            days = seconds // 86400
            return f"{days} day{'s' if days > 1 else ''}"

# ===========================================================================
# VALIDATION UTILITIES
# ===========================================================================

class Validator:
    """Advanced validation utilities"""
    
    @staticmethod
    def email(email: str) -> bool:
        """Validate email address"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def utr(utr: str) -> bool:
        """Validate UTR number (12-22 alphanumeric)"""
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
    
    @staticmethod
    def ifsc(ifsc: str) -> bool:
        """Validate IFSC code"""
        pattern = r'^[A-Z]{4}0[A-Z0-9]{6}$'
        return re.match(pattern, ifsc) is not None
    
    @staticmethod
    def account_number(acc: str) -> bool:
        """Validate bank account number"""
        return 9 <= len(acc) <= 18 and acc.isdigit()
    
    @staticmethod
    def gst(gst: str) -> bool:
        """Validate GST number"""
        pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$'
        return re.match(pattern, gst) is not None
    
    @staticmethod
    def pan(pan: str) -> bool:
        """Validate PAN card"""
        pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
        return re.match(pattern, pan) is not None
    
    @staticmethod
    def aadhaar(aadhaar: str) -> bool:
        """Validate Aadhaar number"""
        pattern = r'^\d{12}$'
        return re.match(pattern, aadhaar) is not None

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

def vip_only(func):
    """Decorator to restrict to VIP users"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        db = DatabaseManager()
        db_user = db.get_user(user.id)
        
        if not db_user or db_user.get('role') not in ['admin', 'vip']:
            await update.message.reply_text(
                "👑 *VIP Only*\n\nThis feature is for VIP users only.\nContact admin to upgrade!",
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
            reset_time = limiter.get_reset_time(user.id)
            await update.message.reply_text(
                f"⚠️ *Rate Limited*\n\n"
                f"Please wait {Formatter.format_seconds(reset_time)}.\n"
                f"Remaining: {remaining} requests/minute",
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
        
        logger.info(f"👤 User {user.id} (@{user.username}) performed: {action}")
        
        try:
            result = await func(update, context, *args, **kwargs)
            logger.info(f"✅ Action {action} completed for user {user.id}")
            return result
        except Exception as e:
            logger.error(f"❌ Action {action} failed for user {user.id}: {e}")
            logger.error(traceback.format_exc())
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
            logger.error(traceback.format_exc())
            
            error_message = (
                "⚠️ *An error occurred*\n\n"
                "Please try again later.\n"
                "If the problem persists, contact support."
            )
            
            try:
                if update.callback_query:
                    await update.callback_query.edit_message_text(
                        error_message,
                        parse_mode=ParseMode.MARKDOWN
                    )
                elif update.message:
                    await update.message.reply_text(
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
        logger.error(f"❌ Membership check error for user {user_id}: {e}")
        return False

# ===========================================================================
# GLOBAL INSTANCES
# ===========================================================================

db = DatabaseManager()
cache = CacheManager()
session_manager = SessionManager()

# ===========================================================================
# START COMMAND
# ===========================================================================

@log_action
@rate_limit
@handle_errors
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    # Check if user is banned
    with db.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM banned_users WHERE user_id = ?", (user.id,))
        banned = c.fetchone()
        if banned:
            await update.message.reply_text(
                "🚫 *You are banned*\n\nContact admin for more information.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
    
    # Check for referral
    referred_by = None
    if context.args and context.args[0].startswith('ref_'):
        try:
            referrer_id = int(context.args[0].replace('ref_', ''))
            if referrer_id != user.id:
                referred_by = referrer_id
        except:
            pass
    
    # Get or create user
    db_user = db.get_user(user.id)
    if not db_user:
        db_user = db.create_user(
            user.id, 
            user.username, 
            user.first_name, 
            user.last_name,
            referred_by
        )
        logger.info(f"✅ New user registered: {user.id} - {user.first_name}")
        
        # Process referral if exists
        if referred_by:
            db.process_referral(referred_by, user.id, user.first_name)
            
            # Notify referrer
            try:
                await context.bot.send_message(
                    chat_id=referred_by,
                    text=f"🎉 *Referral Bonus!*\n\n{user.first_name} joined using your link!\n₹{config.REFERRAL_BONUS} added to your balance.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
    
    db.update_last_active(user.id)
    
    # Check maintenance mode
    with db.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key = 'maintenance_mode'")
        maintenance = c.fetchone()
        if maintenance and maintenance[0] == '1':
            c.execute("SELECT value FROM settings WHERE key = 'maintenance_message'")
            msg = c.fetchone()
            await update.message.reply_text(
                f"🔧 *Maintenance Mode*\n\n{msg[0] if msg else 'Bot under maintenance'}",
                parse_mode=ParseMode.MARKDOWN
            )
            return
    
    # Check channel membership
    is_member = await check_membership(user.id, context)
    
    if not is_member:
        # Welcome message for new users
        welcome_text = (
            f"✨ *WELCOME TO {config.BOT_NAME}* ✨\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👋 *Hello {user.first_name}!*\n\n"
            f"🎁 *Get Gift Cards at 80% OFF!*\n"
            f"• 10+ Brands Available\n"
            f"• Instant Email Delivery\n"
            f"• 24/7 Support\n"
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
    balance = db.get_balance(user.id)
    
    # Get welcome message from settings
    with db.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key = 'welcome_message'")
        welcome_msg = c.fetchone()
    
    menu_text = (
        f"🎉 *WELCOME BACK TO {config.BOT_NAME}!* 🎉\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *User:* {user.first_name}\n"
        f"💰 *Balance:* {Formatter.currency(balance)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"*What would you like to do today?* ⬇️"
    )
    
    keyboard = [
        [InlineKeyboardButton("🎁 GIFT CARDS", callback_data="giftcard")],
        [InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")],
        [InlineKeyboardButton("💳 MY WALLET", callback_data="wallet")],
        [InlineKeyboardButton("🆘 SUPPORT", callback_data="support")],
        [InlineKeyboardButton("📊 LIVE PROOFS", callback_data="proofs")],
        [InlineKeyboardButton("🎁 REFERRAL PROGRAM", callback_data="referral")],
        [InlineKeyboardButton("👤 MY ACCOUNT", callback_data="account")]
    ]
    
    await update.message.reply_text(
        menu_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===========================================================================
# BUTTON HANDLER - MAIN NAVIGATION
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
    
    db.update_last_active(user.id)
    
    # ===== VERIFY BUTTON =====
    if data == "verify":
        is_member = await check_membership(user.id, context)
        
        if is_member:
            balance = db.get_balance(user.id)
            
            success_text = (
                f"✅ *VERIFICATION SUCCESSFUL!*\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👋 *Welcome {user.first_name}!*\n"
                f"💰 *Balance:* {Formatter.currency(balance)}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"*You now have full access to:*\n"
                f"• 🎁 10+ Gift Card Brands\n"
                f"• 💰 Instant UPI Recharge\n"
                f"• ⚡ 24/7 Auto Delivery\n"
                f"• 📊 Live Proofs Channel\n"
                f"• 🎁 Referral Bonus Program\n\n"
                f"⬇️ *Choose an option:*"
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
        balance = db.get_balance(user.id)
        
        main_text = (
            f"🏠 *MAIN MENU*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *User:* {user.first_name}\n"
            f"💰 *Balance:* {Formatter.currency(balance)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"*Please select an option:* ⬇️"
        )
        
        keyboard = [
            [InlineKeyboardButton("🎁 GIFT CARDS", callback_data="giftcard")],
            [InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")],
            [InlineKeyboardButton("💳 MY WALLET", callback_data="wallet")],
            [InlineKeyboardButton("🆘 SUPPORT", callback_data="support")],
            [InlineKeyboardButton("📊 PROOFS", callback_data="proofs")],
            [InlineKeyboardButton("🎁 REFERRAL", callback_data="referral")],
            [InlineKeyboardButton("👤 ACCOUNT", callback_data="account")]
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
        featured_cards = [(cid, card) for cid, card in GIFT_CARDS.items() if card.get('featured', False) and not card.get('popular', False)]
        other_cards = [(cid, card) for cid, card in GIFT_CARDS.items() if not card.get('popular', False) and not card.get('featured', False)]
        
        keyboard = []
        
        # Add popular cards
        if popular_cards:
            for card_id, card in popular_cards:
                keyboard.append([InlineKeyboardButton(
                    f"{card['full_emoji']} {card['name']} ⭐🔥", 
                    callback_data=f"card_{card_id}"
                )])
        
        # Add separator
        if popular_cards and featured_cards:
            keyboard.append([InlineKeyboardButton("✨ *FEATURED* ✨", callback_data="ignore")])
        
        # Add featured cards
        if featured_cards:
            for card_id, card in featured_cards:
                keyboard.append([InlineKeyboardButton(
                    f"{card['full_emoji']} {card['name']} ✨", 
                    callback_data=f"card_{card_id}"
                )])
        
        # Add separator
        if (popular_cards or featured_cards) and other_cards:
            keyboard.append([InlineKeyboardButton("📌 *ALL CARDS* 📌", callback_data="ignore")])
        
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
            f"*Choose from 10+ premium brands:*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💳 *All cards delivered INSTANTLY on email*\n"
            f"⚡ *24/7 Automatic Delivery*\n"
            f"✅ *100% Working Codes*\n"
            f"🛡️ *100% Buyer Protection*\n\n"
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
        
        # Build price buttons in rows of 2
        keyboard = []
        row = []
        for i, denom in enumerate(AVAILABLE_DENOMINATIONS):
            if denom in PRICES:
                price = PRICES[denom]
                savings = denom - price
                savings_percent = int((savings / denom) * 100)
                
                button = InlineKeyboardButton(
                    f"₹{denom} → ₹{price} (-{savings_percent}%)", 
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
            f"{card['description']}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
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
        except ValueError:
            await query.edit_message_text("❌ Invalid amount")
            return
        
        card = GIFT_CARDS.get(card_id)
        if not card or value not in PRICES:
            await query.edit_message_text("❌ Card or amount not available")
            return
        
        price = PRICES[value]
        savings = value - price
        savings_percent = int((savings / value) * 100)
        
        balance = db.get_balance(user.id)
        
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
        
        # Store purchase data in session
        session_manager.set_session_data(user.id, 'purchase', {
            'card_id': card_id,
            'card_name': card['name'],
            'card_emoji': card['full_emoji'],
            'value': value,
            'price': price
        })
        
        # Show savings
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
            f"📱 *Account No:* `12345678901234`\n"
            f"🏧 *IFSC Code:* `HDFC0001234`\n"
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
        balance = db.get_balance(user.id)
        
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
            elif type_ == 'referral':
                trans_text += f"👥 *+{Formatter.currency(amount)}* (Referral, {time_str})\n"
        
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
            [InlineKeyboardButton("📜 FULL HISTORY", callback_data="history")],
            [InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            wallet_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== TRANSACTION HISTORY =====
    elif data == "history":
        transactions = db.get_transactions(user.id, 15)
        
        history_text = f"📜 *TRANSACTION HISTORY*\n\n"
        history_text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        if not transactions:
            history_text += "📭 No transactions yet\n"
        else:
            for t in transactions:
                amount = t['amount']
                type_ = t['type']
                status = t['status']
                time_str = Formatter.date(t['timestamp'], "%d %b %Y, %I:%M %p")
                
                status_emoji = "✅" if status == 'completed' else "⏳" if status == 'pending' else "❌"
                
                if type_ == 'credit':
                    history_text += f"{status_emoji} *+{Formatter.currency(amount)}* (Credit)\n"
                elif type_ == 'debit':
                    history_text += f"{status_emoji} *-{Formatter.currency(amount)}* (Purchase)\n"
                elif type_ == 'bonus':
                    history_text += f"🎁 *+{Formatter.currency(amount)}* (Welcome Bonus)\n"
                elif type_ == 'referral':
                    history_text += f"👥 *+{Formatter.currency(amount)}* (Referral Bonus)\n"
                
                history_text += f"   🕐 {time_str}\n\n"
        
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
            f"👤 *YOUR ACCOUNT*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 *User ID:* `{user.id}`\n"
            f"👤 *Name:* {db_user['first_name']} {db_user.get('last_name', '')}\n"
            f"📧 *Email:* {db_user.get('email', 'Not set')}\n"
            f"📱 *Phone:* {db_user.get('phone', 'Not set')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *Account Statistics:*\n"
            f"• 📅 Joined: {Formatter.date(db_user['join_date'], '%d %b %Y')}\n"
            f"• 🎁 Total Purchases: {total_purchases}\n"
            f"• 💰 Total Spent: {Formatter.currency(db_user['total_spent'])}\n"
            f"• 💳 Total Recharged: {Formatter.currency(db_user['total_recharged'])}\n"
            f"• 👥 Referrals: {db_user['total_referrals']}\n"
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
                time_str = Formatter.date(p['timestamp'], "%d %b %Y, %I:%M %p")
                purchases_text += (
                    f"• {p['card_type']} *₹{p['card_value']}*\n"
                    f"  🆔 Order: `{p['order_id']}`\n"
                    f"  📧 {Formatter.mask_email(p['email'])}\n"
                    f"  🕐 {time_str}\n\n"
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
        referral_stats = db.get_referral_stats(user.id)
        
        bot_username = (await context.bot.get_me()).username
        referral_link = f"https://t.me/{bot_username}?start=ref_{user.id}"
        
        referral_text = (
            f"🎁 *REFERRAL PROGRAM*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"*Earn ₹{config.REFERRAL_BONUS} for every friend!*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔗 *Your Personal Link:*\n"
            f"`{referral_link}`\n\n"
            f"📊 *Your Statistics:*\n"
            f"• 👥 Total Referrals: {referral_stats['total']}\n"
            f"• ✅ Completed: {referral_stats['completed']}\n"
            f"• ⏳ Pending: {referral_stats['pending']}\n"
            f"• 💰 Bonus Earned: {Formatter.currency(referral_stats['bonus'])}\n\n"
            f"📌 *How it works:*\n"
            f"1️⃣ Share your referral link\n"
            f"2️⃣ Friend joins using your link\n"
            f"3️⃣ You get ₹{config.REFERRAL_BONUS} instantly\n"
            f"4️⃣ Friend gets welcome bonus too!\n\n"
            f"*Start sharing now!* 🚀"
        )
        
        keyboard = [
            [InlineKeyboardButton("📋 COPY LINK", callback_data="copy_link")],
            [InlineKeyboardButton("👥 MY REFERRALS", callback_data="my_referrals")],
            [InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            referral_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== COPY LINK =====
    elif data == "copy_link":
        bot_username = (await context.bot.get_me()).username
        referral_link = f"https://t.me/{bot_username}?start=ref_{user.id}"
        
        await query.answer(f"Link copied! Share with friends.", show_alert=False)
        
        await query.edit_message_text(
            f"🔗 *Your Referral Link:*\n\n"
            f"`{referral_link}`\n\n"
            f"*Share this with your friends and earn ₹{config.REFERRAL_BONUS} each!*",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ===== MY REFERRALS =====
    elif data == "my_referrals":
        referrals = db.get_referrals(user.id, 20)
        
        referrals_text = f"👥 *YOUR REFERRALS*\n\n"
        referrals_text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        if not referrals:
            referrals_text += "📭 No referrals yet\n\nShare your link to start earning!"
        else:
            for r in referrals:
                time_str = Formatter.date(r['timestamp'], "%d %b %Y")
                status_emoji = "✅" if r['bonus_paid'] else "⏳"
                name = r['referred_name'] or f"User {r['referred_id']}"
                
                referrals_text += f"{status_emoji} • {name}\n"
                referrals_text += f"  🕐 {time_str}\n"
                if r['bonus_paid']:
                    referrals_text += f"  💰 +₹{r['bonus_amount']}\n"
                referrals_text += "\n"
        
        referrals_text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="referral")]]
        
        await query.edit_message_text(
            referrals_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
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
            f"   → Send screenshot with UTR to admin\n\n"
            f"4️⃣ *Card not received?*\n"
            f"   → Check spam folder, contact support\n\n"
            f"5️⃣ *How to refer friends?*\n"
            f"   → Get referral link from Referral section\n\n"
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
    
    # ===== IGNORE BUTTON =====
    elif data == "ignore":
        await query.answer()

# ===========================================================================
# AMOUNT HANDLER
# ===========================================================================

@log_action
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
    
    # Store in session
    session_manager.set_session_data(user.id, 'topup', {
        'amount': amount,
        'fee': fee,
        'final': final
    })
    
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
    
    return ConversationHandler.END

# ===========================================================================
# PAID BUTTON HANDLER
# ===========================================================================

@log_action
@handle_errors
async def handle_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle paid button click"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    # Get topup data from session
    topup_data = session_manager.get_session_data(user.id, 'topup')
    
    if not topup_data:
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

@log_action
@handle_errors
async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle screenshot for payment"""
    user = update.effective_user
    
    if not update.message.photo:
        await update.message.reply_text(
            "❌ *Please send a PHOTO*\n\n"
            "Send the screenshot of your payment.",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_SCREENSHOT
    
    # Store screenshot in session
    photo = update.message.photo[-1].file_id
    session_manager.set_session_data(user.id, 'screenshot', photo)
    
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

@log_action
@handle_errors
async def handle_utr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle UTR input for payment"""
    user = update.effective_user
    utr = update.message.text.strip()
    
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
    
    # Get data from session
    topup_data = session_manager.get_session_data(user.id, 'topup')
    screenshot = session_manager.get_session_data(user.id, 'screenshot')
    
    if not topup_data or not screenshot:
        await update.message.reply_text(
            "❌ *Session expired*\n\nPlease start over with /start",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    # Check for duplicate UTR
    existing = db.get_transaction_by_utr(utr)
    if existing:
        await update.message.reply_text(
            "❌ *Duplicate UTR*\n\n"
            "This UTR has already been submitted.\n"
            "Please check and try again.",
            parse_mode=ParseMode.MARKDOWN
        )
        return STATE_UTR
    
    # Create verification
    verification_id = db.create_verification(
        user.id,
        topup_data['amount'],
        topup_data['fee'],
        topup_data['final'],
        utr,
        screenshot
    )
    
    # Get user info
    db_user = db.get_user(user.id)
    
    # Create admin message
    caption = (
        f"🔔 *NEW PAYMENT VERIFICATION*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *User:* {user.first_name} {user.last_name or ''}\n"
        f"🆔 *ID:* `{user.id}`\n"
        f"👤 *Username:* @{user.username or 'N/A'}\n"
        f"📧 *Email:* {db_user.get('email', 'Not set')}\n"
        f"📱 *Phone:* {db_user.get('phone', 'Not set')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 *Amount:* {Formatter.currency(topup_data['amount'])}\n"
        f"💸 *Fee:* {Formatter.currency(topup_data['fee'])}\n"
        f"🎁 *Credit:* {Formatter.currency(topup_data['final'])}\n"
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
    session_manager.clear_session(user.id)
    
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

@log_action
@handle_errors
async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle email input for purchase"""
    user = update.effective_user
    email = update.message.text.strip()
    
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
    
    # Get purchase data from session
    purchase = session_manager.get_session_data(user.id, 'purchase')
    
    if not purchase:
        await update.message.reply_text(
            "❌ *Session expired*\n\nPlease start over with /start",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    balance = db.get_balance(user.id)
    
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
    session_manager.clear_session(user.id)
    
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
    
    return ConversationHandler.END

# ===========================================================================
# SUPPORT HANDLER
# ===========================================================================

@log_action
@handle_errors
async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle support message"""
    user = update.effective_user
    message = update.message.text.strip()
    
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
    
    if action == "approve":
        # Approve payment
        success = db.approve_verification(verification_id, config.ADMIN_ID)
        
        if success:
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n✅ *APPROVED BY ADMIN*",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Get verification details for notification
            verification = db.get_verification(verification_id)
            if verification:
                # Notify user
                try:
                    await context.bot.send_message(
                        chat_id=verification['user_id'],
                        text=(
                            f"✅ *PAYMENT APPROVED!*\n\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"*Amount:* {Formatter.currency(verification['final_amount'])} added to your balance.\n"
                            f"*UTR:* `{verification['utr']}`\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                            f"Thank you for using our service! 🙏"
                        ),
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
            
            # Notify admin
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
        reason = "Payment not verified"  # Could add reason input
        success = db.reject_verification(verification_id, config.ADMIN_ID)
        
        if success:
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n❌ *REJECTED BY ADMIN*",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Get verification details for notification
            verification = db.get_verification(verification_id)
            if verification:
                # Notify user
                try:
                    await context.bot.send_message(
                        chat_id=verification['user_id'],
                        text=(
                            f"❌ *PAYMENT REJECTED*\n\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"*UTR:* `{verification['utr']}`\n"
                            f"*Reason:* {reason}\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                            f"Please try again or contact support."
                        ),
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
            
            # Notify admin
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
    stats = db.get_statistics()
    cache_stats = cache.get_stats()
    session_stats = session_manager.get_stats()
    
    stats_text = (
        f"📊 *BOT STATISTICS*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 *Date:* {datetime.now().strftime('%d %b %Y, %I:%M %p')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"*👥 Users:*\n"
        f"• Total Users: {stats['total_users']:,}\n"
        f"• Active Today: {stats['active_today']}\n"
        f"• New Today: {stats['new_today']}\n\n"
        f"*💰 Financials:*\n"
        f"• Total Revenue: {Formatter.currency(stats['total_revenue'])}\n"
        f"• Revenue Today: {Formatter.currency(stats['revenue_today'])}\n"
        f"• Total Spent: {Formatter.currency(stats['total_spent'])}\n"
        f"• Total Balance: {Formatter.currency(stats['total_balance'])}\n"
        f"• Avg Balance: {Formatter.currency(stats['avg_balance'])}\n\n"
        f"*📊 Transactions:*\n"
        f"• Total: {stats['total_transactions']:,}\n"
        f"• Today: {stats['transactions_today']}\n"
        f"• Purchases: {stats['total_purchases']:,}\n"
        f"• Purchases Today: {stats['purchases_today']}\n\n"
        f"*⏳ Pending:*\n"
        f"• Verifications: {stats['pending_verifications']}\n"
        f"• Approved Today: {stats['approved_today']}\n"
        f"• Open Tickets: {stats['open_tickets']}\n"
        f"• New Tickets: {stats['new_tickets']}\n\n"
        f"*👥 Referrals:*\n"
        f"• Total: {stats['total_referrals']}\n"
        f"• Bonus Paid: {Formatter.currency(stats['total_bonus_paid'])}\n\n"
        f"*⚡ Performance:*\n"
        f"• Cache Hits: {cache_stats['hit_rate']}\n"
        f"• Active Sessions: {session_stats['active_sessions']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    await update.message.reply_text(
        stats_text,
        parse_mode=ParseMode.MARKDOWN
    )

@admin_only
async def admin_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to view pending verifications"""
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
    """Admin command to broadcast message to all users"""
    if not context.args:
        await update.message.reply_text(
            "📢 *BROADCAST*\n\n"
            "Usage: `/broadcast Your message here`\n\n"
            "Example: `/broadcast 🎉 New offer: 10% off on all cards!`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    message = " ".join(context.args)
    
    # Get all users
    with db.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE status = 'active'")
        users = [row[0] for row in c.fetchall()]
    
    if not users:
        await update.message.reply_text("❌ No active users found")
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
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*{config.BOT_NAME}*"
    )
    
    for user_id in users:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=broadcast_text,
                parse_mode=ParseMode.MARKDOWN
            )
            sent += 1
            await asyncio.sleep(0.05)  # Rate limit
        except Exception as e:
            failed += 1
            logger.error(f"❌ Broadcast to {user_id} failed: {e}")
        
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
            "🦸 Hero", "🦹 Storm", "🧚 Fairy", "🧛 Vamp", "🧟 Zombie",
            "👨‍🍳 Chef", "👩‍🍳 Chef", "👨‍🌾 Farmer", "👩‍🌾 Farmer", "👨‍🏫 Teacher",
            "👩‍🏫 Teacher", "👨‍⚖️ Judge", "👩‍⚖️ Judge", "👨‍⚕️ Doctor", "👩‍⚕️ Doctor"
        ]
        
        cards = [
            "🟦 AMAZON", "🟩 PLAY STORE", "🎟️ BOOKMYSHOW", 
            "🛍️ MYNTRA", "📦 FLIPKART", "🍕 ZOMATO", 
            "🛒 BIG BASKET", "🎮 GOOGLE PLAY", "🎬 NETFLIX", 
            "🎵 SPOTIFY", "💳 AMAZON PAY", "🏏 DREAM11",
            "🎁 GIFT VOUCHER", "🛍️ AJIO", "👕 MYNTRA",
            "📱 APPLE", "💻 DELL", "🎧 BOAT", "⌚ SAMSUNG",
            "🎮 XBOX", "🎮 PLAYSTATION", "📚 KINDLE", "☕ STARBUCKS",
            "🏦 HDFC", "💳 CREDIT CARD", "💰 PAYTM", "📱 PHONEPE"
        ]
        
        amounts = [500, 1000, 2000, 3000, 5000]
        
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
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            
            f"🏆 *TOP PURCHASE*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👑 *Premium User:* {name}\n"
            f"💎 *Premium Card:* {card}\n"
            f"💵 *Amount:* ₹{amount}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📧 *Email Delivery*\n"
            f"⚡ *Instant*\n"
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
        # Update daily statistics
        db.update_daily_stats()
        
        # Clean up cache
        cache.cleanup()
        
        # Clean up sessions
        session_manager.cleanup()
        
        # Create backup
        if config.ENABLE_AUTO_BACKUP:
            backup_path = db.backup_database()
            if backup_path:
                logger.info(f"✅ Auto backup created: {backup_path}")
        
        logger.info("✅ Cleanup job completed")
        
    except Exception as e:
        logger.error(f"❌ Cleanup job error: {e}")

# ===========================================================================
# CANCEL HANDLER
# ===========================================================================

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
        logger.error(traceback.format_exc())
        
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
        BotCommand("broadcast", "📢 Broadcast message (admin)"),
        BotCommand("backup", "💾 Create database backup (admin)"),
        BotCommand("optimize", "⚡ Optimize database (admin)")
    ]
    
    await application.bot.set_my_commands(commands)
    
    logger.info(f"✅ {config.BOT_NAME} v{config.BOT_VERSION} initialized successfully")

# ===========================================================================
# ADDITIONAL ADMIN COMMANDS
# ===========================================================================

@admin_only
async def admin_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to create database backup"""
    backup_path = db.backup_database()
    
    if backup_path:
        await update.message.reply_text(
            f"✅ *Backup created successfully!*\n\n"
            f"📁 `{backup_path}`",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            "❌ *Backup failed*\n\nPlease check logs.",
            parse_mode=ParseMode.MARKDOWN
        )

@admin_only
async def admin_optimize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to optimize database"""
    status_msg = await update.message.reply_text(
        "⚡ *Optimizing database...*",
        parse_mode=ParseMode.MARKDOWN
    )
    
    success = db.optimize_database()
    
    if success:
        await status_msg.edit_text(
            "✅ *Database optimized successfully!*",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await status_msg.edit_text(
            "❌ *Optimization failed*\n\nPlease check logs.",
            parse_mode=ParseMode.MARKDOWN
        )

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

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    logger.info("🛑 Shutting down bot...")
    sys.exit(0)

def main():
    """Main function"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Validate configuration
        config.validate()
        
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
        app.add_handler(CommandHandler("backup", admin_backup))
        app.add_handler(CommandHandler("optimize", admin_optimize))
        
        # ===== BUTTON HANDLER =====
        app.add_handler(CallbackQueryHandler(button_handler))
        
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
        logger.critical(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
