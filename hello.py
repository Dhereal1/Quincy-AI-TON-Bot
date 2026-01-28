import os
import logging
import json
import requests
import threading
import time
import re
import telebot
from groq import Groq
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- 1. SETUP & CONFIG ---
logging.basicConfig(level=logging.INFO)
load_dotenv()

TOKEN = os.getenv('TELEGRAM_TOKEN')
GROQ_KEY = os.getenv('GROQ_KEY')
TONCENTER_KEY = os.getenv('TONCENTER_API_KEY')  # Get free key from https://toncenter.com

bot = telebot.TeleBot(TOKEN)
client = Groq(api_key=GROQ_KEY)

# Globals for Alerts & Caching
alerts = {}  # {chat_id: {'target_price': float, 'initial_price': float, 'direction': 'above'/'below'}}
last_price = 0.0
last_update_time = 0
ALERTS_FILE = "quincy_alerts.json"  # Persistence file for alerts

# USDT Jetton Master Contract on TON
# Using the user-friendly address format (EQ...)
# TON Center API v3 accepts both user-friendly and raw formats
# This is the official USDT contract address on TON blockchain
# Verify at: https://tonscan.org/jetton/EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRv7Nw2Id_sDs
USDT_MASTER_ADDRESS = "EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRv7Nw2Id_sDs"

# TON Address Validation Regex
# Matches standard user-friendly TON addresses (48 chars, base64url-safe)
TON_ADDRESS_REGEX = re.compile(r'^[EUK0][Qq][A-Za-z0-9_-]{46}$')

# --- ALERT PERSISTENCE FUNCTIONS ---
def load_alerts():
    """Load alerts from JSON file on startup"""
    global alerts
    try:
        if os.path.exists(ALERTS_FILE):
            with open(ALERTS_FILE, 'r') as f:
                # Convert string keys back to integers
                loaded = json.load(f)
                alerts = {int(k): v for k, v in loaded.items()}
                logging.info(f"Loaded {len(alerts)} alerts from disk")
    except Exception as e:
        logging.error(f"Error loading alerts: {e}")
        alerts = {}

def save_alerts():
    """Save alerts to JSON file for persistence"""
    try:
        with open(ALERTS_FILE, 'w') as f:
            json.dump(alerts, f, indent=2)
        logging.debug("Alerts saved to disk")
    except Exception as e:
        logging.error(f"Error saving alerts: {e}")

def safe_send_message(chat_id, text, **kwargs):
    """
    Safely send message with Telegram's 4096 character limit
    Truncates if necessary and adds warning
    """
    MAX_LENGTH = 4000  # Leave room for truncation message
    try:
        if len(text) > MAX_LENGTH:
            text = text[:MAX_LENGTH] + "\n\n... _(Message truncated due to length)_"
        bot.send_message(chat_id, text, **kwargs)
        return True
    except Exception as e:
        logging.error(f"Error sending message to {chat_id}: {e}")
        return False

# --- 2. UTILS ---
def get_ton_price():
    """Fetch TON price with 2-minute cache"""
    global last_price, last_update_time
    current_time = time.time()
    if last_price and (current_time - last_update_time < 120):
        return last_price
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd"
        resp = requests.get(url, timeout=10).json()
        if 'the-open-network' in resp:
            last_price = resp['the-open-network']['usd']
            last_update_time = current_time
            return last_price
    except Exception as e:
        logging.error(f"Error fetching TON price: {e}")
    return last_price if last_price else 0.0

def get_ton_balance(address):
    """
    Fetch TON balance using TON Center API
    Returns balance in TON (float) or None on error
    """
    try:
        # Using TON Center API v2
        url = f"https://toncenter.com/api/v2/getAddressBalance"
        params = {"address": address}
        
        headers = {}
        if TONCENTER_KEY:
            headers["X-API-Key"] = TONCENTER_KEY
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("ok") and "result" in data:
            # Balance is returned in nanotons (1 TON = 1,000,000,000 nanotons)
            balance_nanoton = int(data["result"])
            balance_ton = balance_nanoton / 1_000_000_000
            return round(balance_ton, 4)
        else:
            logging.error(f"API returned not ok: {data}")
            return None
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error fetching TON balance: {e}")
        return None
    except Exception as e:
        logging.error(f"Error fetching TON balance: {e}")
        return None

