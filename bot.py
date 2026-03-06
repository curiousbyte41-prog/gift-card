#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
===============================================================================
GIFT CARD & RECHARGE BOT - RAILWAY OPTIMIZED EDITION
===============================================================================
A fully featured Telegram bot for selling gift cards and managing recharges
Optimized for Railway deployment with enhanced error handling

Version: 4.1.0 (Railway Stable)
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
import signal
import traceback

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
    """Centralized configuration management with Railway support"""
    
    # Bot Credentials - Use environment variables for Railway
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    ADMIN_ID = int(os.environ.get("ADMIN_ID", "6185091342"))
    
    # Channel Configuration - Use environment variables
    MAIN_CHANNEL = os.environ.get("MAIN_CHANNEL", "@gift_card_main")
    PROOF_CHANNEL = os.environ.get("PROOF_CHANNEL", "@gift_card_log")
    ADMIN_CHANNEL_ID = int(os.environ.get("ADMIN_CHANNEL_ID", "-1003607749028"))
    
    # Payment Configuration - Use environment variables
    UPI_ID = os.environ.get("UPI_ID", "helobiy41@ptyes")
    MIN_RECHARGE = int(os.environ.get("MIN_RECHARGE", "10"))
    MAX_RECHARGE = int(os.environ.get("MAX_RECHARGE", "10000"))
    FEE_PERCENT = int(os.environ.get("FEE_PERCENT", "20"))
    FEE_THRESHOLD = int(os.environ.get("FEE_THRESHOLD", "120"))
    
    # Railway specific paths
    RAILWAY_VOLUME = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "/data")
    IS_RAILWAY = os.environ.get("RAILWAY_SERVICE_NAME") is not None
    
    # File Paths - Use Railway volume if available
    if IS_RAILWAY and os.path.exists(RAILWAY_VOLUME):
        BASE_DIR = Path(RAILWAY_VOLUME)
    else:
        BASE_DIR = Path(".")
    
    QR_CODE_PATH = str(BASE_DIR / "qr.jpg")
    DATABASE_PATH = str(BASE_DIR / "bot_database.db")
    LOG_FILE = str(BASE_DIR / "bot.log")
    CONFIG_FILE = str(BASE_DIR / "config.json")
    BACKUP_DIR = str(BASE_DIR / "backups")
    
    # Timeouts and Limits
    SESSION_TIMEOUT = 600  # 10 minutes
    RATE_LIMIT = 30  # requests per minute
    CACHE_TIMEOUT = 300  # 5 minutes
    VERIFICATION_TIMEOUT = 600  # 10 minutes
    
    # UI Configuration
    BOT_NAME = "🎁 GIFT CARD BOT"
    BOT_VERSION = "4.1.0"
    COMPANY_NAME = "GiftCard Store"
    SUPPORT_EMAIL = "support@giftcard.com"
    WEBSITE = "www.giftcard.com"
    
    # Health check
    HEALTH_CHECK_INTERVAL = 60  # seconds

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
        "brand_color": "#FF9900"
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
        "brand_color": "#34A853"
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
        "brand_color": "#C51C3E"
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
        "brand_color": "#E12B38"
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
        "brand_color": "#2874F0"
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
        "brand_color": "#CB202D"
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

def setup_logging():
    """Setup comprehensive logging system for Railway"""
    
    # Create logs directory
    log_dir = Path("logs")
    try:
        log_dir.mkdir(exist_ok=True)
    except Exception:
        log_dir = Path("/tmp/logs")  # Fallback for Railway
        log_dir.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # File handler for all logs
    try:
        file_handler = logging.FileHandler(log_dir / "bot.log")
        file_handler.setLevel(logging.INFO)
        file_format = logging.Formatter('%(asctime)s | %(levelname)-8s | %(name)s | %(message)s')
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"⚠️ Could not create file handler: {e}")
    
    # Console handler for Railway logs
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = '%(asctime)s | %(levelname)-8s | %(message)s'
    console_handler.setFormatter(logging.Formatter(console_format))
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

# ===========================================================================
# DATABASE MANAGER - FIXED FOR RAILWAY
# ===========================================================================

