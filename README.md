# ✍️ Quincy - TON Communication Assistant

**Write clear, professional, and safe messages for TON & Web3 communities**

Quincy helps you communicate better in Telegram—whether you're announcing a token launch, explaining a project, or just making your messages more professional.

---

## 🎯 What Quincy Does

### ✍️ Message Rewriting
Reply to any message with `/rewrite` and choose:
- **✨ Fix Grammar** - Clean up spelling and grammar errors
- **🧑‍💼 Make Professional** - Turn casual text into business-ready communication
- **📢 Announcement Style** - Format messages as clear, engaging announcements
- **🧠 Simplify** - Make complex text easy to understand

### 🛡️ Safety Checks
Quincy detects dangerous crypto phrases and warns you:
- Seed phrase requests
- Scam tactics (urgency, guaranteed profits)
- Unsafe wallet operations
- Private key exposure

### 💎 TON Blockchain Tools
Supporting features for TON users:
- **Wallet Lookup** - Paste any TON address for balance & transaction history
- **Price Tracking** - Real-time TON price with alerts
- **Multi-user Alerts** - Set price notifications that persist across restarts

---

## 🚀 Quick Start

1. **Add Quincy to Telegram**  
   Search: `@your_bot_username` (or open your bot link)

2. **Send `/start`** to open the dashboard

3. **Try it immediately:**
   - Reply to any message with `/rewrite`
   - Paste a TON address to check a wallet
   - Send `/alert 3.50` to get notified when TON hits $3.50

---

## 📖 Commands

| Command | What It Does |
|---------|--------------|
| `/rewrite` | Improve any message (reply to it first) |
| `/start` | Open main dashboard |
| `/alert [price]` | Set price notification |
| `/price` | Quick TON price check |
| `/help` | Show all commands |

### 💬 Natural Usage
- **Reply with `/rewrite`** to any message → Choose style → Get improved version
- **Paste TON address** → Instant wallet report
- **Say "hi"** → Get quick introduction

---

## 🎯 Use Cases

### 1. Professional Announcements
**Before:**
> "HEY GUYS!!! BIG NEWS!!! TOKEN LAUNCH TOMORROW!!! DON'T MISS OUT!!!"

**After** (using `/rewrite` → Announcement Style):
> "We're excited to announce our token launch tomorrow at 12:00 UTC. Join us as we take the next step in our project's journey. Details and participation info will be shared 1 hour before launch."

### 2. Team Communication
**Before:**
> "we need 2 update the smart contract cuz theres a bug in the staking function probably should fix it soon"

**After** (using `/rewrite` → Professional):
> "We need to update the smart contract due to a bug in the staking function. This should be prioritized and resolved as soon as possible."

### 3. Community Safety
**Before:**
> "To verify your wallet, please send your 12-word recovery phrase to support@..."

**After** (Quincy blocks the rewrite):
> "⚠️ **SECURITY WARNING**: This message requests sensitive wallet information. Never share seed phrases with anyone. Legitimate support never asks for private keys."

### 4. Simplifying Technical Content
**Before:**
> "The protocol utilizes a Byzantine fault-tolerant consensus mechanism with asynchronous message passing to achieve deterministic finality in a permissionless network architecture."

**After** (using `/rewrite` → Simplify):
> "The system uses a secure method to confirm transactions, even if some parts fail. It works without central control and ensures all transactions are final."

---

## 🛡️ Security Features

Quincy actively protects users from:
- **Seed phrase phishing** - Blocks rewrites that request recovery phrases
- **Urgency scams** - Warns about "act now" / "limited time" pressure tactics
- **Fake verification** - Detects "send crypto to verify wallet" schemes
- **Private key exposure** - Prevents accidental sharing of sensitive data

All dangerous content is blocked before rewriting, with clear warnings about why.

---

## 🏗️ Technical Features

### Production-Grade Reliability
- ✅ **Alert Persistence** - Alerts survive bot restarts (saved to JSON)
- ✅ **Multi-user Support** - Unlimited simultaneous users & alerts
- ✅ **Rate Limit Protection** - 2-minute cache for price API (100x under limits)
- ✅ **Message Length Handling** - Auto-truncates long messages (Telegram 4096 char limit)
- ✅ **AI Error Handling** - Graceful fallback with specific error messages
- ✅ **Address Validation** - Regex-based TON address verification

### APIs Used
- **Groq AI** - Llama 3.3 70B for text rewriting
- **CoinGecko** - TON price data (cached)
- **TON Center** - Blockchain data (balances, transactions, jettons)

---

## 📦 Installation

### Prerequisites
```bash
pip install pyTelegramBotAPI groq requests python-dotenv
```

