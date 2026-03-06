import logging
import sqlite3
import asyncio
import random
import string
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram.constants import ParseMode

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8646034766:AAGXkMglnsc72ew1aGcFmWnZziwb8nfS2S8"
ADMIN_ID = 6185091342
MAIN_CHANNEL = "@GIFT_CARD_MAIN"
PROOF_CHANNEL = "@GIFT_CARD_LOGS_PROOF"
ADMIN_CHANNEL_ID = -1003607749028
UPI_ID = "helobiy41@ptyes"

# Gift Card Data
GIFT_CARDS = {
    "amazon": {"name": "🟦 AMAZON", "emoji": "🟦"},
    "playstore": {"name": "🟩 PLAY STORE", "emoji": "🟩"},
    "bookmyshow": {"name": "🎟️ BOOKMYSHOW", "emoji": "🎟️"},
    "myntra": {"name": "🛍️ MYNTRA", "emoji": "🛍️"},
    "flipkart": {"name": "📦 FLIPKART", "emoji": "📦"},
    "zomato": {"name": "🍕 ZOMATO", "emoji": "🍕"},
    "bigbasket": {"name": "🛒 BIG BASKET", "emoji": "🛒"}
}

PRICES = {
    500: 100,
    1000: 200,
    2000: 400
}

# States for conversation
AMOUNT, SCREENSHOT, EMAIL = range(3)

# ==================== DATABASE SETUP ====================
def init_db():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_name TEXT,
                  balance INTEGER DEFAULT 0,
                  joined_date TEXT,
                  last_active TEXT)''')
    
    # Transactions table
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  amount INTEGER,
                  type TEXT,
                  status TEXT,
                  utr TEXT,
                  timestamp TEXT)''')
    
    # Purchases table
    c.execute('''CREATE TABLE IF NOT EXISTS purchases
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  card_type TEXT,
                  card_value INTEGER,
                  price INTEGER,
                  email TEXT,
                  status TEXT,
                  timestamp TEXT)''')
    
    # Pending verifications table
    c.execute('''CREATE TABLE IF NOT EXISTS pending_verifications
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  amount INTEGER,
                  final_amount INTEGER,
                  utr TEXT,
                  timestamp TEXT)''')
    
    conn.commit()
    conn.close()

init_db()

# ==================== HELPER FUNCTIONS ====================
def get_user_balance(user_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def update_user_balance(user_id, amount):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, balance) VALUES (?, ?)",
              (user_id, amount))
    conn.commit()
    conn.close()