class DatabaseManager:
    """
    Thread-safe database manager with connection pooling and Railway optimization
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
        
        # Create backup directory with error handling
        try:
            self.backup_dir.mkdir(exist_ok=True, parents=True)
        except Exception as e:
            logger.error(f"❌ Could not create backup dir: {e}")
            # Fallback to temp directory
            self.backup_dir = Path("/tmp/backups")
            self.backup_dir.mkdir(exist_ok=True, parents=True)
        
        # Initialize database with retry logic
        self._init_database_with_retry()
        
        logger.info("✅ Database Manager initialized")
    
    def _init_database_with_retry(self, max_retries=3):
        """Initialize database with retry logic for Railway"""
        for attempt in range(max_retries):
            try:
                self._init_database()
                return
            except Exception as e:
                logger.error(f"❌ Database init attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.critical("❌ Failed to initialize database after all retries")
                    raise
    
    def _init_database(self):
        """Initialize database tables with error handling"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            # Enable foreign keys and WAL mode
            c.execute("PRAGMA foreign_keys = ON")
            c.execute("PRAGMA journal_mode = WAL")
            c.execute("PRAGMA synchronous = NORMAL")
            
            # Create tables with error handling
            self._create_tables(c)
            
            conn.commit()
            conn.close()
            
            logger.info("✅ Database tables initialized")
            
        except Exception as e:
            logger.error(f"❌ Database initialization error: {e}")
            raise
    
    def _create_tables(self, c):
        """Create all database tables"""
        try:
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
                preferences TEXT DEFAULT '{}',
                notes TEXT
            )''')
            
            # Create indexes
            c.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)")
            
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
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )''')
            
            # Create indexes
            c.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)")
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
                status TEXT DEFAULT 'completed',
                timestamp TIMESTAMP,
                delivered_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )''')
            
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
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )''')
            
            # ===== SETTINGS TABLE =====
            c.execute('''CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                type TEXT DEFAULT 'string',
                description TEXT,
                updated_at TIMESTAMP
            )''')
            
            # Insert default settings
            default_settings = [
                ('bot_name', config.BOT_NAME, 'string', 'Bot display name'),
                ('min_recharge', str(config.MIN_RECHARGE), 'int', 'Minimum recharge amount'),
                ('max_recharge', str(config.MAX_RECHARGE), 'int', 'Maximum recharge amount'),
                ('fee_percent', str(config.FEE_PERCENT), 'int', 'Fee percentage'),
                ('fee_threshold', str(config.FEE_THRESHOLD), 'int', 'Fee threshold amount'),
                ('upi_id', config.UPI_ID, 'string', 'UPI ID for payments'),
                ('referral_bonus', '10', 'int', 'Referral bonus amount')
            ]
            
            for key, value, type_, desc in default_settings:
                c.execute(
                    "INSERT OR IGNORE INTO settings (key, value, type, description, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (key, value, type_, desc, datetime.now().isoformat())
                )
                
        except Exception as e:
            logger.error(f"❌ Table creation error: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get database connection with error handling"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def backup_database(self):
        """Create database backup with Railway compatibility"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"backup_{timestamp}.db"
            
            with self.get_connection() as conn:
                backup_conn = sqlite3.connect(backup_path)
                conn.backup(backup_conn)
                backup_conn.close()
            
            logger.info(f"✅ Database backup created: {backup_path}")
            
            # Keep only last 5 backups on Railway (limited storage)
            backups = sorted(self.backup_dir.glob("backup_*.db"))
            max_backups = 3 if config.IS_RAILWAY else 10
            if len(backups) > max_backups:
                for backup in backups[:-max_backups]:
                    backup.unlink()
            
            return str(backup_path)
        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            return None
    
    # ===== USER METHODS =====
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                row = c.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ Error getting user {user_id}: {e}")
            return None
    
    def create_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None) -> Optional[Dict]:
        """Create new user"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                
                # Generate unique referral code
                referral_code = hashlib.md5(f"{user_id}{datetime.now()}{random.random()}".encode()).hexdigest()[:8]
                
                now = datetime.now().isoformat()
                
                c.execute('''INSERT OR IGNORE INTO users 
                    (user_id, username, first_name, last_name, referral_code, join_date, last_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (user_id, username, first_name, last_name, referral_code, now, now))
                
                conn.commit()
                
                return self.get_user(user_id)
        except Exception as e:
            logger.error(f"❌ Error creating user {user_id}: {e}")
            return None
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        """Update user fields"""
        try:
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
        except Exception as e:
            logger.error(f"❌ Error updating user {user_id}: {e}")
            return False
    
    def update_balance(self, user_id: int, amount: int, transaction_type: str, **kwargs) -> bool:
        """Update user balance and record transaction"""
        try:
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
        except Exception as e:
            logger.error(f"❌ Error updating balance for user {user_id}: {e}")
            return False
    
    # ===== VERIFICATION METHODS =====
    
    def create_verification(self, user_id: int, amount: int, fee: int, final: int, utr: str, screenshot: str) -> Optional[str]:
        """Create payment verification"""
        try:
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
        except Exception as e:
            logger.error(f"❌ Error creating verification: {e}")
            return None
    
    def approve_verification(self, verification_id: str, admin_id: int) -> bool:
        """Approve payment verification"""
        try:
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
        except Exception as e:
            logger.error(f"❌ Error approving verification {verification_id}: {e}")
            return False

# ===========================================================================
# CACHE MANAGER
# ===========================================================================

class CacheManager:
    """Simple cache manager with TTL"""
    
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

# ===========================================================================
# RATE LIMITER
# ===========================================================================

class RateLimiter:
    """Simple rate limiter"""
    
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

# ===========================================================================
# SESSION MANAGER
# ===========================================================================

class SessionManager:
    """Simple session manager"""
    
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
    def relative_time(date_str: str) -> str:
        """Get relative time string"""
        try:
            dt = datetime.fromisoformat(date_str)
            now = datetime.now()
            diff = now - dt
            
            if diff.days > 365:
                years = diff.days // 365
                return f"{years}y ago"
            elif diff.days > 30:
                months = diff.days // 30
                return f"{months}mo ago"
            elif diff.days > 0:
                return f"{diff.days}d ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours}h ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes}m ago"
            else:
                return "now"
        except:
            return date_str
    
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
    def amount(amount: int) -> bool:
        """Validate recharge amount"""
        return config.MIN_RECHARGE <= amount <= config.MAX_RECHARGE

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
        action = func.__name__
        
        logger.info(f"👤 User {user.id} ({user.first_name}) performed: {action}")
        
        try:
            result = await func(update, context, *args, **kwargs)
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
            logger.error(traceback.format_exc())
            
            error_message = (
                "⚠️ *An error occurred*\n\n"
                "Please try again later.\n"
                "If the problem persists, contact support."
            )
            
            try:
                if update.message:
                    await update.message.reply_text(
                        error_message,
                        parse_mode=ParseMode.MARKDOWN
                    )
                elif update.callback_query:
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
        if db_user:
            logger.info(f"✅ New user registered: {user.id} - {user.first_name}")
    
    db.update_user(user.id, last_active=datetime.now().isoformat())
    
    # Check channel membership
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
            f"To ensure safe transactions, you must join our official channel.\n\n"
            f"👇 *Click below to join and verify*"
        )
        
        keyboard = [[
            InlineKeyboardButton("📢 JOIN OFFICIAL CHANNEL", url=f"https://t.me/{config.MAIN_CHANNEL.replace('@', '')}"),
            InlineKeyboardButton("✅ I HAVE JOINED", callback_data="verify")
        ]]
        
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Show main menu for verified users
    balance = db.get_user_balance(user.id) if db_user else 0
    
    main_menu_text = (
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
        [InlineKeyboardButton("🆘 HELP & SUPPORT", callback_data="support")]
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
    db.update_user(user.id, last_active=datetime.now().isoformat())
    
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
                f"⬇️ *Choose an option:*"
            )
            
            keyboard = [
                [InlineKeyboardButton("🎁 GIFT CARDS", callback_data="giftcard")],
                [InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")],
                [InlineKeyboardButton("💳 MY WALLET", callback_data="wallet")],
                [InlineKeyboardButton("🆘 HELP & SUPPORT", callback_data="support")]
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
                f"2️⃣ Join {config.MAIN_CHANNEL}\n"
                f"3️⃣ Click VERIFY AGAIN"
            )
            
            keyboard = [[
                InlineKeyboardButton("📢 JOIN CHANNEL", url=f"https://t.me/{config.MAIN_CHANNEL.replace('@', '')}"),
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
    if not is_member and data not in ["verify", "main_menu"]:
        keyboard = [[
            InlineKeyboardButton("📢 JOIN CHANNEL", url=f"https://t.me/{config.MAIN_CHANNEL.replace('@', '')}"),
            InlineKeyboardButton("✅ VERIFY", callback_data="verify")
        ]]
        
        await query.edit_message_text(
            f"⚠️ *ACCESS DENIED*\n\nYou must join {config.MAIN_CHANNEL} first.",
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
            [InlineKeyboardButton("🆘 HELP & SUPPORT", callback_data="support")]
        ]
        
        await query.edit_message_text(
            main_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== GIFT CARD MENU =====
    elif data == "giftcard":
        keyboard = []
        for card_id, card in GIFT_CARDS.items():
            keyboard.append([InlineKeyboardButton(
                f"{card['full_emoji']} {card['name']}", 
                callback_data=f"card_{card_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 BACK", callback_data="main_menu")])
        
        await query.edit_message_text(
            f"🎁 *GIFT CARDS CATALOG*\n\n"
            f"*Choose from 10+ brands:* ⬇️",
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
        
        await query.edit_message_text(
            f"{card['full_emoji']} *{card['name']} GIFT CARD*\n\n"
            f"📝 {card['description']}\n"
            f"📱 {card['delivery']}\n"
            f"⏳ {card['validity']}\n\n"
            f"*Available Denominations:*\n"
            f"*Select amount below:* ⬇️",
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
                f"Card: {card['name']} ₹{value}\n"
                f"Price: {Formatter.currency(price)}\n"
                f"Your Balance: {Formatter.currency(balance)}\n"
                f"Short by: {Formatter.currency(short)}\n\n"
                f"Please add money to your wallet.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        # Store purchase data
        context.user_data['purchase'] = {
            'card_id': card_id,
            'card_name': card['name'],
            'card_emoji': card['full_emoji'],
            'value': value,
            'price': price
        }
        
        await query.edit_message_text(
            f"✅ *BALANCE SUFFICIENT*\n\n"
            f"Card: {card['full_emoji']} {card['name']} ₹{value}\n"
            f"Price: {Formatter.currency(price)}\n\n"
            f"📧 *Please enter your EMAIL address:*\n"
            f"Example: `yourname@gmail.com`",
            parse_mode=ParseMode.MARKDOWN
        )
        
        return STATE_EMAIL
    
    # ===== TOP UP MENU =====
    elif data == "topup":
        keyboard = [
            [InlineKeyboardButton("📱 UPI PAYMENT", callback_data="upi")],
            [InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            f"💰 *ADD MONEY TO WALLET*\n\n"
            f"*Select payment method:* ⬇️",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== UPI SELECTED =====
    elif data == "upi":
        await query.edit_message_text(
            f"💳 *UPI RECHARGE*\n\n"
            f"*Please enter the amount to add:*\n\n"
            f"💰 Minimum: {Formatter.currency(config.MIN_RECHARGE)}\n"
            f"💰 Maximum: {Formatter.currency(config.MAX_RECHARGE)}\n\n"
            f"📌 Fee: {config.FEE_PERCENT}% for amounts below ₹{config.FEE_THRESHOLD}\n\n"
            f"*Enter amount (in numbers):*",
            parse_mode=ParseMode.MARKDOWN
        )
        
        return STATE_AMOUNT
    
    # ===== WALLET =====
    elif data == "wallet":
        balance = db.get_user_balance(user.id)
        
        # Get recent transactions
        transactions = db.get_transactions(user.id, 5) if hasattr(db, 'get_transactions') else []
        
        trans_text = ""
        for t in transactions[:3]:  # Show last 3
            amount = t['amount']
            type_ = t['type']
            time_str = Formatter.relative_time(t['timestamp'])
            
            if type_ == 'credit':
                trans_text += f"✅ +{Formatter.currency(amount)} ({time_str})\n"
            elif type_ == 'debit':
                trans_text += f"💳 -{Formatter.currency(amount)} ({time_str})\n"
        
        if not trans_text:
            trans_text = "📭 No recent transactions"
        
        await query.edit_message_text(
            f"💳 *YOUR WALLET*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 *Balance:* {Formatter.currency(balance)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"*Recent Activity:*\n{trans_text}\n",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ===== SUPPORT =====
    elif data == "support":
        await query.edit_message_text(
            f"🆘 *HELP & SUPPORT*\n\n"
            f"Please type your issue below.\n\n"
            f"Our team will respond within 24 hours.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        return STATE_SUPPORT

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
    if amount < config.FEE_THRESHOLD:
        fee = int(amount * config.FEE_PERCENT / 100)
        final = amount - fee
    else:
        fee = 0
        final = amount
    
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
    
    await update.message.reply_text(
        f"💳 *PAYMENT DETAILS*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*UPI ID:* `{config.UPI_ID}`\n"
        f"*Amount:* {Formatter.currency(amount)}\n"
        f"*Fee:* {Formatter.currency(fee) if fee > 0 else 'No fee'}\n"
        f"*You will receive:* {Formatter.currency(final)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📱 *HOW TO PAY:*\n"
        f"1️⃣ Open any UPI app\n"
        f"2️⃣ Pay to UPI ID: `{config.UPI_ID}`\n"
        f"3️⃣ Take a SCREENSHOT\n"
        f"4️⃣ Click 'I HAVE PAID'\n\n"
        f"⏳ *Auto-cancel in {config.VERIFICATION_TIMEOUT//60} minutes*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
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
        f"*Please send the following:*\n\n"
        f"1️⃣ *PAYMENT SCREENSHOT* (as photo)\n"
        f"2️⃣ *UTR NUMBER* (in text)\n\n"
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
        "Now please send your *UTR number*.\n\n"
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
            "Example: `SBIN1234567890`",
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
    
    if not verification_id:
        await update.message.reply_text(
            "❌ *Error creating verification*\n\nPlease try again.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    # Get user info
    db_user = db.get_user(user.id)
    
    # Create admin message
    caption = (
        f"🔔 *NEW PAYMENT VERIFICATION*\n\n"
        f"👤 *User:* {user.first_name}\n"
        f"🆔 *ID:* `{user.id}`\n"
        f"👤 *Username:* @{user.username or 'N/A'}\n"
        f"💰 *Amount:* {Formatter.currency(data['amount'])}\n"
        f"🎁 *Credit:* {Formatter.currency(data['final'])}\n"
        f"🔢 *UTR:* `{utr}`\n"
        f"🆔 *Verification ID:* `{verification_id}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    # Create approve/reject buttons
    keyboard = [[
        InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{verification_id}"),
        InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{verification_id}")
    ]]
    
    # Send to admin channel
    try:
        await context.bot.send_photo(
            chat_id=config.ADMIN_CHANNEL_ID,
            photo=screenshot,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"❌ Error sending to admin channel: {e}")
        # Send to admin directly as fallback
        await context.bot.send_message(
            chat_id=config.ADMIN_ID,
            text=f"❌ Failed to send to channel. Please check manually.\n{verification_id}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Clear session data
    context.user_data.clear()
    
    # Confirm to user
    keyboard = [[InlineKeyboardButton("🏠 MAIN MENU", callback_data="main_menu")]]
    
    await update.message.reply_text(
        f"✅ *VERIFICATION SUBMITTED!*\n\n"
        f"Your payment is being verified.\n"
        f"You will be notified once approved.\n\n"
        f"⏳ *Estimated time: 5-10 minutes*",
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
            "Please enter a valid email address.\n"
            "Example: `yourname@gmail.com`",
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
    if hasattr(db, 'create_purchase'):
        order_id = db.create_purchase(
            user.id,
            purchase['card_name'],
            purchase['value'],
            purchase['price'],
            email
        )
    else:
        order_id = f"GC{datetime.now().strftime('%y%m%d%H%M%S')}{random.randint(1000, 9999)}"
    
    # Update user email if not set
    db_user = db.get_user(user.id)
    if db_user and not db_user.get('email'):
        db.update_user(user.id, email=email)
    
    # Clear session
    context.user_data.clear()
    
    # Send confirmation
    keyboard = [[InlineKeyboardButton("🏠 MAIN MENU", callback_data="main_menu")]]
    
    await update.message.reply_text(
        f"✅ *PURCHASE SUCCESSFUL!*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*{purchase['card_emoji']} {purchase['card_name']} ₹{purchase['value']}*\n"
        f"*Price:* {Formatter.currency(purchase['price'])}\n"
        f"*Order ID:* `{order_id}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📧 *Gift card sent to:*\n"
        f"`{email}`\n\n"
        f"📌 Check your inbox (and spam folder).\n"
        f"Card arrives in 2-5 minutes.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
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
    if hasattr(db, 'create_support_ticket'):
        ticket_id = db.create_support_ticket(user.id, message)
    else:
        ticket_id = f"TKT{datetime.now().strftime('%y%m%d%H%M%S')}{random.randint(1000, 9999)}"
    
    # Notify admin
    try:
        db_user = db.get_user(user.id)
        
        admin_msg = (
            f"🆘 *NEW SUPPORT TICKET*\n\n"
            f"👤 *User:* {user.first_name}\n"
            f"🆔 *ID:* `{user.id}`\n"
            f"👤 *Username:* @{user.username or 'N/A'}\n"
            f"🎫 *Ticket ID:* `{ticket_id}`\n"
            f"💬 *Message:*\n{message}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
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
        f"*Ticket ID:* `{ticket_id}`\n\n"
        f"Our support team will contact you within 24 hours.",
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
            
            # Notify user (you would need to get user_id from verification)
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
        if hasattr(db, 'reject_verification'):
            success = db.reject_verification(verification_id, config.ADMIN_ID)
        else:
            success = False
        
        if success:
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n❌ *REJECTED BY ADMIN*",
                parse_mode=ParseMode.MARKDOWN
            )
            
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
@handle_errors
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to view statistics"""
    db = DatabaseManager()
    
    # Basic stats
    with db.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]
        
        c.execute("SELECT SUM(balance) FROM users")
        total_balance = c.fetchone()[0] or 0
    
    stats_text = (
        f"📊 *BOT STATISTICS*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 *Date:* {datetime.now().strftime('%d %b %Y')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"*👥 Users:*\n"
        f"• Total Users: {total_users:,}\n\n"
        f"*💰 Finances:*\n"
        f"• Total Balance: {Formatter.currency(total_balance)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    await update.message.reply_text(
        stats_text,
        parse_mode=ParseMode.MARKDOWN
    )

@admin_only
@handle_errors
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
        names = [
            "Raj", "Arjun", "Kavya", "Veer", "Aryan",
            "Neha", "Karan", "Riya", "Amit", "Priya"
        ]
        
        cards = ["AMAZON", "PLAY STORE", "BOOKMYSHOW", "MYNTRA", "FLIPKART", "ZOMATO"]
        amounts = [500, 1000, 2000, 5000]
        
        name = random.choice(names)
        card = random.choice(cards)
        amount = random.choice(amounts)
        
        message = (
            f"⚡ *NEW PURCHASE*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✨ *{name}* just bought\n"
            f"🎁 {card} *₹{amount}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📧 *Delivery:* Email (Instant)\n"
            f"🕐 *Time:* {datetime.now().strftime('%I:%M %p')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        
        await context.bot.send_message(
            chat_id=config.PROOF_CHANNEL,
            text=message,
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info("✅ Auto proof sent to channel")
        
    except Exception as e:
        logger.error(f"❌ Auto proof error: {e}")

# ===========================================================================
# HEALTH CHECK JOB
# ===========================================================================

async def health_check(context: ContextTypes.DEFAULT_TYPE):
    """Health check for Railway"""
    try:
        # Check database
        db = DatabaseManager()
        with db.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT 1")
            c.fetchone()
        
        logger.info("✅ Health check passed")
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")

# ===========================================================================
# CANCEL HANDLER
# ===========================================================================

@handle_errors
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
        BotCommand("broadcast", "📢 Broadcast message (admin)")
    ]
    
    await application.bot.set_my_commands(commands)
    
    # Initialize database
    db = DatabaseManager()
    
    # Log startup
    logger.info(f"✅ {config.BOT_NAME} v{config.BOT_VERSION} initialized successfully")
    if config.IS_RAILWAY:
        logger.info(f"🚀 Running on Railway with volume: {config.RAILWAY_VOLUME}")

# ===========================================================================
# GRACEFUL SHUTDOWN
# ===========================================================================

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    logger.info("🛑 Received shutdown signal, stopping bot...")
    sys.exit(0)

# ===========================================================================
# MAIN FUNCTION
# ===========================================================================

def main():
    """Main function"""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Validate bot token
    if config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.critical("❌ Please set your BOT_TOKEN in environment variables or Config class")
        sys.exit(1)
    
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
        app.add_handler(CommandHandler("broadcast", admin_broadcast))
        
        # ===== BUTTON HANDLERS =====
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
            # Auto proofs every 60 seconds
            app.job_queue.run_repeating(auto_proofs, interval=60, first=10)
            
            # Health check every 60 seconds
            app.job_queue.run_repeating(health_check, interval=config.HEALTH_CHECK_INTERVAL, first=30)
        
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
        if config.IS_RAILWAY:
            print(f"🚀 Platform: Railway")
            print(f"💾 Volume: {config.RAILWAY_VOLUME}")
        print("="*70)
        print(f"✅ Bot is running...")
        print("="*70 + "\n")
        
        # Start polling with Railway-optimized settings
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            close_loop=False
        )
        
    except Exception as e:
        logger.critical(f"❌ Fatal error: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