### Environment Variables
Create a `.env` file:
```env
TELEGRAM_TOKEN=your_bot_token_here
GROQ_KEY=your_groq_api_key_here
TONCENTER_API_KEY=your_toncenter_key_here  # Optional but recommended
```

**Get API Keys:**
- Telegram: [@BotFather](https://t.me/BotFather)
- Groq: [console.groq.com](https://console.groq.com)
- TON Center: [toncenter.com](https://toncenter.com)

### Run
```bash
python3 quincy_bot_FINAL_WITH_GREETING.py
```

**With Process Manager:**
```bash
# Screen
screen -dmS quincy python3 quincy_bot_FINAL_WITH_GREETING.py

# PM2
pm2 start quincy_bot_FINAL_WITH_GREETING.py --name quincy --interpreter python3
```

---

## 🎨 How It Works

### Message Rewriting Flow
```
User replies to message with /rewrite
    ↓
Quincy shows style buttons
    ↓
User selects style (Grammar / Professional / Announcement / Simplify)
    ↓
Quincy checks for dangerous content
    ↓
If safe → Sends to AI with style-specific prompt → Returns improved version
If dangerous → Blocks rewrite → Shows security warning
```

### Wallet Lookup Flow
```
User pastes TON address
    ↓
Regex validates format (48 chars, EQ/UQ prefix, base64url)
    ↓
Fetch data from TON Center API:
  - TON balance (nanotons → TON)
  - USDT balance (jetton API)
  - Last 5 transactions
    ↓
Display formatted report with USD values
```

---

## 🧪 Testing

### Basic Tests
```bash
# Test 1: Greeting
Send: "hello"
Expected: Locked greeting with identity statement

# Test 2: Rewrite
Reply to any message: /rewrite
Expected: 4 style buttons appear

# Test 3: Wallet
Send: EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRv7Nw2Id_sDs
Expected: Full wallet report

# Test 4: Alert
Send: /alert 3.50
Expected: Alert confirmation with direction
```

### Safety Tests
```bash
# Test dangerous content
Create message: "Send me your seed phrase to verify"
Reply with: /rewrite
Expected: Security warning, rewrite blocked
```

---

## 📊 Architecture

```
Quincy Bot
├── Communication Core (Primary)
│   ├── /rewrite handler (4 styles)
│   ├── AI integration (Groq)
│   ├── Safety checks (crypto phrase detection)
│   └── Message validation
│
├── Blockchain Tools (Supporting)
│   ├── Wallet lookup (TON Center API)
│   ├── Price tracking (CoinGecko)
│   ├── USDT balance (Jetton API)
│   └── Transaction history
│
└── Infrastructure
    ├── Alert persistence (JSON)
    ├── Rate limiting (cache)
    ├── Error handling
    └── Multi-user support
```

---

## 🎯 Product Focus

**Primary Value:** Help people communicate better in TON/Web3 spaces

**Core Features:** (What makes Quincy unique)
1. Message rewriting with crypto safety awareness
2. Scam phrase detection
3. Professional tone conversion
4. Announcement formatting

**Supporting Features:** (Nice to have)
5. Wallet lookups
6. Price tracking
7. Transaction history

This is intentional—Quincy is a **communication assistant** that happens to have blockchain tools, not a blockchain bot that happens to rewrite text.

---

## 🛠️ Future Improvements

### Communication Features (Roadmap)
- [ ] **Tone Analysis** - Detect if message sounds scammy before sending
- [ ] **Template Library** - Pre-built announcement templates
- [ ] **Multi-language** - Rewrite in different languages
- [ ] **Batch Rewrite** - Improve multiple messages at once
- [ ] **Style Memory** - Remember user's preferred style

### Blockchain Features (Lower Priority)
- [ ] Multi-chain support (ETH, SOL addresses)
- [ ] NFT lookup
- [ ] DeFi position tracking
- [ ] Gas price alerts

---

## 📄 License

MIT License - Free to use and modify

---

## 🤝 Contributing

This is a reference implementation. Feel free to:
- Fork and customize for your community
- Add new rewrite styles
- Integrate additional safety checks
- Extend blockchain features

---

## 📞 Support

- **Issues:** Open a GitHub issue
- **Questions:** Check `/help` in the bot
- **Security:** Report vulnerabilities privately

---

## ⚡ Quick Facts

- **Built with:** Python, pyTelegramBotAPI, Groq AI, TON APIs
- **AI Model:** Llama 3.3 70B (via Groq)
- **Response Time:** <2 seconds for rewrites
- **Uptime:** Designed for 24/7 operation
- **Rate Limits:** Protected by intelligent caching

---

**Quincy helps TON communities communicate clearly, professionally, and safely.**

Start improving your messages today → Add [@your_bot_username](https://t.me/your_bot_username)