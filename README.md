# Discord Minecraft & Economy Bot

A feature-rich Discord bot for Minecraft server communities, combining server status, fun games, and a full-fledged economy system with leveling, inventory, and trading. This bot is built using [discord.py](https://github.com/Rapptz/discord.py) and is designed for easy customization and deployment.

---

## Features

### 🛠️ Server & Utility
- **Minecraft Server Status**: Check server status, player list, and IP for both Java and Bedrock.
- **Server Info**: View Discord server details, user info, role info, and avatars.
- **Leave Notifications**: Set a channel to receive notifications when members leave.
- **Polls & Suggestions**: Create polls and submit suggestions to a dedicated channel.

### 💰 Economy & Leveling
- **Wallet & Bank**: Earn, deposit, withdraw, and transfer virtual currency.
- **Daily & Work Rewards**: Claim daily rewards and work for random payouts.
- **Gambling**: Play coinflip, Russian roulette, and crime for a chance to win or lose money.
- **Robbery & Adventure**: Rob other users or embark on adventures for random outcomes.
- **Inventory System**: Collect, buy, sell, and trade items of varying rarities.
- **Tools & Mining**: Buy tools (metal detectors, pickaxes) to search or mine for items.
- **Leaderboard**: View the richest users and top levels.
- **Leveling**: Gain XP and level up by using commands.

### 🎮 Fun & Games
- **Counting Game**: Set up a counting channel with reset or non-reset options.
- **Adventure**: Random events with rewards or penalties.

### 🛡️ Admin Controls
- **Set Rewards & Cooldowns**: Configure daily/work rewards, robbery chance, and cooldowns.
- **Role Management**: Add or remove roles from humans, bots, or specific members.
- **Sync Commands**: Sync slash commands globally or per guild.

---

## Setup & Installation

### 1. Requirements
- Python 3.8+
- [discord.py](https://pypi.org/project/discord.py/) (2.0+ recommended)
- [mcstatus](https://pypi.org/project/mcstatus/)
- [python-dotenv](https://pypi.org/project/python-dotenv/)

Install dependencies:
```bash
pip install discord.py mcstatus python-dotenv
```

### 2. Configuration
Create a `.env` file in the same directory as the bot with the following variables:
```
DISCORD_TOKEN=your_discord_bot_token
MINECRAFT_SERVER_IP=your.minecraft.server.ip
MINECRAFT_SERVER_PORT=25565
```

- **Do NOT share your `.env` file or bot token.**

### 3. Running the Bot
Run the bot with:
```bash
python bot.py
```

---

## Usage

### Command Prefix
- The bot responds to `i!` or `I!` (e.g., `i!help`).
- Slash commands are also supported (e.g., `/help`).

### Help Menu
- Use `i!help` or `/help` to view all commands, grouped by category.

### Economy Commands
- `i!daily` / `/daily` — Claim daily reward
- `i!work` / `/work` — Work for money
- `i!balance` / `/balance` — Check your balance
- `i!deposit <amount/all>` / `/deposit` — Deposit money
- `i!withdraw <amount/all>` / `/withdraw` — Withdraw money
- `i!give <user> <amount>` — Give money to another user
- `i!rob <user>` / `/rob` — Attempt to rob someone
- `i!russianroulette <amount>` — Gamble in Russian Roulette
- `i!crime` — Attempt a risky crime
- `i!coinflip <heads/tails> <amount/all/half>` — Bet on a coin flip
- `i!search` — Use a metal detector to find items
- `i!mine` — Use a pickaxe to mine items
- `i!adventure` — Go on a random adventure
- `i!inventory` — View your inventory
- `i!buytool` — Buy a metal detector
- `i!buypickaxe` — Buy a pickaxe
- `i!sell <index/all> <amount>` — Sell items
- `i!trade <user> <item> <amount>` — Trade items
- `i!leaderboard` — View the richest users
- `i!profile` — View your full profile

### Server & Utility Commands
- `i!ip` / `/ip` — Show Minecraft server IP
- `i!status` / `/status` — Show server status
- `i!players` / `/players` — List online players
- `i!serverinfo` / `/serverinfo` — Discord server info
- `i!userinfo` / `/userinfo` — User info
- `i!avatar` / `/avatar` — User avatar
- `i!roleinfo` / `/roleinfo` — Role info
- `i!support` / `/support` — Support info

### Fun & Admin Commands
- `i!setchannel <#channel> reset/dontreset` — Set counting game channel
- `i!poll <question> <options>` / `/poll` — Create a poll
- `i!setsuggestionchannel <#channel>` — Set suggestion channel
- `i!suggest <text>` / `/suggest` — Submit a suggestion
- `i!setdaily <amount>` — Set daily reward (admin)
- `i!setrobchance <chance>` — Set robbery chance (admin)
- `i!addrole <human/bots/member> <role> [@member]` — Add role (admin)
- `i!removerole <human/bots/member> <role> [@member]` — Remove role (admin)
- `i!leave <#channel>` — Set leave notification channel (admin)
- `i!sync` — Sync slash commands (owner)

---

## Data Files
- `economy_data.json` — Stores user balances, inventory, tools, etc.
- `level_data.json` — Stores user XP and levels.
- `counting_game_data.json` — Counting game state.
- `suggestion_channels.json` — Suggestion channel settings.
- `leave_channels.json` — Leave notification channels.

**Do not share these files publicly.**

---

## Customization
- Edit the `settings` dictionary in the code to change default economy values.
- Add or modify items, tools, and rarities in the `item_data` and `tools` dictionaries.
- Update the help command and embeds for your server branding.

---

## Notes
- The bot requires the following Discord permissions: `Read Messages`, `Send Messages`, `Embed Links`, `Manage Roles` (for role commands), and `Read Message History`.
- For best results, run the bot on a server with Python 3.8+ and keep your dependencies up to date.
- Make sure your bot has the necessary intents enabled in the Discord Developer Portal (especially for member and message content).

---

## License
This project is provided as-is for educational and community use. Please review and modify as needed for your own server.

---

## Credits
If you use this code or any part of it, please give credit to **[Rutwik2003](https://github.com/Rutwik2003)** (my GitHub username).

If you have any issues or questions, feel free to contact me via Discord at **rocky_rutwik**. 