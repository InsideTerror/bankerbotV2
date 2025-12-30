# 🏦 BankerBot - Global Economy Bridge

A Discord bot that enables cross-server currency transfers using UnbelievaBoat API.

## 📋 Features

- **Global Economy System**: Connect multiple Discord servers with different currencies
- **Automatic Currency Conversion**: Transfer funds with real-time exchange rate calculations
- **Application System**: Servers must apply and be approved by World Bank Officers
- **Full Audit Logging**: All transfers and administrative actions are logged
- **Rate Limiting**: Built-in protection against API abuse
- **Officer Management**: Secure role-based access control

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Discord Bot Token ([Get one here](https://discord.com/developers/applications))
- UnbelievaBoat API Key ([Get one here](https://unbelievaboat.com/api))
- A Discord server to act as your "Central Bank"

### Installation

1. **Clone or download this repository**

```bash
git clone https://github.com/yourusername/bankerbot.git
cd bankerbot
```

2. **Create a virtual environment** (recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure the bot**

Edit `bot.py` and update these values:

```python
DISCORD_TOKEN = "YOUR_DISCORD_BOT_TOKEN_HERE"
UNB_API_KEY = "YOUR_UNBELIEVABOAT_API_KEY_HERE"
CENTRAL_BANK_SERVER_ID = 1234567890  # Your Central Bank server ID
APPROVAL_CHANNEL_ID = 1234567890  # Channel for approval messages
OWNER_USER_ID = 1234567890  # Your Discord user ID
```

**How to get these IDs:**
- Enable Developer Mode in Discord (User Settings → Advanced → Developer Mode)
- Right-click on server/channel/user → Copy ID

5. **Run the bot**

```bash
python bot.py
```

## 📁 Project Structure

```
bankerbot/
├── bot.py                  # Main entry point
├── cogs/
│   ├── database.py        # Database operations
│   ├── unbelievaboat.py   # UnbelievaBoat API integration
│   ├── economy.py         # Economy commands (optin, list, withdraw)
│   ├── transfer.py        # Transfer command
│   └── admin.py           # Admin commands (kick, cleanup)
├── requirements.txt       # Python dependencies
├── README.md             # This file
└── bankerbot.db          # SQLite database (auto-created)
```

## 🎮 Commands

### For Server Administrators

| Command | Description | Required Permission |
|---------|-------------|---------------------|
| `/economy optin` | Apply to join the global economy | Manage Server |
| `/economy list` | View all economies and their status | None |
| `/economy withdraw` | Leave the global economy | Administrator |

### For All Users

| Command | Description |
|---------|-------------|
| `/transfer` | Transfer currency between approved servers |

### For World Bank Officers

| Command | Description |
|---------|-------------|
| `/kick_economy` | Remove a server from the global economy |
| `/cleanup_transfers` | Delete old transfer logs |

### For Bot Owner (via DM)

Send these commands as DMs to the bot:

- `add officer <user_id>` - Grant officer privileges
- `remove officer <user_id>` - Revoke officer privileges
- `list officers` - Show all officers
- `officer help` - Show help message

## 📝 Setup Checklist

### 1. Discord Bot Setup

- [ ] Create application at https://discord.com/developers/applications
- [ ] Create bot and copy token
- [ ] Enable these Privileged Gateway Intents:
  - Server Members Intent
  - Message Content Intent
- [ ] Invite bot with these permissions:
  - Send Messages
  - Embed Links
  - Read Message History
  - Use Slash Commands

### 2. UnbelievaBoat Setup

- [ ] Add UnbelievaBoat to all participating servers
- [ ] Get API key from https://unbelievaboat.com/api
- [ ] For each server, approve BankerBot's API access:
  1. Go to https://unbelievaboat.com/applications
  2. Click "Authorize" next to your application
  3. Select the server
  4. Grant permissions

### 3. Central Bank Setup

- [ ] Create a dedicated "Central Bank" server (or use existing)
- [ ] Create an "applications" channel for approval messages
- [ ] Copy server ID and channel ID to bot.py
- [ ] Add your Discord user ID to bot.py as OWNER_USER_ID

### 4. First Run

- [ ] Run the bot
- [ ] Check that it connects successfully
- [ ] DM the bot: `officer help` to verify owner status
- [ ] Add at least one officer: `add officer <user_id>`
- [ ] Test `/economy list` in any server

## 🔧 Configuration Options

Edit these values in `bot.py` to customize behavior:

```python
bot.config = {
    'api_delay': 1.0,  # Seconds between API calls
    'min_exchange_rate': 0.01,  # Minimum rate against USD
    'max_exchange_rate': 10000.0,  # Maximum rate against USD
    'min_transfer_amount': 1.0,  # Minimum transfer amount
    'max_transfer_amount': 1000000.0  # Maximum transfer amount
}
```

## 🎯 Usage Example

### Server Joins the Economy

1. Admin runs `/economy optin`:
   - Currency: "Gold Coins"
   - Rate: 50 (50 Gold Coins = 1 USD)
   - Symbol: 🪙
   - Note: "Roleplay medieval server"

2. Message appears in Central Bank approval channel
3. Officer clicks "Approve ✅"
4. Server receives confirmation message

### User Transfers Currency

1. User in Server A has 1000 🪙 Gold Coins
2. User runs `/transfer`:
   - Source: "Medieval Kingdom" (Server A)
   - Target: "Space Station" (Server B)
   - Amount: 500
   - Wallet: Cash
3. Bot calculates conversion:
   - 500 🪙 = 10 USD
   - 10 USD = 200 ⭐ (Server B rate: 20 ⭐ = 1 USD)
4. User confirms transfer
5. 500 🪙 deducted from Server A
6. 200 ⭐ added to Server B

## 🛡️ Security Features

- **Application Approval**: Prevents abuse by requiring officer review
- **Officer-Only Commands**: Sensitive commands only visible to authorized users
- **Rate Limiting**: Prevents API overload
- **Transaction Logging**: All transfers logged for 6 months
- **Rollback Protection**: Failed transfers automatically roll back
- **Balance Validation**: Checks balance before and during transfer

## 🐛 Troubleshooting

### Bot won't start
- Check Python version: `python --version` (needs 3.11+)
- Verify all dependencies installed: `pip install -r requirements.txt`
- Check bot token is correct
- Enable logging to see detailed errors

### Commands not showing
- Wait 1 hour for Discord to sync commands globally
- Or kick and re-invite bot to force sync
- Check bot has "applications.commands" scope

### API errors
- Verify UnbelievaBoat API key is correct
- Check that each server has approved API access
- Ensure UnbelievaBoat bot is in the server
- Check API rate limits (1 req/second default)

### Transfer fails
- Verify both servers are approved (not pending/rejected)
- Check user has sufficient balance
- Ensure both servers have UnbelievaBoat API access
- Check database for any errors in logs

### Officer commands not working
- Verify user ID is added: DM bot `list officers`
- Check bot owner ID is correct in bot.py
- Try adding officer again: `add officer <user_id>`

## 📊 Database Schema

The bot uses SQLite with these tables:

- **economies**: Server applications and status
- **transfers**: All currency transfers
- **approved_officers**: Authorized users
- **audit_log**: All administrative actions

Data retention:
- Transfers: 6 months (auto-cleanup)
- Economies: Permanent until withdrawn/kicked
- Audit logs: Permanent

## 🔄 Updates and Maintenance

### Updating the bot
1. Pull latest changes
2. Install any new dependencies: `pip install -r requirements.txt`
3. Restart the bot

### Regular maintenance
- Run `/cleanup_transfers` every few months
- Review audit logs periodically
- Update exchange rates if needed (servers must reapply)

## 📄 License

See LICENSE file for details.

## 🤝 Support

For issues or questions:
1. Check this README
2. Review bot logs: `bankerbot.log`
3. Check database: `bankerbot.db`
4. Open an issue on GitHub

## 🎉 Credits

Built with:
- [discord.py](https://github.com/Rapptz/discord.py) - Discord API wrapper
- [UnbelievaBoat](https://unbelievaboat.com) - Currency system
- [aiosqlite](https://github.com/omnilib/aiosqlite) - Async SQLite

---

Made with ❤️ for the roleplay community