def get_usdt_balance(address):
    """
    Fetch USDT balance using TON Center API v3
    USDT is a Jetton (token) on TON blockchain
    Returns balance in USDT (float) or 0.0 on error
    """
    try:
        # Using TON Center API v3 to get jetton wallets
        url = "https://toncenter.com/api/v3/jetton/wallets"
        params = {
            "owner_address": address,
            "jetton_address": USDT_MASTER_ADDRESS,
            "limit": 1
        }
        
        headers = {}
        if TONCENTER_KEY:
            headers["X-API-Key"] = TONCENTER_KEY
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Check if we have jetton wallets
        if "jetton_wallets" in data and len(data["jetton_wallets"]) > 0:
            jetton_wallet = data["jetton_wallets"][0]
            balance = jetton_wallet.get("balance", "0")
            
            # USDT has 6 decimals (1 USDT = 1,000,000 units)
            balance_usdt = int(balance) / 1_000_000
            return round(balance_usdt, 2)
        else:
            # No USDT wallet found for this address
            return 0.0
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error fetching USDT balance: {e}")
        return 0.0
    except Exception as e:
        logging.error(f"Error fetching USDT balance: {e}")
        return 0.0

def get_last_transactions(address, limit=5):
    """
    Fetch last N transactions for an address
    Returns formatted string or error message
    """
    try:
        url = f"https://toncenter.com/api/v2/getTransactions"
        params = {
            "address": address,
            "limit": limit
        }
        
        headers = {}
        if TONCENTER_KEY:
            headers["X-API-Key"] = TONCENTER_KEY
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get("ok") or not data.get("result"):
            return "No recent transactions found."
        
        transactions = data["result"]
        
        if not transactions:
            return "No recent transactions found."
        
        # Format transactions
        tx_list = []
        for i, tx in enumerate(transactions[:limit], 1):
            try:
                # Extract transaction details
                tx_hash = tx.get("transaction_id", {}).get("hash", "N/A")[:8]
                
                # Get in/out messages
                in_msg = tx.get("in_msg", {})
                value = in_msg.get("value", "0")
                
                # Convert from nanotons to TON
                value_ton = int(value) / 1_000_000_000 if value != "0" else 0
                
                # Get timestamp
                utime = tx.get("utime", 0)
                time_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(utime)) if utime else "Unknown"
                
                # Determine if incoming or outgoing
                source = in_msg.get("source", "")
                destination = in_msg.get("destination", "")
                
                direction = "📥 IN" if destination == address else "📤 OUT"
                
                if value_ton > 0:
                    tx_list.append(f"{i}. {direction} `{value_ton:.4f} TON` - {time_str}")
                else:
                    tx_list.append(f"{i}. {direction} Smart Contract Call - {time_str}")
                
            except Exception as e:
                logging.error(f"Error parsing transaction: {e}")
                continue
        
        return "\n".join(tx_list) if tx_list else "No recent transactions found."
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error fetching transactions: {e}")
        return "❌ Error fetching transactions."
    except Exception as e:
        logging.error(f"Error fetching transactions: {e}")
        return "❌ Error fetching transactions."

def check_crypto_safety(text):
    """
    Check text for dangerous crypto-related phrases
    Returns dict with warning info
    """
    text_lower = text.lower()
    
    # Highly dangerous phrases (block rewrite)
    dangerous_phrases = [
        "seed phrase", "mnemonic", "private key", "recovery phrase",
        "12 word", "24 word", "secret phrase", "wallet backup",
        "send me your", "share your key", "give me access",
        "verify your wallet by sending", "unlock wallet by transferring"
    ]
    
    # Warning phrases (allow rewrite but warn)
    warning_phrases = [
        "buy now", "act fast", "limited time", "urgent",
        "send ton to", "transfer to this address", "guaranteed profit",
        "double your", "risk free", "can't lose"
    ]
    
    # Check for dangerous content
    for phrase in dangerous_phrases:
        if phrase in text_lower:
            return {
                "is_dangerous": True,
                "has_warning": True,
                "warning": "This message requests sensitive wallet information. Never share seed phrases or private keys with anyone."
            }
    
    # Check for warning content
    for phrase in warning_phrases:
        if phrase in text_lower:
            return {
                "is_dangerous": False,
                "has_warning": True,
                "warning": "Be cautious of urgency-based or investment promises in crypto communications."
            }
    
    # All clear
    return {
        "is_dangerous": False,
        "has_warning": False,
        "warning": None
    }

