import os
import logging
import json
import requests
import threading
import time
import telebot
from groq import Groq
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- 1. SETUP & CONFIG ---
logging.basicConfig(level=logging.INFO)
load_dotenv()

TOKEN = os.getenv('TELEGRAM_TOKEN')
GROQ_KEY = os.getenv('GROQ_KEY')
TONCENTER_KEY = os.getenv('TONCENTER_API_KEY')

bot = telebot.TeleBot(TOKEN)
client = Groq(api_key=GROQ_KEY)

# Globals for Alerts & Caching
alert_price = None
alert_chat_id = None
last_price = 0.0
last_update_time = 0

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

# --- 3. BACKGROUND WATCHER ---
def price_watcher():
    """Background thread to monitor price alerts"""
    global alert_price, alert_chat_id
    while True:
        if alert_price and alert_chat_id:
            current = get_ton_price()
            if current and current >= alert_price:
                try:
                    bot.send_message(alert_chat_id, f"🚨 **PRICE ALERT!**\nTON is now **${current}**!")
                    alert_price = None
                    alert_chat_id = None
                except Exception as e:
                    logging.error(f"Error sending alert: {e}")
        time.sleep(60)

threading.Thread(target=price_watcher, daemon=True).start()

# --- 4. COMMAND HANDLERS (THESE MUST BE REGISTERED FIRST!) ---

@bot.message_handler(commands=['start', 'dashboard'])
def show_dashboard(message):
    """Display the main dashboard with real-time data"""
    price = get_ton_price()
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    btn1 = InlineKeyboardButton("💎 Check Wallet", callback_data="check_wallet")
    btn2 = InlineKeyboardButton("📈 Refresh Price", callback_data="check_price")
    btn3 = InlineKeyboardButton("🔔 Set Alert", callback_data="set_alert_info")
    markup.add(btn1, btn2, btn3)
    
    dashboard_text = (
        f"🖥️ **Quincy Real-Time Dashboard**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 **Live Price:** `${price} USD`\n"
        f"⏰ **Sync Time:** {time.strftime('%H:%M:%S')}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Tap a button below for real data:"
    )
    bot.send_message(message.chat.id, dashboard_text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['alert'])
def set_alert(message):
    """Set a price alert for TON"""
    global alert_price, alert_chat_id
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Use: `/alert 2.50`", parse_mode='Markdown')
            return
        
        price = float(parts[1])
        if price <= 0:
            bot.reply_to(message, "❌ Price must be positive!")
            return
            
        alert_price, alert_chat_id = price, message.chat.id
        bot.reply_to(message, f"✅ **Target Locked!** Quincy will alert you when TON reaches **${price}**.", parse_mode='Markdown')
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
        "🤖 **Quincy Help Menu**\n"
        "━━━━━━━━━━━━━━━\n"
        "📌 **Commands:**\n"
        "`/start` - Open dashboard\n"
        "`/dashboard` - Open dashboard\n"
        "`/price` - Check TON price\n"
        "`/alert [price]` - Set price alert\n"
        "`/help` - Show this menu\n"
        "━━━━━━━━━━━━━━━\n"
        "💬 You can also chat with me naturally!"
    )
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

# --- 5. BUTTON CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    """Handle inline button clicks"""
    if call.data == "check_price":
        p = get_ton_price()
        bot.answer_callback_query(call.id, text=f"Updated: ${p}")
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"🖥️ **Quincy Real-Time Dashboard**\n━━━━━━━━━━━━━━━\n💰 **Live Price:** `${p} USD`\n⏰ **Sync Time:** {time.strftime('%H:%M:%S')}\n━━━━━━━━━━━━━━━\nTap a button below for real data:",
                reply_markup=call.message.reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.error(f"Error updating message: {e}")
    
    elif call.data == "check_wallet":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📍 **Paste your TON wallet address:**\n(Example: `EQD...abc`)", parse_mode='Markdown')
    
    elif call.data == "set_alert_info":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🔔 **Set Price Alert**\n\nUse the command:\n`/alert [target_price]`\n\nExample: `/alert 3.50`", parse_mode='Markdown')

# --- 6. GENERAL HANDLER (AI CHAT) - MUST BE LAST! ---
@bot.message_handler(func=lambda message: True)
def handle_all(message):
    """
    AI chat handler - catches all non-command messages
    This MUST be the last handler registered!
    """
    try:
        # Build conversation context
        messages = [
            {
                "role": "system", 
                "content": (
                    "You are Quincy, a helpful TON blockchain assistant. "
                    "You provide information about TON cryptocurrency, blockchain technology, "
                    "and can help users with general questions. Be concise and friendly. "
                    "If users ask about TON price, suggest they use /price or /dashboard commands."
                )
            },
            {
                "role": "user", 
                "content": message.text
            }
        ]
        
        # Call Groq API
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        reply = response.choices[0].message.content
        bot.reply_to(message, reply)
        
    except Exception as e:
        logging.error(f"Error in AI handler: {e}")
        bot.reply_to(message, "❌ Sorry, I encountered an error. Please try again or use /help for commands.")

# --- 7. STARTUP ---
if __name__ == "__main__":
    print("🚀 Quincy is online...")
    print("📊 Dashboard: /start or /dashboard")
    print("💰 Price: /price")
    print("🔔 Alerts: /alert [price]")
    print("━━━━━━━━━━━━━━━━━━━━━━━━")
    bot.infinity_polling()