def add_transaction(user_id, amount, type_, status, utr=None):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('''INSERT INTO transactions 
                 (user_id, amount, type, status, utr, timestamp)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (user_id, amount, type_, status, utr, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def add_pending_verification(user_id, amount, final_amount, utr):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('''INSERT INTO pending_verifications
                 (user_id, amount, final_amount, utr, timestamp)
                 VALUES (?, ?, ?, ?, ?)''',
              (user_id, amount, final_amount, utr, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

# ==================== CHECK MEMBERSHIP ====================
async def check_membership(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=MAIN_CHANNEL, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# ==================== START COMMAND ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Check if user in main channel
    is_member = await check_membership(user.id, context)
    
    if not is_member:
        keyboard = [[InlineKeyboardButton("📢 JOIN CHANNEL", url=f"https://t.me/GIFT_CARD_MAIN")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"*👋 WELCOME {user.first_name}!*\n\n"
            f"⚠️ *To use this bot, you MUST join our main channel first:*\n"
            f"👉 @GIFT_CARD_MAIN\n\n"
            f"*After joining, click /start again.*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return
    
    # Save or update user
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO users 
                 (user_id, username, first_name, last_active)
                 VALUES (?, ?, ?, ?)''',
              (user.id, user.username, user.first_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    
    # Show main menu
    balance = get_user_balance(user.id)
    
    keyboard = [
        [InlineKeyboardButton("🎁 GIFT CARD", callback_data="giftcard")],
        [InlineKeyboardButton("💰 TOP UP", callback_data="topup")],
        [InlineKeyboardButton("💳 BALANCE", callback_data="balance")],
        [InlineKeyboardButton("🆘 SUPPORT", callback_data="support")],
        [InlineKeyboardButton("📊 PROOFS", callback_data="proofs")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"*🏠 MAIN MENU*\n\n"
        f"*Welcome Back, {user.first_name}!* 👋\n"
        f"*Your Balance:* ₹{balance}\n\n"
        f"*Please select an option:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

# ==================== CALLBACK HANDLER ====================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data
    
    # Check membership for all actions
    is_member = await check_membership(user.id, context)
    if not is_member:
        keyboard = [[InlineKeyboardButton("📢 JOIN CHANNEL", url=f"https://t.me/GIFT_CARD_MAIN")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"*⚠️ ACCESS DENIED*\n\n"
            f"*You must join our main channel first:*\n"
            f"👉 @GIFT_CARD_MAIN",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return
    
    # ========== GIFT CARD SECTION ==========
    if data == "giftcard":
        keyboard = []
        for card_id, card in GIFT_CARDS.items():
            keyboard.append([InlineKeyboardButton(f"{card['emoji']} {card['name']}", callback_data=f"card_{card_id}")])
        keyboard.append([InlineKeyboardButton("🔙 BACK", callback_data="main_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"*🎁 GIFT CARDS*\n\n"
            f"*Select your preferred brand:*\n\n"
            f"💳 *All cards delivered INSTANTLY on email*\n"
            f"⚡ *24/7 Automatic Delivery*\n"
            f"✅ *100% Working Codes*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    # Card selection
    elif data.startswith("card_"):
        card_id = data.replace("card_", "")
        card = GIFT_CARDS[card_id]
        
        keyboard = [
            [InlineKeyboardButton(f"₹500 FOR JUST ₹{PRICES[500]}", callback_data=f"buy_{card_id}_500")],
            [InlineKeyboardButton(f"₹1000 FOR JUST ₹{PRICES[1000]}", callback_data=f"buy_{card_id}_1000")],
            [InlineKeyboardButton(f"₹2000 FOR JUST ₹{PRICES[2000]}", callback_data=f"buy_{card_id}_2000")],
            [InlineKeyboardButton("🔙 BACK", callback_data="giftcard")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"*{card['emoji']} {card['name']} GIFT CARD*\n\n"
            f"📱 *Delivery:* On Email\n"
            f"⚡ *Time:* Instant after purchase\n"
            f"✅ *Status:* IN SALE\n\n"
            f"*Select denomination:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    # Buy card
    elif data.startswith("buy_"):
        parts = data.split("_")
        card_id = parts[1]
        value = int(parts[2])
        price = PRICES[value]
        card = GIFT_CARDS[card_id]
        
        balance = get_user_balance(user.id)
        
        if balance < price:
            keyboard = [
                [InlineKeyboardButton("💰 TOP UP NOW", callback_data="topup")],
                [InlineKeyboardButton("🏠 MAIN MENU", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"*❌ INSUFFICIENT BALANCE!*\n\n"
                f"*Your Balance:* ₹{balance}\n"
                f"*Required:* ₹{price}\n\n"
                f"*Please top up your wallet first.*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            return
        
        # Store purchase info in context
        context.user_data['purchase'] = {
            'card_id': card_id,
            'card_name': card['name'],
            'value': value,
            'price': price
        }
        
        await query.edit_message_text(
            f"*✅ BALANCE SUFFICIENT*\n\n"
            f"*{card['emoji']} {card['name']} ₹{value}*\n"
            f"*Price:* ₹{price}\n"
            f"*Your Balance:* ₹{balance}\n"
            f"*New Balance:* ₹{balance - price}\n\n"
            f"*Please enter your GMAIL ID to receive the card:*\n"
            f"*(Example: example@gmail.com)*",
            parse_mode=ParseMode.MARKDOWN
        )
        
        return EMAIL
    
    # ========== TOP UP SECTION ==========
    elif data == "topup":
        keyboard = [
            [InlineKeyboardButton("📱 UPI", callback_data="upi")],
            [InlineKeyboardButton("₿ CRYPTO", callback_data="crypto")],
            [InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"*💰 TOP UP YOUR WALLET*\n\n"
            f"*Select payment method:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    elif data == "upi":
        await query.edit_message_text(
            f"*💳 UPI RECHARGE*\n\n"
            f"*Please specify the amount you want to recharge:*\n\n"
            f"💰 *Minimum:* ₹10\n"
            f"💰 *Maximum:* ₹10,000\n\n"
            f"📌 *NOTE:* 20% fee will be deducted for payments below ₹120\n"
            f"       *(Example: Recharge ₹100 → You get ₹80 balance)*\n\n"
            f"*Enter amount (in numbers):*",
            parse_mode=ParseMode.MARKDOWN
        )
        
        return AMOUNT
    
    elif data == "crypto":
        await query.edit_message_text(
            f"*₿ CRYPTO PAYMENT*\n\n"
            f"*Coming Soon!* ⏳\n\n"
            f"*Please use UPI for now.*",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ========== BALANCE SECTION ==========
    elif data == "balance":
        balance = get_user_balance(user.id)
        
        # Get recent transactions
        conn = sqlite3.connect('bot_database.db')
        c = conn.cursor()
        c.execute('''SELECT amount, type, timestamp FROM transactions 
                     WHERE user_id = ? ORDER BY timestamp DESC LIMIT 5''', (user.id,))
        transactions = c.fetchall()
        conn.close()
        
        trans_text = ""
        for t in transactions:
            amount, type_, time = t
            if type_ == "credit":
                trans_text += f"• *+₹{amount}* on {time[:10]}\n"
            else:
                trans_text += f"• *-₹{amount}* on {time[:10]}\n"
        
        if not trans_text:
            trans_text = "• No transactions yet"
        
        keyboard = [
            [InlineKeyboardButton("💰 TOP UP NOW", callback_data="topup")],
            [InlineKeyboardButton("🏠 MAIN MENU", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"*💳 YOUR BALANCE*\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 *Available:* ₹{balance}\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"*📊 Recent Transactions:*\n"
            f"{trans_text}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    # ========== SUPPORT SECTION ==========
    elif data == "support":
        keyboard = [[InlineKeyboardButton("🏠 MAIN MENU", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"*🆘 CUSTOMER SUPPORT*\n\n"
            f"⚠️ *Sorry for the issue!*\n\n"
            f"*Our support team has been notified.*\n"
            f"*We will contact you within 24 hours.*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    # ========== PROOFS SECTION ==========
    elif data == "proofs":
        keyboard = [[InlineKeyboardButton("🏠 MAIN MENU", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"*📊 PROOF CHANNEL*\n\n"
            f"✅ *See real-time purchases:*\n\n"
            f"👉 {PROOF_CHANNEL}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⚡ *Latest Purchase:*\n"
            f"*[User] bought Amazon ₹1000 at {datetime.now().strftime('%I:%M %p')}*\n"
            f"━━━━━━━━━━━━━━━━━━",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    # ========== MAIN MENU ==========
    elif data == "main_menu":
        balance = get_user_balance(user.id)
        
        keyboard = [
            [InlineKeyboardButton("🎁 GIFT CARD", callback_data="giftcard")],
            [InlineKeyboardButton("💰 TOP UP", callback_data="topup")],
            [InlineKeyboardButton("💳 BALANCE", callback_data="balance")],
            [InlineKeyboardButton("🆘 SUPPORT", callback_data="support")],
            [InlineKeyboardButton("📊 PROOFS", callback_data="proofs")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"*🏠 MAIN MENU*\n\n"
            f"*Welcome Back, {user.first_name}!* 👋\n"
            f"*Your Balance:* ₹{balance}\n\n"
            f"*Please select an option:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

# ==================== AMOUNT HANDLER ====================
async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()
    
    try:
        amount = int(text)
        if amount < 10 or amount > 10000:
            await update.message.reply_text(
                f"*❌ INVALID AMOUNT*\n\n"
                f"*Amount must be between ₹10 and ₹10,000*\n\n"
                f"*Please try again:*",
                parse_mode=ParseMode.MARKDOWN
            )
            return AMOUNT
        
        # Calculate fee
        if amount < 120:
            fee = int(amount * 0.2)
            final_amount = amount - fee
        else:
            fee = 0
            final_amount = amount
        
        # Store in context
        context.user_data['topup'] = {
            'amount': amount,
            'final_amount': final_amount,
            'fee': fee
        }
        
        # Send QR code (you'll add QR photo later)
        keyboard = [
            [InlineKeyboardButton("✅ VERIFY", callback_data="verify_payment")],
            [InlineKeyboardButton("❌ CANCEL", callback_data="topup")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"*💳 PAYMENT DETAILS*\n\n"
            f"*Amount:* ₹{amount}\n"
            f"*Fee:* ₹{fee}\n"
            f"*You will receive:* ₹{final_amount}\n\n"
            f"*👇 Scan this QR code to pay:*\n\n"
            f"*UPI ID:* `{UPI_ID}`\n\n"
            f"*✅ AFTER PAYMENT:*\n"
            f"1️⃣ *Take a SCREENSHOT of the payment*\n"
            f"2️⃣ *Copy the UTR number*\n"
            f"3️⃣ *Click VERIFY below*\n\n"
            f"⏳ *Auto-cancel in 10 minutes*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text(
            f"*❌ INVALID INPUT*\n\n"
            f"*Please enter a valid number:*",
            parse_mode=ParseMode.MARKDOWN
        )
        return AMOUNT

# ==================== VERIFY PAYMENT ====================
async def verify_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    topup_data = context.user_data.get('topup', {})
    
    if not topup_data:
        await query.edit_message_text(
            f"*❌ SESSION EXPIRED*\n\n"
            f"*Please start over.*",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    await query.edit_message_text(
        f"*📤 SEND PAYMENT PROOF*\n\n"
        f"*Please send:*\n"
        f"1️⃣ *Your payment SCREENSHOT (as photo)*\n"
        f"2️⃣ *Your UTR NUMBER (in message)*\n\n"
        f"*Example UTR:* `SBIN1234567890`",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return SCREENSHOT

# ==================== SCREENSHOT HANDLER ====================
async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Check if photo
    if not update.message.photo:
        await update.message.reply_text(
            f"*❌ PLEASE SEND A PHOTO*\n\n"
            f"*Send the screenshot first, then UTR number.*",
            parse_mode=ParseMode.MARKDOWN
        )
        return SCREENSHOT
    
    # Store photo
    photo = update.message.photo[-1].file_id
    context.user_data['screenshot'] = photo
    
    await update.message.reply_text(
        f"*✅ SCREENSHOT RECEIVED*\n\n"
        f"*Now please send your UTR number:*",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return SCREENSHOT

# ==================== UTR HANDLER ====================
async def handle_utr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    utr = update.message.text.strip()
    
    # Check if we have screenshot
    if 'screenshot' not in context.user_data:
        await update.message.reply_text(
            f"*❌ PLEASE SEND SCREENSHOT FIRST*",
            parse_mode=ParseMode.MARKDOWN
        )
        return SCREENSHOT
    
    topup_data = context.user_data.get('topup', {})
    screenshot = context.user_data.get('screenshot')
    
    # Forward to admin channel
    caption = (
        f"*🔔 NEW PAYMENT VERIFICATION*\n\n"
        f"*User:* {user.first_name} (@{user.username})\n"
        f"*User ID:* `{user.id}`\n"
        f"*Amount:* ₹{topup_data['amount']}\n"
        f"*Fee:* ₹{topup_data['fee']}\n"
        f"*Final Amount:* ₹{topup_data['final_amount']}\n"
        f"*UTR:* `{utr}`\n"
        f"*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{user.id}_{topup_data['final_amount']}_{utr}"),
            InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{user.id}_{utr}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_photo(
        chat_id=ADMIN_CHANNEL_ID,
        photo=screenshot,
        caption=caption,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    # Save to pending
    add_pending_verification(user.id, topup_data['amount'], topup_data['final_amount'], utr)
    
    await update.message.reply_text(
        f"*✅ VERIFICATION SUBMITTED!*\n\n"
        f"*Your payment is being verified.*\n"
        f"*You will be notified once approved.*\n\n"
        f"⏳ *Estimated time: 5-10 minutes*",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Clear context
    context.user_data.clear()
    
    return ConversationHandler.END

# ==================== ADMIN APPROVAL ====================
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    parts = data.split("_")
    
    if parts[0] == "approve":
        user_id = int(parts[1])
        amount = int(parts[2])
        utr = parts[3]
        
        # Get current balance
        balance = get_user_balance(user_id)
        new_balance = balance + amount
        
        # Update balance
        update_user_balance(user_id, new_balance)
        
        # Add transaction
        add_transaction(user_id, amount, "credit", "completed", utr)
        
        # Update pending
        conn = sqlite3.connect('bot_database.db')
        c = conn.cursor()
        c.execute("UPDATE pending_verifications SET status='approved' WHERE utr=?", (utr,))
        conn.commit()
        conn.close()
        
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"*✅ PAYMENT APPROVED!*\n\n"
                    f"*Amount:* ₹{amount} added to your balance\n"
                    f"*New Balance:* ₹{new_balance}\n"
                    f"*UTR:* `{utr}`\n\n"
                    f"*Thank you for using our service!* 🙏"
                ),
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
        
        # Update admin message
        await query.edit_message_caption(
            caption=query.message.caption + "\n\n*✅ APPROVED BY ADMIN*",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif parts[0] == "reject":
        user_id = int(parts[1])
        utr = parts[2]
        
        # Update pending
        conn = sqlite3.connect('bot_database.db')
        c = conn.cursor()
        c.execute("UPDATE pending_verifications SET status='rejected' WHERE utr=?", (utr,))
        conn.commit()
        conn.close()
        
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"*❌ PAYMENT REJECTED*\n\n"
                    f"*UTR:* `{utr}`\n"
                    f"*Reason:* Payment not verified\n\n"
                    f"*Please try again or contact support.*"
                ),
                parseMode=ParseMode.MARKDOWN
            )
        except:
            pass
        
        # Update admin message
        await query.edit_message_caption(
            caption=query.message.caption + "\n\n*❌ REJECTED BY ADMIN*",
            parse_mode=ParseMode.MARKDOWN
        )

# ==================== EMAIL HANDLER ====================
async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    email = update.message.text.strip()
    
    # Simple email validation
    if "@" not in email or "." not in email:
        await update.message.reply_text(
            f"*❌ INVALID EMAIL*\n\n"
            f"*Please enter a valid Gmail address:*",
            parse_mode=ParseMode.MARKDOWN
        )
        return EMAIL
    
    purchase = context.user_data.get('purchase')
    if not purchase:
        await update.message.reply_text(
            f"*❌ SESSION EXPIRED*\n\n"
            f"*Please start over.*",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    # Get balance and process
    balance = get_user_balance(user.id)
    if balance < purchase['price']:
        await update.message.reply_text(
            f"*❌ INSUFFICIENT BALANCE*",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    # Deduct balance
    new_balance = balance - purchase['price']
    update_user_balance(user.id, new_balance)
    
    # Add transaction
    add_transaction(user.id, purchase['price'], "debit", "completed")
    
    # Save purchase
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('''INSERT INTO purchases
                 (user_id, card_type, card_value, price, email, status, timestamp)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (user.id, purchase['card_name'], purchase['value'], purchase['price'], 
               email, "completed", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    
    # Send to proof channel (randomly)
    if random.choice([True, False]):  # 50% chance to post
        try:
            await context.bot.send_message(
                chat_id=PROOF_CHANNEL,
                text=(
                    f"*⚡ NEW PURCHASE*\n\n"
                    f"*[User] bought* {purchase['card_name']} *₹{purchase['value']}*\n"
                    f"*at {datetime.now().strftime('%I:%M %p')}*"
                ),
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
    
    await update.message.reply_text(
        f"*✅ PURCHASE SUCCESSFUL!*\n\n"
        f"*🎁 Gift Card:* {purchase['card_name']} ₹{purchase['value']}\n"
        f"*💰 Price:* ₹{purchase['price']}\n"
        f"*📧 Sent to:* `{email}`\n\n"
        f"*Check your inbox (and spam folder)!*\n"
        f"*🆔 Order ID:* #GC{random.randint(100000, 999999)}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Clear context
    context.user_data.clear()
    
    return ConversationHandler.END

# ==================== BROADCAST SYSTEM (FEATURE #10) ====================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Admin only
    if user.id != ADMIN_ID:
        await update.message.reply_text(
            f"*❌ UNAUTHORIZED*\n\n"
            f"*This command is for admins only.*",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Check if message provided
    if not context.args:
        await update.message.reply_text(
            f"*📢 BROADCAST COMMAND*\n\n"
            f"*Usage:* `/broadcast Your message here`\n\n"
            f"*Example:* `/broadcast 🎉 New offer: 10% off on all cards!`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    message = " ".join(context.args)
    
    # Get all users
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    
    sent = 0
    failed = 0
    
    status_msg = await update.message.reply_text(
        f"*📢 BROADCAST STARTED*\n\n"
        f"*Sending to {len(users)} users...*",
        parse_mode=ParseMode.MARKDOWN
    )
    
    for user_id in users:
        try:
            await context.bot.send_message(
                chat_id=user_id[0],
                text=(
                    f"*📢 ADMIN BROADCAST*\n\n"
                    f"{message}\n\n"
                    f"*━ GIFT CARD BOT ━*"
                ),
                parse_mode=ParseMode.MARKDOWN
            )
            sent += 1
            await asyncio.sleep(0.05)  # Small delay to avoid flooding
        except:
            failed += 1
        
        # Update status every 10 users
        if (sent + failed) % 10 == 0:
            await status_msg.edit_text(
                f"*📢 BROADCASTING...*\n\n"
                f"*Sent:* {sent}\n"
                f"*Failed:* {failed}\n"
                f"*Total:* {len(users)}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    await status_msg.edit_text(
        f"*📢 BROADCAST COMPLETED*\n\n"
        f"*✅ Sent:* {sent}\n"
        f"*❌ Failed:* {failed}\n"
        f"*Total:* {len(users)}",
        parse_mode=ParseMode.MARKDOWN
    )

# ==================== AUTO PROOFS ====================
async def auto_proofs(context: ContextTypes.DEFAULT_TYPE):
    """Send random purchase proofs to proof channel every 30-60 seconds"""
    
    cards = ["🟦 Amazon", "🟩 Play Store", "🎟️ BookMyShow", "🛍️ Myntra", "📦 Flipkart", "🍕 Zomato", "🛒 Big Basket"]
    amounts = [500, 1000, 2000]
    
    card = random.choice(cards)
    amount = random.choice(amounts)
    
    message = (
        f"*⚡ NEW PURCHASE*\n\n"
        f"*[User] bought* {card} *₹{amount}*\n"
        f"*at {datetime.now().strftime('%I:%M %p')}*"
    )
    
    try:
        await context.bot.send_message(
            chat_id=PROOF_CHANNEL,
            text=message,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        print(f"Auto proof error: {e}")

# ==================== CANCEL ====================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"*❌ CANCELLED*\n\n"
        f"*Send /start to begin again.*",
        parse_mode=ParseMode.MARKDOWN
    )
    context.user_data.clear()
    return ConversationHandler.END

# ==================== MAIN FUNCTION ====================
def main():
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Conversation handler for UPI
    upi_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(verify_payment, pattern="^verify_payment$")],
        states={
            SCREENSHOT: [
                MessageHandler(filters.PHOTO, handle_screenshot),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_utr)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Conversation handler for amount
    amount_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_callback, pattern="^upi$")],
        states={
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Conversation handler for email
    email_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_callback, pattern="^buy_")],
        states={
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(upi_conv)
    app.add_handler(amount_handler)
    app.add_handler(email_conv)
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^(approve_|reject_)"))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Auto proofs job (every 30-60 seconds)
    job_queue = app.job_queue
    job_queue.run_repeating(auto_proofs, interval=random.randint(30, 60), first=10)
    
    # Start bot
    print("🤖 Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
