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
- **Chat:** Simply type "What is a Jetton?" to get a simplified explanation.
- **Balance Check:** Send any TON wallet address (e.g., EQCD...) to see the current balance.
- **Safety:** Ask "How do I store my keys?" for best-practice advice.

---

👨‍💻 Developed by Opeyemi Building the future of the Open Network.