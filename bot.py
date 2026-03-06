import logging
import sqlite3
import asyncio
import random
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram.constants import ParseMode

# ==================== SETUP LOGGING ====================
logging.basicConfig(
    format='%(asime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8646034766:AAGXkMglnsc72ew1aGcFmWnZziwb8nfS2S8"
ADMIN_ID = 6185091342
MAIN_CHANNEL = "@gift_card_main"
PROOF_CHANNEL = "@gift_card_log"
ADMIN_CHANNEL_ID = -1003607749028
UPI_ID = "helobiy41@ptyes"

# QR Code file path
QR_CODE_PATH = "qr.jpg"

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

# States
AMOUNT, SCREENSHOT, EMAIL, SUPPORT_MSG = range(4)

# ==================== DATABASE SETUP ====================
def init_db():
    try:
        conn = sqlite3.connect('bot_database.db')
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (user_id INTEGER PRIMARY KEY,
                      username TEXT,
                      first_name TEXT,
                      balance INTEGER DEFAULT 0,
                      joined_date TEXT,
                      last_active TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS transactions
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      amount INTEGER,
                      type TEXT,
                      status TEXT,
                      utr TEXT,
                      timestamp TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS purchases
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      card_type TEXT,
                      card_value INTEGER,
                      price INTEGER,
                      email TEXT,
                      status TEXT,
                      timestamp TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS pending_verifications
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      amount INTEGER,
                      final_amount INTEGER,
                      utr TEXT,
                      timestamp TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS support_tickets
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      message TEXT,
                      status TEXT,
                      timestamp TEXT)''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database init error: {e}")

init_db()

# ==================== HELPER FUNCTIONS ====================
def get_user_balance(user_id):
    try:
        conn = sqlite3.connect('bot_database.db')
        c = conn.cursor()
        c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else 0
    except Exception as e:
        logger.error(f"❌ Balance fetch error: {e}")
        return 0

def update_user_balance(user_id, amount):
    try:
        conn = sqlite3.connect('bot_database.db')
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO users (user_id, balance, last_active) VALUES (?, ?, ?)",
                  (user_id, amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"❌ Balance update error: {e}")

def add_user(user_id, username, first_name):
    try:
        conn = sqlite3.connect('bot_database.db')
        c = conn.cursor()
        c.execute('''INSERT OR IGNORE INTO users 
                     (user_id, username, first_name, balance, joined_date, last_active)
                     VALUES (?, ?, ?, 0, ?, ?)''',
                  (user_id, username, first_name, 
                   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"❌ Add user error: {e}")

# ==================== CHECK MEMBERSHIP ====================
async def check_membership(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=MAIN_CHANNEL, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"❌ Membership check error: {e}")
        return False

# ==================== START COMMAND ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        
        # Add user to database
        add_user(user.id, user.username, user.first_name)
        
        # Check if user is in main channel
        is_member = await check_membership(user.id, context)
        
        if not is_member:
            welcome_text = (
                f"✨ *WELCOME TO GIFT CARD BOT* ✨\n\n"
                f"👋 *Hello {user.first_name}!*\n\n"
                f"🎁 *Get Gift Cards at 80% OFF!*\n\n"
                f"🔒 *VERIFICATION REQUIRED*\n"
                f"You must join our official channel first.\n\n"
                f"👇 *Click the button below to join*"
            )
            
            keyboard = [[
                InlineKeyboardButton("📢 JOIN CHANNEL", url=f"https://t.me/gift_card_main"),
                InlineKeyboardButton("✅ VERIFY", callback_data="verify")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                welcome_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            return
        
        # Show main menu
        balance = get_user_balance(user.id)
        
        keyboard = [
            [InlineKeyboardButton("🎁 GIFT CARDS", callback_data="giftcard")],
            [InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")],
            [InlineKeyboardButton("💳 MY BALANCE", callback_data="balance")],
            [InlineKeyboardButton("🆘 SUPPORT", callback_data="support")],
            [InlineKeyboardButton("📊 PROOFS", callback_data="proofs")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"*🏠 MAIN MENU*\n\n"
            f"👋 *Welcome Back, {user.first_name}!*\n"
            f"💰 *Balance:* ₹{balance}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"❌ Start error: {e}")
        await update.message.reply_text("⚠️ Error. Please try /start again")

# ==================== BUTTON CALLBACK HANDLER ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main handler for all button clicks"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data
    
    print(f"🔘 Button clicked: {data} by {user.first_name}")  # Debug
    
    # ===== VERIFY BUTTON =====
    if data == "verify":
        is_member = await check_membership(user.id, context)
        
        if is_member:
            balance = get_user_balance(user.id)
            keyboard = [
                [InlineKeyboardButton("🎁 GIFT CARDS", callback_data="giftcard")],
                [InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")],
                [InlineKeyboardButton("💳 MY BALANCE", callback_data="balance")],
                [InlineKeyboardButton("🆘 SUPPORT", callback_data="support")],
                [InlineKeyboardButton("📊 PROOFS", callback_data="proofs")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ *VERIFIED!*\n\n"
                f"👋 *Welcome {user.first_name}!*\n"
                f"💰 *Balance:* ₹{balance}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        else:
            keyboard = [[
                InlineKeyboardButton("📢 JOIN CHANNEL", url=f"https://t.me/gift_card_main"),
                InlineKeyboardButton("🔄 VERIFY AGAIN", callback_data="verify")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"❌ *Not a member!*\n\nJoin @gift_card_main first",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        return
    
    # Check membership for all other actions
    is_member = await check_membership(user.id, context)
    if not is_member:
        keyboard = [[
            InlineKeyboardButton("📢 JOIN CHANNEL", url=f"https://t.me/gift_card_main"),
            InlineKeyboardButton("✅ VERIFY", callback_data="verify")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚠️ *Access Denied*\n\nJoin @gift_card_main first",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return
    
    # ===== GIFT CARD MENU =====
    if data == "giftcard":
        keyboard = []
        for card_id, card in GIFT_CARDS.items():
            keyboard.append([InlineKeyboardButton(f"{card['emoji']} {card['name']}", callback_data=f"card_{card_id}")])
        keyboard.append([InlineKeyboardButton("🔙 BACK", callback_data="main_menu")])
        
        await query.edit_message_text(
            "*🎁 GIFT CARDS*\n\nSelect a brand:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== CARD SELECTED =====
    elif data.startswith("card_"):
        card_id = data.replace("card_", "")
        card = GIFT_CARDS[card_id]
        
        keyboard = [
            [InlineKeyboardButton(f"₹500 → ₹{PRICES[500]}", callback_data=f"buy_{card_id}_500")],
            [InlineKeyboardButton(f"₹1000 → ₹{PRICES[1000]}", callback_data=f"buy_{card_id}_1000")],
            [InlineKeyboardButton(f"₹2000 → ₹{PRICES[2000]}", callback_data=f"buy_{card_id}_2000")],
            [InlineKeyboardButton("🔙 BACK", callback_data="giftcard")]
        ]
        
        await query.edit_message_text(
            f"*{card['emoji']} {card['name']}*\n\nSelect amount:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== BUY CARD =====
    elif data.startswith("buy_"):
        parts = data.split("_")
        card_id = parts[1]
        value = int(parts[2])
        price = PRICES[value]
        card = GIFT_CARDS[card_id]
        
        balance = get_user_balance(user.id)
        
        if balance < price:
            keyboard = [[InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")]]
            await query.edit_message_text(
                f"❌ *Insufficient balance*\nNeed: ₹{price}\nYou have: ₹{balance}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        context.user_data['purchase'] = {
            'card': card['name'],
            'value': value,
            'price': price
        }
        
        await query.edit_message_text(
            f"*📧 Enter your email:*",
            parse_mode=ParseMode.MARKDOWN
        )
        return EMAIL
    
    # ===== TOP UP MENU =====
    elif data == "topup":
        keyboard = [
            [InlineKeyboardButton("📱 UPI", callback_data="upi")],
            [InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            "*💰 ADD MONEY*\n\nSelect method:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== UPI SELECTED =====
    elif data == "upi":
        await query.edit_message_text(
            f"*💰 Enter amount (₹10-10000):*\n\nNote: 20% fee below ₹120",
            parse_mode=ParseMode.MARKDOWN
        )
        return AMOUNT
    
    # ===== PAID BUTTON =====
    elif data == "paid":
        keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]]
        await query.edit_message_text(
            f"*📤 SEND PAYMENT PROOF*\n\n"
            f"1️⃣ Send SCREENSHOT\n"
            f"2️⃣ Send UTR number",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SCREENSHOT
    
    # ===== CANCEL TOPUP =====
    elif data == "cancel_topup":
        keyboard = [
            [InlineKeyboardButton("📱 UPI", callback_data="upi")],
            [InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            f"❌ *Cancelled*\n\nSelect method:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END
    
    # ===== BALANCE =====
    elif data == "balance":
        balance = get_user_balance(user.id)
        keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]]
        await query.edit_message_text(
            f"*💳 YOUR BALANCE*\n\n💰 ₹{balance}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== SUPPORT =====
    elif data == "support":
        keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]]
        await query.edit_message_text(
            "*🆘 SUPPORT*\n\nType your issue below:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SUPPORT_MSG
    
    # ===== PROOFS =====
    elif data == "proofs":
        keyboard = [
            [InlineKeyboardButton("📢 VIEW CHANNEL", url=f"https://t.me/gift_card_log")],
            [InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            f"*📊 PROOFS*\n\nJoin @gift_card_log",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ===== MAIN MENU =====
    elif data == "main_menu":
        balance = get_user_balance(user.id)
        keyboard = [
            [InlineKeyboardButton("🎁 GIFT CARDS", callback_data="giftcard")],
            [InlineKeyboardButton("💰 ADD MONEY", callback_data="topup")],
            [InlineKeyboardButton("💳 MY BALANCE", callback_data="balance")],
            [InlineKeyboardButton("🆘 SUPPORT", callback_data="support")],
            [InlineKeyboardButton("📊 PROOFS", callback_data="proofs")]
        ]
        await query.edit_message_text(
            f"*🏠 MAIN MENU*\n\n👋 {user.first_name}\n💰 ₹{balance}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ==================== AMOUNT HANDLER ====================
async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = int(update.message.text.strip())
        
        if amount < 10 or amount > 10000:
            await update.message.reply_text("❌ Amount must be ₹10-10000")
            return AMOUNT
        
        if amount < 120:
            final = amount - int(amount * 0.2)
            fee_text = f"Fee: ₹{int(amount*0.2)}"
        else:
            final = amount
            fee_text = "No fee"
        
        context.user_data['topup'] = {'amount': amount, 'final': final}
        
        keyboard = [
            [InlineKeyboardButton("✅ PAID", callback_data="paid")],
            [InlineKeyboardButton("❌ CANCEL", callback_data="cancel_topup")]
        ]
        
        # Try to send QR code
        if os.path.exists(QR_CODE_PATH):
            with open(QR_CODE_PATH, 'rb') as qr:
                await update.message.reply_photo(
                    photo=qr,
                    caption=(
                        f"*💳 PAY TO:* `{UPI_ID}`\n"
                        f"Amount: ₹{amount}\n"
                        f"{fee_text}\n"
                        f"You get: ₹{final}\n\n"
                        f"After payment, click PAID"
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        else:
            await update.message.reply_text(
                f"*💳 PAY TO:* `{UPI_ID}`\n"
                f"Amount: ₹{amount}\n"
                f"{fee_text}\n"
                f"You get: ₹{final}\n\n"
                f"After payment, click PAID",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        return ConversationHandler.END
    except:
        await update.message.reply_text("❌ Enter a valid number")
        return AMOUNT

# ==================== SCREENSHOT HANDLER ====================
async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ Send a photo first")
        return SCREENSHOT
    
    context.user_data['screenshot'] = update.message.photo[-1].file_id
    await update.message.reply_text("✅ Now send UTR number:")
    return SCREENSHOT

# ==================== UTR HANDLER ====================
async def handle_utr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    utr = update.message.text.strip()
    
    if 'screenshot' not in context.user_data:
        await update.message.reply_text("❌ Send screenshot first")
        return SCREENSHOT
    
    data = context.user_data.get('topup', {})
    
    # Forward to admin
    keyboard = [[
        InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user.id}_{data.get('final',0)}_{utr}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user.id}_{utr}")
    ]]
    
    await context.bot.send_photo(
        chat_id=ADMIN_CHANNEL_ID,
        photo=context.user_data['screenshot'],
        caption=f"User: {user.first_name}\nAmount: ₹{data.get('amount',0)}\nUTR: {utr}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    await update.message.reply_text("✅ Verification submitted!")
    context.user_data.clear()
    return ConversationHandler.END

# ==================== EMAIL HANDLER ====================
async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()
    
    if "@" not in email:
        await update.message.reply_text("❌ Invalid email")
        return EMAIL
    
    purchase = context.user_data.get('purchase')
    if not purchase:
        await update.message.reply_text("❌ Session expired")
        return ConversationHandler.END
    
    user = update.effective_user
    balance = get_user_balance(user.id)
    
    if balance < purchase['price']:
        await update.message.reply_text("❌ Insufficient balance")
        return ConversationHandler.END
    
    # Process purchase
    new_balance = balance - purchase['price']
    update_user_balance(user.id, new_balance)
    
    await update.message.reply_text(
        f"*✅ SUCCESS!*\n\n"
        f"*{purchase['card']} ₹{purchase['value']}*\n"
        f"*Sent to:* {email}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    context.user_data.clear()
    return ConversationHandler.END

# ==================== SUPPORT MESSAGE HANDLER ====================
async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message.text.strip()
    
    # Notify admin
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🆘 Support from {user.first_name}:\n{message}"
        )
    except:
        pass
    
    await update.message.reply_text(
        "✅ *Message sent!*\n\nSupport will contact you soon.",
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END

# ==================== ADMIN CALLBACK ====================
async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    parts = data.split("_")
    
    if parts[0] == "approve":
        user_id = int(parts[1])
        amount = int(parts[2])
        
        balance = get_user_balance(user_id)
        update_user_balance(user_id, balance + amount)
        
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ Payment approved! ₹{amount} added"
        )
        await query.edit_message_caption("✅ Approved")
    
    elif parts[0] == "reject":
        user_id = int(parts[1])
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Payment rejected"
        )
        await query.edit_message_caption("❌ Rejected")

# ==================== AUTO PROOFS ====================
async def auto_proofs(context: ContextTypes.DEFAULT_TYPE):
    try:
        names = ["👑 Raj", "💫 Arjun", "🌟 Kavya", "⚡ Veer", "🔥 Aryan"]
        cards = ["🟦 AMAZON", "🟩 PLAY STORE", "📦 FLIPKART", "🍕 ZOMATO"]
        amounts = [500, 1000, 2000]
        
        msg = f"⚡ *{random.choice(names)}* bought {random.choice(cards)} ₹{random.choice(amounts)}"
        
        await context.bot.send_message(
            chat_id=PROOF_CHANNEL,
            text=msg,
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        pass

# ==================== CANCEL ====================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled")
    context.user_data.clear()
    return ConversationHandler.END

# ==================== MAIN ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    
    # Callback handler for ALL buttons
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Admin callback handler
    app.add_handler(CallbackQueryHandler(admin_handler, pattern="^(approve_|reject_)"))
    
    # Conversation handlers
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^upi$")],
        states={AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    ))
    
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^paid$")],
        states={
            SCREENSHOT: [
                MessageHandler(filters.PHOTO, handle_screenshot),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_utr)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    ))
    
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^buy_")],
        states={EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    ))
    
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^support$")],
        states={SUPPORT_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_support)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    ))
    
    # Auto proofs
    if app.job_queue:
        app.job_queue.run_repeating(auto_proofs, interval=45, first=10)
    
    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