def generate_change_summary(original, rewritten, style):
    """
    Generate a brief summary of what was changed
    """
    original_lower = original.lower()
    rewritten_lower = rewritten.lower()
    
    changes = []
    
    # Detect specific changes based on style
    if style == "fix_grammar":
        if original != rewritten:
            changes.append("Fixed grammar and spelling")
    
    elif style == "make_pro":
        if "!!!" in original or original.isupper():
            changes.append("Removed excessive punctuation and caps")
        if len(rewritten.split('.')) > len(original.split('.')):
            changes.append("Improved sentence structure")
        changes.append("Enhanced professional tone")
    
    elif style == "make_announcement":
        changes.append("Formatted as public announcement")
        if "buy now" in original_lower or "act fast" in original_lower:
            changes.append("Removed pressure tactics")
    
    elif style == "simplify":
        original_words = original.split()
        rewritten_words = rewritten.split()
        if len(rewritten_words) < len(original_words):
            changes.append("Shortened for clarity")
        changes.append("Simplified language")
    
    if not changes:
        return None
    
    return "Changes: " + ", ".join(changes)


# --- 3. BACKGROUND WATCHER ---
def price_watcher():
    """
    Background thread to monitor price alerts for all users
    Supports multiple simultaneous alerts with direction tracking
    """
    global alerts
    while True:
        try:
            if alerts:  # Only check if there are active alerts
                current_price = get_ton_price()
                
                if not current_price or current_price == 0:
                    # Skip this cycle if price fetch failed
                    time.sleep(60)
                    continue
                
                # Check each user's alert
                triggered_alerts = []
                
                for chat_id, alert_data in alerts.items():
                    target = alert_data['target_price']
                    initial = alert_data['initial_price']
                    direction = alert_data['direction']
                    
                    # Check if alert should trigger based on direction
                    should_trigger = False
                    
                    if direction == 'above':
                        # Alert triggers when price crosses above target
                        # Only if we started below the target
                        if initial < target and current_price >= target:
                            should_trigger = True
                    elif direction == 'below':
                        # Alert triggers when price crosses below target
                        # Only if we started above the target
                        if initial > target and current_price <= target:
                            should_trigger = True
                    
                    if should_trigger:
                        try:
                            emoji = "🚀" if direction == 'above' else "📉"
                            message = (
                                f"{emoji} **PRICE ALERT!**\n\n"
                                f"TON has crossed **${target}**\n"
                                f"Current price: **${current_price}**\n\n"
                                f"Alert set at: ${initial}"
                            )
                            bot.send_message(chat_id, message, parse_mode='Markdown')
                            triggered_alerts.append(chat_id)
                        except Exception as e:
                            logging.error(f"Error sending alert to {chat_id}: {e}")
                            triggered_alerts.append(chat_id)  # Remove failed alerts
                
                # Remove triggered alerts
                for chat_id in triggered_alerts:
                    del alerts[chat_id]
                
                # CRITICAL: Save to disk after removing triggered alerts
                if triggered_alerts:
                    save_alerts()
        
        except Exception as e:
            logging.error(f"Error in price_watcher: {e}")
        
        time.sleep(60)  # Check every minute

threading.Thread(target=price_watcher, daemon=True).start()

# --- 4. COMMAND HANDLERS ---

@bot.message_handler(commands=['start', 'dashboard'])
def show_dashboard(message):
    """Display the communication-focused dashboard"""
    price = get_ton_price()
    
    # Handle failed price fetch
    if not price or price == 0:
        price_display = "Unavailable"
        price_text = "Unavailable"
    else:
        price_display = f"${price}"
        price_text = f"${price}"
    
    # NEW: Communication-first button layout
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    
    # ROW 1: Primary communication features
    btn_rewrite = InlineKeyboardButton("✍️ Improve Message", callback_data="how_to_rewrite")
    btn_announcement = InlineKeyboardButton("📢 Draft Announcement", callback_data="draft_announcement")
    markup.add(btn_rewrite, btn_announcement)
    
    # ROW 2: Safety and help
    btn_safety = InlineKeyboardButton("🛡️ Safety Tips", callback_data="safety_tips")
    markup.add(btn_safety)
    
    # ROW 3: TON Data tools (demoted but accessible)
    btn_wallet = InlineKeyboardButton("💎 Check Wallet", callback_data="check_wallet")
    btn_price = InlineKeyboardButton("📈 TON Price", callback_data="check_price")
    markup.add(btn_wallet, btn_price)
    
    # ROW 4: Alert
    btn_alert = InlineKeyboardButton("🔔 Price Alert", callback_data="set_alert_info")
    markup.add(btn_alert)
    
    # NEW: Communication-focused dashboard text
    dashboard_text = (
        f"✍️ **Quincy Communication Hub**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"I help you write clear, professional, and safe TON messages.\n\n"
        f"📌 **Main Tools:**\n"
        f"• Improve any message with AI\n"
        f"• Draft professional announcements\n"
        f"• Check for scam language\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💎 **TON Data:** Price: {price_text} | ⏰ {time.strftime('%H:%M')}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Choose an option below:"
    )
    bot.send_message(message.chat.id, dashboard_text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['alert'])
