# 💎 Quincy AI: Intelligent TON Blockchain Assistant

Quincy is an advanced Telegram bot that bridges the gap between **Generative AI** and the **TON Ecosystem**. It provides users with a friendly, secure, and data-driven way to interact with the blockchain.

## 🌟 Key Features
- **🧠 AI Core:** Powered by Llama-3.3-70b via Groq for high-speed, expert-level responses.
- **🔍 Wallet Explorer:** Real-time $TON balance checking directly from the Telegram chat.
- **🛡️ Web3 Safety Guard:** Automated warnings for seed phrase protection and common scam detection.
- **💾 Persistent Memory:** Uses JSON-based local storage to remember user preferences and context.
- **📚 Expert Knowledge:** Injected with a specialized TON FAQ knowledge base.

## 🚀 Tech Stack
| Component | Technology |
| :--- | :--- |
| **Language** | Python 3.10+ |
| **Framework** | pyTelegramBotAPI |
| **Blockchain** | TonCenter API & pytonlib |
| **AI Model** | Llama-3.3-70b (Groq) |
| **Data** | JSON (Persistence) |

## 🛠️ Installation & Setup

1. **Clone the repository:**
	```bash
	git clone https://github.com/Dhereal1/Quincy-AI-TON-Bot.git
	cd Quincy-AI-TON-Bot
	```
2. **Install Dependencies:**
	```bash
	pip install -r requirements.txt
	```
3. **Environment Variables:** Create a .env file in the root directory and add your keys:
	```env
	TELEGRAM_TOKEN=your_bot_token
	GROQ_KEY=your_groq_api_key
	TONCENTER_API_KEY=your_toncenter_key
	```
4. **Run the Bot:**
	```bash
	python hello.py
	```

## 📜 Usage Examples
# 💎 Quincy AI

### Intelligent TON Blockchain Assistant for Telegram

**Quincy** is a production-ready Telegram application that acts as a **Web3 terminal for the TON ecosystem**.
It combines real-time on-chain data, market monitoring, and generative AI to help users interact with the TON blockchain through a simple, chat-based interface.

Designed for **TON users, traders, and communities**, Quincy reduces friction between complex blockchain data and everyday Telegram usage.

---

## 🚀 What Quincy Does (At a Glance)

* Answers TON-related questions using AI
* Fetches live wallet balances & transactions
* Tracks Jetton (USDT) holdings
* Monitors TON price and sends alerts
* Protects users from common Web3 scams
* Works entirely inside Telegram

No dashboards. No browser extensions. Just Telegram.

---

## 🌟 Core Features

### 🧠 AI-Powered TON Assistant

* Powered by **Llama-3.3-70B via Groq**
* Injected with a TON-specific knowledge base (Jettons, wallets, security, FAQs)
* Provides beginner-friendly explanations with expert-level accuracy

---

### 🔍 On-Chain Wallet Analytics

* **TON Balance Lookup** via Toncenter API
* **Jetton Detection** with specialized USDT tracking logic
* **Recent Transactions** (last 5) displayed in a human-readable format

Users can paste a wallet address and instantly see activity.

---

### 📈 Real-Time Market Data

* Live **TON/USD price** via CoinGecko
* Intelligent **2-minute caching system** to respect API limits
* Optimized for frequent queries without performance loss

---

### ⏰ Price Watcher & Alerts

* Background **multithreaded watcher system**
* Checks price conditions every 60 seconds
* Sends instant Telegram notifications when targets are hit

No manual refreshing needed.

---

### 🛡️ Web3 Safety Guard

* Detects and warns against:

	* Seed phrase sharing
	* Common scam patterns
* Acts as a “security layer” for new TON users

---

### 🧩 Advanced Telegram UI

* Button-based **dashboard architecture** using `InlineKeyboardMarkup`
* Persistent interface using `edit_message_text`
* Reduces chat clutter and typing errors
* App-like experience inside Telegram

---

## 🧠 Technical Highlights

* **Handler Priority System**
	Prevents AI hallucinations by routing commands (e.g. `/dashboard`) before LLM responses.

* **Persistent Memory**
	JSON-based local storage remembers user preferences and past interactions.

* **Modular Architecture**
	Market data, wallet analytics, AI logic, and watchers are cleanly separated for scalability.

---

## 🧰 Tech Stack

| Component   | Technology           |
| ----------- | -------------------- |
| Language    | Python 3.10+         |
| Telegram    | pyTelegramBotAPI     |
| Blockchain  | Toncenter API        |
| Market Data | CoinGecko API        |
| AI Engine   | Llama-3.3-70B (Groq) |
| Concurrency | Python `threading`   |
| Persistence | JSON                 |

---

## 🛠️ Installation & Setup

### 1️⃣ Clone the repository

```bash
git clone https://github.com/Dhereal1/Quincy-AI-TON-Bot.git
cd Quincy-AI-TON-Bot
```

### 2️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Environment Variables

Create a `.env` file in the root directory:

```env
TELEGRAM_TOKEN=your_bot_token
GROQ_KEY=your_groq_api_key
TONCENTER_API_KEY=your_toncenter_api_key
```

### 4️⃣ Run the bot

```bash
python hello.py
```

---

## 📜 Usage Examples

* **Ask Questions:**
	`What is a Jetton?`

* **Wallet Lookup:**
	Paste any TON wallet address (e.g. `EQCD...`) to fetch balance & activity

* **Price Alerts:**
	Set alerts and receive instant Telegram notifications

* **Security Help:**
	`How do I store my private keys safely?`

---

## 👨‍💻 Developer

**Opeyemi**
Building practical AI automation for the TON ecosystem.