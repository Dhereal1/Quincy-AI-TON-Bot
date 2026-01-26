import os
import logging
import json
import requests
import telebot
from groq import Groq
from dotenv import load_dotenv

# 1. Setup Logging & Environment
logging.basicConfig(level=logging.INFO)
load_dotenv()

TOKEN = os.getenv('TELEGRAM_TOKEN')
GROQ_KEY = os.getenv('GROQ_KEY')
TONCENTER_KEY = os.getenv('TONCENTER_API_KEY')

bot = telebot.TeleBot(TOKEN)
client = Groq(api_key=GROQ_KEY)

# 2. Memory Management Functions
def load_memory():
    try:
        with open("chat_history.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_memory(history):
    with open("chat_history.json", "w") as f:
        json.dump(history, f)

user_history = load_memory()

# 3. Blockchain & Market Functions
def get_ton_price():
    """Fetches live price using the correct CoinGecko ID"""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd"
        response = requests.get(url, timeout=10)
        data = response.json()
        if 'the-open-network' in data:
            return data['the-open-network']['usd']
        return None
    except Exception as e:
        print(f"Price Error: {e}")
        return None

def get_ton_balance(address):
    """Fetches real-time TON balance using TonCenter API"""
    try:
        url = f"https://toncenter.com/api/v2/getAddressBalance?address={address}"
        headers = {"X-API-Key": TONCENTER_KEY}
        response = requests.get(url, headers=headers)
        data = response.json()
        if data.get("ok"):
            nanotons = int(data["result"])
            return nanotons / 10**9
        return None
    except:
        return None

# 4. AI Logic
def get_ai_response(user_id, text):
    user_id_str = str(user_id)
    if user_id_str not in user_history:
        user_history[user_id_str] = [{"role": "system", "content": "You are Quincy, a friendly TON expert."}]
    
    user_history[user_id_str].append({"role": "user", "content": text})

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=user_history[user_id_str][-10:],
            temperature=0.7
        )
        reply = response.choices[0].message.content
        user_history[user_id_str].append({"role": "assistant", "content": reply})
        save_memory(user_history)
        return reply
    except Exception as e:
        return "⚠️ My AI brain is offline. Try again later!"

# 5. Message Handlers
@bot.message_handler(commands=['start'])
def welcome(message):
    user_name = message.from_user.first_name
    welcome_text = f"👋 *Hello {user_name}! I'm Quincy.*\n\nI am your *TON Expert*. Send me a wallet address or ask me a question!"
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: "price" in message.text.lower())
def send_price(message):
    live_price = get_ton_price()
    if live_price:
        bot.reply_to(message, f"📈 **Live TON Price**: `${live_price} USD`")
    else:
        bot.reply_to(message, "Price data unavailable. 🔄")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    text = message.text.strip()
    
    # Check for Wallet Address
    if len(text) > 40 and (text.startswith("EQ") or text.startswith("UQ")):
        balance = get_ton_balance(text)
        price = get_ton_price()
        if balance is not None:
            usd_val = f" (${round(balance * price, 2)})" if price else ""
            bot.reply_to(message, f"💎 **Balance:** `{balance} TON`{usd_val}")
        else:
            bot.reply_to(message, "❌ Invalid address.")
    else:
        # Normal AI Chat
        bot.send_chat_action(message.chat.id, 'typing')
        reply = get_ai_response(message.from_user.id, text)
        bot.reply_to(message, reply)

if __name__ == "__main__":
    print("🚀 Quincy is alive and listening...")
    bot.infinity_polling()