def set_alert(message):
    """Set a price alert for TON with direction detection"""
    global alerts
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Use: `/alert 2.50`", parse_mode='Markdown')
            return
        
        target_price = float(parts[1])
        if target_price <= 0:
            bot.reply_to(message, "❌ Price must be positive!")
            return
        
        # Get current price to determine direction
        current_price = get_ton_price()
        
        if not current_price or current_price == 0:
            bot.reply_to(message, 
                "❌ Unable to fetch current price. Please try again in a moment.",
                parse_mode='Markdown'
            )
            return
        
        # Determine alert direction
        if target_price > current_price:
            direction = 'above'
            direction_text = "rises to"
        else:
            direction = 'below'
            direction_text = "drops to"
        
        # Store alert for this user
        alerts[message.chat.id] = {
            'target_price': target_price,
            'initial_price': current_price,
            'direction': direction
        }
        
        # CRITICAL: Save to disk for persistence
        save_alerts()
        
        bot.reply_to(
            message, 
            f"✅ **Alert Set!**\n\n"
            f"You'll be notified when TON {direction_text} **${target_price}**\n\n"
            f"Current price: ${current_price}\n"
            f"Direction: {'📈 Above' if direction == 'above' else '📉 Below'}",
            parse_mode='Markdown'
        )
        
    except ValueError:
        bot.reply_to(message, "❌ Invalid price format. Use: `/alert 2.50`", parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Error setting alert: {e}")
        bot.reply_to(message, "❌ Error setting alert. Please try again.")

@bot.message_handler(commands=['price'])
def check_price(message):
    """Quick price check command"""
    price = get_ton_price()
    bot.reply_to(message, f"💰 **TON Price:** `${price} USD`", parse_mode='Markdown')

@bot.message_handler(commands=['help'])
def show_help(message):
    """Display help information"""
    help_text = (
        "✍️ **Quincy - TON Communication Assistant**\n"
        "━━━━━━━━━━━━━━━\n"
        "I help you write clear, professional, and safe messages.\n\n"
        
        "📌 **Main Features:**\n"
        "`/rewrite` - Improve any message\n"
        "   → Reply to a message, then type /rewrite\n"
        "   → Choose: Grammar, Professional, Announcement, or Simplify\n"
        "   → Get improved version in seconds\n\n"
        
        "🛡️ **Safety:** I detect and block scam language automatically\n\n"
        
        "━━━━━━━━━━━━━━━\n"
        "💎 **TON Tools:**\n"
        "`/start` or `/dashboard` - Open communication hub\n"
        "`/price` - Check TON price\n"
        "`/alert [price]` - Set price notification\n"
        "Paste TON address - Get wallet report\n"
        
        "━━━━━━━━━━━━━━━\n"
        "💡 **Tips:**\n"
        "• Use /rewrite on announcements before posting\n"
        "• I'll warn you if text looks unsafe\n"
        "• Reply 'hi' anytime to see what I do"
    )
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['rewrite'])
def start_rewrite(message):
    """
    Interactive rewrite command with multiple style options
    Usage: Reply to any message with /rewrite
    """
    if message.reply_to_message:
        # Check if the replied message has text
        if not message.reply_to_message.text:
            bot.reply_to(message, "❌ The message you replied to doesn't contain any text to rewrite!")
            return
        
        # Create interactive button menu
        markup = InlineKeyboardMarkup()
        markup.row_width = 1
        markup.add(
            InlineKeyboardButton("✨ Fix Grammar", callback_data="rewrite:fix_grammar"),
            InlineKeyboardButton("🧑‍💼 Make Professional", callback_data="rewrite:make_pro"),
            InlineKeyboardButton("📢 Announcement Style", callback_data="rewrite:make_announcement"),
            InlineKeyboardButton("🧠 Simplify", callback_data="rewrite:simplify")
        )
        bot.reply_to(message.reply_to_message, "✍️ **Choose a rewrite style:**", reply_markup=markup, parse_mode='Markdown')
    else:
        bot.reply_to(
            message, 
            "❌ Please **reply** to a message with `/rewrite` to improve it!\n\n"
            "📝 How to use:\n"
            "1. Find a message you want to improve\n"
            "2. Reply to it\n"
            "3. Type `/rewrite`\n"
            "4. Choose your preferred style",
            parse_mode='Markdown'
        )

