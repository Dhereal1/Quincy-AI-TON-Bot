import os
import logging
import json
from dotenv import load_dotenv
import telebot
from groq import Groq

import requests

def get_ton_price():
    """Fetches the live price of Toncoin in USD from CoinGecko"""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=toncoin&vs_currencies=usd"
        response = requests.get(url)
        data = response.json()
        return data['toncoin']['usd']
    except Exception as e:
        print(f"Price Error: {e}")
        return None

# 1. Setup Logging (This shows you errors in VS Code terminal)
logging.basicConfig(level=logging.INFO)
load_dotenv()
def get_ton_balance(address):
    """Fetches real-time TON balance using TonCenter API"""
    try:
        # We use TonCenter API (replace with your key in .env)
        api_key = os.getenv('TONCENTER_API_KEY')
        url = f"https://toncenter.com/api/v2/getAddressBalance?address={address}"
        
        headers = {"X-API-Key": api_key}
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if data.get("ok"):
            # Balance comes in 'nanotons' (1 TON = 1,000,000,000 nanotons)
            nanotons = int(data["result"])
            ton_balance = nanotons / 10**9 
            return round(ton_balance, 2)
        return None
    except Exception as e:
        print(f"Error fetching balance: {e}")
        return None

# 2. MEMORY HELPERS (Permanent storage)
DB_FILE = "chat_history.json"

def load_memory():
    """Load the filing cabinet from the hard drive"""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_memory(data):
    """Save the filing cabinet to the hard drive"""
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# 3. Settings
TOKEN = os.getenv('TELEGRAM_TOKEN')
GROQ_KEY = os.getenv('GROQ_KEY')

bot = telebot.TeleBot(TOKEN)
client = Groq(api_key=GROQ_KEY)

# Load existing memory at startup
user_history = load_memory()

def get_ai_response(user_id, text):
    # Convert user_id to string (JSON keys must be strings)
    user_id_str = str(user_id)
    
    # Ensure user has a history drawer
    if user_id_str not in user_history:
        user_history[user_id_str] = [{"role": "system", "content": "You are Quincy, a helpful bot."}]
    
    user_history[user_id_str].append({"role": "user", "content": text})

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=user_history[user_id_str][-10:], # Limit memory to last 10
            temperature=0.7
        )
        reply = response.choices[0].message.content
        user_history[user_id_str].append({"role": "assistant", "content": reply})
        
        # CRITICAL: Save to file so we don't forget!
        save_memory(user_history)
        
        return reply
    except Exception as e:
        logging.error(f"AI Error: {e}")
        return "⚠️ My AI brain is offline. Try again in a minute!"

@bot.message_handler(commands=['start'])
def welcome(message):
    user_name = message.from_user.first_name
    welcome_text = (
        f"👋 *Hello {user_name}! I'm Quincy.*\n\n"
        "I am your personal *TON Blockchain Expert* and AI companion.\n\n"
        "🛡️ *How I can help:*\n"
        "• Explain TON, Jettons, and Wallets.\n"
        "• Give safety tips for Web3.\n"
        "• Chat about Python and Amala!\n\n"
        "💡 *Try asking:* 'What is a seed phrase?'"
    )
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(content_types=['sticker', 'photo', 'audio', 'video'])
def handle_non_text(message):
    bot.reply_to(message, "That looks cool! But I'm better at processing text. Try asking me a question about TON! 💎")


@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    text = message.text.strip()
    # 1. Check if the message looks like a TON address
    if len(text) > 40 and (text.startswith("EQ") or text.startswith("UQ")):
        bot.send_chat_action(message.chat.id, 'find_location') # 'Looking up...'
        balance = get_ton_balance(text)
        price = get_ton_price()
        if balance is not None and price is not None:
            usd_value = round(balance * price, 2)
            bot.reply_to(
                message,
                f"💎 **Wallet Analysis**\n\n"
                f"💰 Balance: `{balance} TON`\n"
                f"💵 Value: `${usd_value} USD` (@ ${price}/TON)\n\n"
                f"📈 *Live market data provided by CoinGecko*"
            )
        elif balance is not None:
            bot.reply_to(message, f"💎 **Wallet Found!**\n\nBalance: `{balance} TON`\n\n(USD price unavailable right now.)")
        else:
            bot.reply_to(message, "❌ I couldn't find that wallet. Make sure the address is correct!")
    # 2. Otherwise, treat it as a normal AI conversation
    else:
        bot.send_chat_action(message.chat.id, 'typing')
        ai_reply = get_ai_response(message.from_user.id, text)
        bot.reply_to(message, ai_reply)

if __name__ == "__main__":
    print("🚀 Quincy is alive and listening...")
    bot.infinity_polling()