# --- 5. BUTTON CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    """Handle inline button clicks"""
    
    # --- NEW COMMUNICATION CALLBACKS ---
    if call.data == "how_to_rewrite":
        bot.answer_callback_query(call.id)
        help_msg = (
            "✍️ **How to Improve Messages**\n\n"
            "1️⃣ Find any message you want to improve\n"
            "2️⃣ Reply to it with `/rewrite`\n"
            "3️⃣ Choose a style:\n"
            "   • ✨ Fix Grammar\n"
            "   • 🧑‍💼 Make Professional\n"
            "   • 📢 Announcement Style\n"
            "   • 🧠 Simplify\n\n"
            "4️⃣ Get your improved version instantly!\n\n"
            "💡 **Tip:** I'll automatically check for scam language and warn you if anything looks unsafe."
        )
        bot.send_message(call.message.chat.id, help_msg, parse_mode='Markdown')
    
    elif call.data == "draft_announcement":
        bot.answer_callback_query(call.id)
        template_msg = (
            "📢 **Announcement Templates**\n\n"
            "**Token Launch:**\n"
            "_We're excited to announce [TOKEN] launching on [DATE] at [TIME] UTC. "
            "Full details and participation instructions will be shared [TIMEFRAME] before launch._\n\n"
            "**Feature Release:**\n"
            "_[FEATURE] is now live! This update brings [KEY BENEFITS]. "
            "Check out the details at [LINK] and let us know what you think._\n\n"
            "**Community Update:**\n"
            "_Quick update: [MAIN NEWS]. We're [PROGRESS/STATUS]. "
            "More details coming soon—stay tuned!_\n\n"
            "━━━━━━━━━━━━━━━\n"
            "💡 **Pro Tip:**\n"
            "1. Write your announcement using a template\n"
            "2. Send it to this chat\n"
            "3. Reply with `/rewrite` → Announcement Style\n"
            "4. Get a polished, professional version!"
        )
        bot.send_message(call.message.chat.id, template_msg, parse_mode='Markdown')
    
    elif call.data == "safety_tips":
        bot.answer_callback_query(call.id)
        safety_msg = (
            "🛡️ **Crypto Communication Safety**\n\n"
            "**🚨 NEVER share:**\n"
            "• Seed phrases (12/24 words)\n"
            "• Private keys\n"
            "• Recovery phrases\n"
            "• Wallet passwords\n\n"
            "**⚠️ Red Flags to Avoid:**\n"
            "• \"Send crypto to verify your wallet\"\n"
            "• \"Guaranteed profit\" / \"Risk-free\"\n"
            "• \"Act now\" / \"Limited time only\"\n"
            "• \"Double your crypto in 24 hours\"\n\n"
            "**✅ Safe Practices:**\n"
            "• Always verify contract addresses\n"
            "• Use official links only\n"
            "• Never rush financial decisions\n"
            "• Ask questions if unsure\n\n"
            "━━━━━━━━━━━━━━━\n"
            "💡 When you use `/rewrite`, I automatically detect these red flags and warn you before sending!"
        )
        bot.send_message(call.message.chat.id, safety_msg, parse_mode='Markdown')
    
    # --- EXISTING TON DATA CALLBACKS ---
    elif call.data == "check_price":
        p = get_ton_price()
        bot.answer_callback_query(call.id, text=f"Updated: ${p}")
        try:
            # Update the dashboard with new price
            markup = call.message.reply_markup
            updated_text = (
                f"✍️ **Quincy Communication Hub**\n"
                f"━━━━━━━━━━━━━━━\n"
                f"I help you write clear, professional, and safe TON messages.\n\n"
                f"📌 **Main Tools:**\n"
                f"• Improve any message with AI\n"
                f"• Draft professional announcements\n"
                f"• Check for scam language\n\n"
                f"━━━━━━━━━━━━━━━\n"
                f"💎 **TON Data:** Price: ${p} | ⏰ {time.strftime('%H:%M')}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"Choose an option below:"
            )
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=updated_text,
                reply_markup=markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.error(f"Error updating message: {e}")
    
    elif call.data == "check_wallet":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📍 **Paste your TON wallet address:**\n\nExample:\n`EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRv7Nw2Id_sDs`", parse_mode='Markdown')
    
    elif call.data == "set_alert_info":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🔔 **Set Price Alert**\n\nUse the command:\n`/alert [target_price]`\n\nExample: `/alert 3.50`", parse_mode='Markdown')
    
    # --- REWRITE CALLBACKS ---
    elif call.data.startswith("rewrite:"):
        bot.answer_callback_query(call.id, text="Rewriting...")
        
        # SAFE-REFERENCE CHECK: Verify original message still exists
        if not call.message.reply_to_message:
            bot.answer_callback_query(
                call.id, 
                text="❌ Original message was deleted",
                show_alert=True
            )
            bot.send_message(
                call.message.chat.id,
                "❌ **Cannot rewrite** - The original message has been deleted.\n\n"
                "Please use `/rewrite` on an existing message.",
                parse_mode='Markdown'
            )
            # Remove the orphaned button menu
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            return
        
        # Get the original text from the message that the button is attached to
        original_text = call.message.reply_to_message.text
        
        # Additional check: Verify the message has text content
        if not original_text:
            bot.answer_callback_query(
                call.id,
                text="❌ No text to rewrite",
                show_alert=True
            )
            bot.send_message(
                call.message.chat.id,
                "❌ The original message doesn't contain text to rewrite."
            )
            # Clean up button menu
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            return
        
        bot.send_chat_action(call.message.chat.id, 'typing')
        
        try:
            # SAFETY CHECK: Detect dangerous crypto phrases
            safety_warnings = check_crypto_safety(original_text)
            
            # If highly dangerous, block the rewrite and warn
            if safety_warnings.get("is_dangerous"):
                warning_msg = (
                    f"⚠️ **SECURITY WARNING**\n\n"
                    f"This message contains potentially dangerous content:\n"
                    f"{safety_warnings['warning']}\n\n"
                    f"🛡️ **Safety Tips:**\n"
                    f"• Never share your seed phrase with anyone\n"
                    f"• Never send crypto to 'verify' your wallet\n"
                    f"• Legitimate support never asks for private keys\n"
                    f"• Always verify addresses before sending funds\n\n"
                    f"❌ Rewrite blocked for your protection."
                )
                bot.send_message(
                    call.message.chat.id,
                    warning_msg,
                    parse_mode='Markdown',
                    reply_to_message_id=call.message.reply_to_message.message_id if call.message.reply_to_message else None
                )
                
                # Remove buttons
                try:
                    bot.edit_message_reply_markup(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        reply_markup=None
                    )
                except:
                    pass
                return
            
            # Determine the rewrite style
            rewrite_type = call.data.split(":")[1]
            
            # Define system prompts for each style
            style_prompts = {
                "fix_grammar": (
                    "You are a grammar expert. Fix all grammatical errors, spelling mistakes, and punctuation issues. "
                    "Keep the original tone and meaning. Only fix what's wrong - don't change the style."
                ),
                "make_pro": (
                    "You are a professional business writer. Rewrite this text in a formal, professional tone "
                    "suitable for business communication. Make it clear, concise, and polished. "
                    "Remove excessive punctuation, all caps, and overly emotional language."
                ),
                "make_announcement": (
                    "You are a communications specialist. Rewrite this text as a clear, engaging announcement. "
                    "Use a professional but enthusiastic tone. Make it attention-grabbing, well-structured, and appropriate for public communication. "
                    "Remove any urgency-based manipulation or FOMO tactics."
                ),
                "simplify": (
                    "You are a clarity expert. Rewrite this text to be simple and easy to understand. "
                    "Use short sentences, common words, and clear structure. Make it accessible to everyone."
                )
            }
            
            system_prompt = style_prompts.get(rewrite_type, style_prompts["fix_grammar"])
            system_prompt += "\n\nIMPORTANT: Provide ONLY the rewritten text. No explanations, no preambles, no meta-commentary."
            
            # Style-specific user prompts
            style_instructions = {
                "fix_grammar": f"Fix the grammar and spelling in this text:\n\n{original_text}",
                "make_pro": f"Make this text professional and business-appropriate:\n\n{original_text}",
                "make_announcement": f"Turn this into a clear, professional announcement:\n\n{original_text}",
                "simplify": f"Simplify this text for easy understanding:\n\n{original_text}"
            }
            
            user_prompt = style_instructions.get(rewrite_type, style_instructions["fix_grammar"])
            
            # Call AI to rewrite with specific error handling
            try:
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                
                rewritten_text = response.choices[0].message.content.strip()
                
            except Exception as api_error:
                # Specific handling for Groq API errors
                logging.error(f"Groq API error in rewrite: {api_error}")
                error_msg = "❌ The AI service is currently unavailable"
                
                if "rate" in str(api_error).lower():
                    error_msg += " (rate limit reached)"
                elif "auth" in str(api_error).lower() or "key" in str(api_error).lower():
                    error_msg += " (authentication error)"
                elif "timeout" in str(api_error).lower():
                    error_msg += " (service timeout)"
                
                error_msg += ". Please try again in a moment."
                
                bot.send_message(call.message.chat.id, error_msg)
                return
            
            # Generate change summary
            change_summary = generate_change_summary(original_text, rewritten_text, rewrite_type)
            
            # Style emojis for headers
            style_emojis = {
                "fix_grammar": "✨",
                "make_pro": "🧑‍💼",
                "make_announcement": "📢",
                "simplify": "🧠"
            }
            
            emoji = style_emojis.get(rewrite_type, "✍️")
            
            # Build the output message
            output_message = f"{emoji} **Quincy Rewrite:**\n\n{rewritten_text}"
            
            # Add change summary if available
            if change_summary:
                output_message += f"\n\n💡 *{change_summary}*"
            
            # Add safety note if there were minor warnings
            if safety_warnings.get("has_warning") and not safety_warnings.get("is_dangerous"):
                output_message += f"\n\n⚠️ *Note: {safety_warnings['warning']}*"
            
            # Send the rewritten version
            bot.send_message(
                call.message.chat.id,
                output_message,
                parse_mode='Markdown',
                reply_to_message_id=call.message.reply_to_message.message_id if call.message.reply_to_message else None
            )
            
            # Remove the button menu after processing
            try:
                bot.edit_message_reply_markup(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=None
                )
            except:
                pass  # Ignore if we can't remove buttons
                
        except Exception as e:
            logging.error(f"Error in rewrite callback: {e}")
            bot.send_message(call.message.chat.id, "❌ Sorry, I encountered an error while rewriting. Please try again.")

# --- 6. GENERAL HANDLER (AI CHAT + WALLET DETECTION) - MUST BE LAST! ---
@bot.message_handler(func=lambda message: True)
def handle_all(message):
    """
    Enhanced handler with aggressive wallet detection and proper fallback to AI
    """
    text = message.text.strip()
    
    # --- GREETING SHORT-CIRCUIT (keeps identity consistent) ---
    if text.lower() in {"hi", "hello", "hey", "gm", "good morning", "good afternoon", "good evening"}:
        greeting = (
            "Hi — I'm Quincy, your TON Communication Assistant.\n"
            "I help you write clear, professional, and safe TON messages inside Telegram.\n\n"
            "✅ Reply to any message with /rewrite to improve it\n"
            "🖥️ Or use /start to open the dashboard"
        )
        bot.reply_to(message, greeting)
        return
    
    # ROBUST WALLET DETECTION WITH REGEX
    # Uses regex to validate proper TON address format
    # Prevents false positives from random 48-character strings
    is_ton_address = bool(TON_ADDRESS_REGEX.match(text))
    
    if is_ton_address:
        # WALLET LOOKUP MODE - Show real blockchain data
        bot.send_chat_action(message.chat.id, 'typing')
        
        try:
            # Get real data from blockchain
            p = get_ton_price()
            t_bal = get_ton_balance(text)
            u_bal = get_usdt_balance(text)
            hist = get_last_transactions(text)
            
            # Handle None/error cases gracefully
            if t_bal is None:
                bot.reply_to(message, 
                    f"❌ **Error fetching wallet data**\n\n"
                    f"Could not retrieve balance for:\n`{text}`\n\n"
                    f"Please check:\n"
                    f"• Address is correct\n"
                    f"• Address is active on TON blockchain\n"
                    f"• Try again in a moment",
                    parse_mode='Markdown'
                )
                return
            
            ton_balance = t_bal if t_bal is not None else 0
            usdt_balance = u_bal if u_bal is not None else 0
            ton_value_usd = round(ton_balance * p, 2) if p and ton_balance else 0
            
            # Calculate total portfolio value
            total_value_usd = ton_value_usd + usdt_balance
            
            # Format transaction history
            if hist and hist != "No recent transactions found." and not hist.startswith("❌"):
                transaction_text = hist
            else:
                transaction_text = "No recent transactions found."
            
            # Build the wallet report with improved formatting
            report = (
                f"🔍 **Quincy Wallet Report**\n"
                f"━━━━━━━━━━━━━━━\n"
                f"📍 **Address:**\n`{text}`\n\n"
                f"💰 **Portfolio Value:** `${total_value_usd:.2f} USD`\n\n"
                f"💎 **TON Balance:** `{ton_balance} TON` (${ton_value_usd})\n"
                f"💵 **USDT Balance:** `{usdt_balance} USDT`\n\n"
                f"📜 **Last 5 Transactions:**\n{transaction_text}\n\n"
                f"━━━━━━━━━━━━━━━\n"
                f"📈 *Live TON Price: ${p} USD*"
            )
            
            # Use safe_send_message to handle length limits
            safe_send_message(
                message.chat.id,
                report,
                parse_mode='Markdown',
                reply_to_message_id=message.message_id
            )
            
        except Exception as e:
            logging.error(f"Error fetching wallet data: {e}")
            bot.reply_to(message, 
                f"❌ Error fetching wallet data for:\n`{text}`\n\n"
                f"Please verify the address is correct and try again.",
                parse_mode='Markdown'
            )
    
    else:
        # AI CHAT MODE - Only triggered if NOT a wallet address
        bot.send_chat_action(message.chat.id, 'typing')
        
        try:
            # Enhanced system prompt to prevent AI from inventing data
            system_prompt = (
                "You are Quincy, a TON Communication Assistant for Telegram.\n"
                "Your job is to help users communicate clearly, professionally, and safely in TON/Web3 contexts.\n\n"
                "You can help with:\n"
                "- rewriting messages (tone, clarity, announcements, simplification)\n"
                "- safety guidance for crypto communication (seed phrase / scam warnings)\n"
                "- short TON explanations ONLY when needed to improve communication\n\n"
                "Hard rules:\n"
                "- Do NOT behave like a general chatbot.\n"
                "- Do NOT ask 'Are you new to TON?' or similar onboarding questions.\n"
                "- Keep replies short and action-oriented.\n"
                "- Never invent wallet data, balances, transactions, or 'real-time' on-chain facts.\n"
                "- If user asks for wallet specifics, instruct them to paste a wallet address or use /dashboard.\n"
            )
            
            try:
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text}
                    ],
                    temperature=0.7,
                    max_tokens=500
                )
                
                bot.reply_to(message, response.choices[0].message.content)
                
            except Exception as api_error:
                # Specific handling for Groq API errors
                logging.error(f"Groq API error in chat: {api_error}")
                error_msg = "❌ I'm having trouble connecting to my AI service"
                
                if "rate" in str(api_error).lower():
                    error_msg += " due to high usage"
                elif "auth" in str(api_error).lower() or "key" in str(api_error).lower():
                    error_msg += " (configuration issue)"
                
                error_msg += ". Please try again in a moment or use /help for commands."
                bot.reply_to(message, error_msg)
            
        except Exception as e:
            logging.error(f"Error in AI handler: {e}")
            bot.reply_to(message, 
                "❌ Sorry, I encountered an error processing your message. "
                "Please try again or use /help for available commands."
            )

# --- 7. STARTUP ---
if __name__ == "__main__":
    print("🚀 Quincy is online...")
    print("━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # CRITICAL: Load persisted alerts on startup
    load_alerts()
    print(f"✅ Loaded {len(alerts)} active alert(s)")
    
    print("━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📊 Dashboard: /start or /dashboard")
    print("💰 Price: /price")
    print("🔔 Alerts: /alert [price]")
    print("✍️  Rewrite: Reply to message with /rewrite")
    print("💎 Wallet Check: Just paste a TON address")
    print("━━━━━━━━━━━━━━━━━━━━━━━━")
    
    if not TONCENTER_KEY:
        print("⚠️  WARNING: TONCENTER_API_KEY not set!")
        print("   Get a free API key from: https://toncenter.com")
        print("   Add it to your .env file as: TONCENTER_API_KEY=your_key_here")
        print("   The bot will work but with rate limits.")
    else:
        print("✅ TON Center API key loaded")
    
    if not GROQ_KEY:
        print("⚠️  WARNING: GROQ_KEY not set!")
        print("   AI features (rewrite, chat) will not work")
    else:
        print("✅ Groq AI key loaded")
    
    print("━━━━━━━━━━━━━━━━━━━━━━━━")
    logging.info("Starting bot polling...")
    
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("\n👋 Quincy shutting down...")
        save_alerts()  # Save alerts before exit
        print("✅ Alerts saved")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        save_alerts()  # Try to save alerts even on crash
        raise