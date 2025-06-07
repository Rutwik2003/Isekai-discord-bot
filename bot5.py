import sys
import discord
from discord.ext import commands
from discord import app_commands  # For slash commands
from mcstatus import JavaServer
import os
import json
from dotenv import load_dotenv
import re
import asyncio
from discord.ui import Button, View
import random
from datetime import datetime, timedelta
import time
from discord.ui import View, Button
from discord.ext.commands import BucketType

# Add the Economy cog class after your existing imports but before any commands
class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.level_data = {}
        self.exp_per_command = 5  # Amount of XP earned per command
        self.load_level_data()

    def load_level_data(self):
        try:
            with open('level_data.json', 'r') as f:
                self.level_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading level data: {e}")
            self.level_data = {}


    def save_level_data(self):
        with open('level_data.json', 'w') as f:
            json.dump(self.level_data, f, indent=4)

    def add_experience(self, user_id, amount):
        user_id = str(user_id)
        user_data = self.level_data.get(user_id, {"exp": 0, "level": 1})
        user_data["exp"] += amount
        level_up = False

        while user_data["exp"] >= self.get_exp_to_next_level(user_data["level"]):
            user_data["exp"] -= self.get_exp_to_next_level(user_data["level"])
            user_data["level"] += 1
            level_up = True

        self.level_data[user_id] = user_data
        self.save_level_data()
        return level_up, user_data["level"]

    def get_exp_to_next_level(self, level):
        """Scaling formula for XP required to level up"""
        return 100 + (level - 1) * 50  # XP increases as level increases

    @commands.command(name="level", aliases=["lvl"])
    async def level(self, ctx, member: discord.Member = None):
        """Check your or another user's level."""
        user = member or ctx.author
        user_id = str(user.id)

        if user_id not in self.level_data:
            self.level_data[user_id] = {"exp": 0, "level": 1}
            self.save_level_data()

        user_data = self.level_data[user_id]
        level = user_data["level"]
        exp = user_data["exp"]
        exp_to_next_level = self.get_exp_to_next_level(level)

        progress_bar_length = 20
        filled_length = int(progress_bar_length * exp / exp_to_next_level)
        progress_bar = "█" * filled_length + "—" * (progress_bar_length - filled_length)

        embed = discord.Embed(
            title=f"🌟 {user.name}'s Level",
            description=(
                f"**Level:** {level}\n"
                f"**Experience:** {exp}/{exp_to_next_level}\n"
                f"Progress: `{progress_bar}`"
            ),
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)


    @commands.Cog.listener()
    async def on_command(self, ctx):
        if ctx.author.bot:
            return  # Ignore bots

        # Award XP
        level_up, new_level = self.add_experience(ctx.author.id, self.exp_per_command)

        if level_up:
            await ctx.send(f"🎉 {ctx.author.mention} leveled up to **Level {new_level}**!")




class Economy(commands.Cog):
    def __init__(self, bot,leveling_cog):
        self.bot = bot
        self.leveling_cog = leveling_cog
        self.command_cooldowns = {}
        self.cooldowns = {}
        self.set_global_cooldowns = {}
        self.settings = {
            'daily_amount': 1000,
            'work_min': 100,
            'work_max': 500,
            'rob_chance': 40,
            'rob_min_percent': 10,
            'rob_max_percent': 30
        }
        self.tools = {
    "metal_detector": {
        "basic": {"cost": 4000, "rarity_boost": 1.0, "emoji": "🔍"},
        "advanced": {"cost": 9000, "rarity_boost": 1.5, "emoji": "📡"},
        "pro": {"cost": 20000, "rarity_boost": 2.0, "emoji": "🛰️"},
    },
    "pickaxe": {
        "wooden": {"cost": 2500, "rarity_boost": 1.0, "emoji": "⛏️"},
        "iron": {"cost": 8000, "rarity_boost": 1.5, "emoji": "🪓"},
        "diamond": {"cost": 25000, "rarity_boost": 2.0, "emoji": "⚒️"},
    },
}

        self.item_data = {
    "common": {
        "🍎": {"name": "Apple", "value": 50},      # Affordable and low-value
        "🥖": {"name": "Bread", "value": 75},     # Slightly higher than Apple
        "🪨": {"name": "Rock", "value": 60},      # Mid-range common item
    },
    "uncommon": {
        "🥩": {"name": "Steak", "value": 150},    # Higher than common items
        "🧀": {"name": "Cheese", "value": 120},   # More than common, less than Steak
        "🪵": {"name": "Wood Plank", "value": 180},  # Valuable uncommon material
    },
    "rare": {
        "💎": {"name": "Diamond", "value": 1000},   # Significant jump in value
        "⚒️": {"name": "Iron Ingot", "value": 750}, # Rare crafting material
        "🪙": {"name": "Gold Coin", "value": 850},  # Rare currency
    },
    "epic": {
        "🔮": {"name": "Magic Crystal", "value": 2500},  # High-value epic item
        "🗡️": {"name": "Enchanted Sword", "value": 2000},  # Powerful weapon
        "🏺": {"name": "Ancient Vase", "value": 2200},      # Collectible item
    },
    "legendary": {
        "🧙‍♂️": {"name": "Wizard's Staff", "value": 5000}, # Top-tier magic item
        "🗿": {"name": "Relic Idol", "value": 6000},        # Priceless artifact
        "👑": {"name": "King's Crown", "value": 8000},      # Ultimate legendary
    },
}

        self.load_economy()
    
    def get_exp_to_next_level(self, level):
        """Calculate experience required for the next level."""
        return 100 + (level - 1) * 50  # Example scaling formula for XP
 
 
    def get_global_cooldown(self, user_id, command):
        now = time.time()
        if user_id not in self.global_cooldowns:
            self.global_cooldowns[user_id] = {}
        user_cooldowns = self.global_cooldowns[user_id]
        if command in user_cooldowns:
            remaining_time = user_cooldowns[command] - now
            if remaining_time > 0:
                return remaining_time
        return 0
    def is_on_cooldown(self, user_id, command, cooldown_seconds):
        now = time.time()
        if user_id not in self.command_cooldowns:
            self.command_cooldowns[user_id] = {}
        user_cooldowns = self.command_cooldowns[user_id]

        if command in user_cooldowns:
            if now < user_cooldowns[command]:
                return user_cooldowns[command] - now  # Remaining time
        return 0

    def set_cooldown(self, user_id, command, cooldown_seconds):
        now = time.time()
        if user_id not in self.command_cooldowns:
            self.command_cooldowns[user_id] = {}
        self.command_cooldowns[user_id][command] = now + cooldown_seconds
        
        
    def set_global_cooldown(self, user_id, command, cooldown_seconds):
        now = time.time()
        if user_id not in self.global_cooldowns:
            self.global_cooldowns[user_id] = {}
        self.global_cooldowns[user_id][command] = now + cooldown_seconds


    # def load_economy(self):
    #     try:
    #         with open('economy_data.json', 'r') as f:
    #             self.economy_data = json.load(f)
    #     except FileNotFoundError:
    #         self.economy_data = {}
    def load_economy(self):
        try:
            with open('economy_data.json', 'r') as f:
                self.economy_data = json.load(f)
            
            # Ensure all items in inventory have the 'quantity' key
            for user_id, data in self.economy_data.items():
                for item in data.get("inventory", []):
                    item.setdefault("quantity", 1)  # Default quantity to 1 if missing
            
            print("Economy data loaded successfully.")
        except FileNotFoundError:
            self.economy_data = {}
            print("No economy data file found. Starting fresh.")

    def add_experience(self, user_id, amount):
        account = self.get_account(user_id)
        account['xp'] += amount

        # Check for level-up
        xp_needed = 100 + (account['level'] - 1) * 50  # Increase XP requirement per level
        while account['xp'] >= xp_needed:
            account['xp'] -= xp_needed
            account['level'] += 1
            xp_needed = 100 + (account['level'] - 1) * 50

        self.save_economy()


        
    def save_economy(self):
        with open('economy_data.json', 'w') as f:
            json.dump(self.economy_data, f, indent=4)

    def get_account(self, user_id):
        if str(user_id) not in self.economy_data:
            self.economy_data[str(user_id)] = {
                'wallet': 0,
                'bank': 0,
                'last_daily': None,
                'level': 1,               # New field for user level
                'xp': 0,                  # New field for experience points
                'pets': [],
            }
            self.save_economy()
        return self.economy_data[str(user_id)]

    @commands.command(name='sync', aliases=['resync'])
    @commands.is_owner()
    async def sync_commands(self, ctx):
        """
        Syncs slash commands globally.
        """
        try:
            # Sync global commands
            synced_global = await self.bot.tree.sync()
            
            # Optionally sync for a specific guild (uncomment if you have specific guild commands)
            #synced_guild = await self.bot.tree.sync(guild=discord.Object(id=YOUR_GUILD_ID))
            
            await ctx.send(f"✅ Synced {len(synced_global)} global commands.")
        except Exception as e:
            await ctx.send(f"❌ Failed to sync commands: {e}")



    @commands.command(name="leaderboard", aliases=["lvlboard"])
    async def leaderboard(self, ctx):
        """Show the leveling leaderboard."""
        sorted_users = sorted(
            self.level_data.items(),
            key=lambda x: (x[1]["level"], x[1]["exp"]),
            reverse=True
        )[:10]

        embed = discord.Embed(
            title="🏆 Level Leaderboard",
            color=discord.Color.blurple()
        )
        for rank, (user_id, data) in enumerate(sorted_users, 1):
            user = await self.bot.fetch_user(int(user_id))
            embed.add_field(
                name=f"{rank}. {user.name}",
                value=f"Level: {data['level']} | EXP: {data['exp']}",
                inline=False
            )

        await ctx.send(embed=embed)




    @commands.command(aliases=['bal'])
    async def balance(self, ctx, member: discord.Member = None):
        """Check your or another user's balance"""
        user = member or ctx.author
        account = self.get_account(user.id)
        
        embed = discord.Embed(
            title=f"💰 {user.name}'s Balance",
            color=discord.Color.green()
        )
        embed.add_field(name="Wallet", value=f"${account['wallet']:,}", inline=True)
        embed.add_field(name="Bank", value=f"${account['bank']:,}", inline=True)
        embed.add_field(name="Total", value=f"${(account['wallet'] + account['bank']):,}", inline=True)
        
        await ctx.send(embed=embed)

    @app_commands.command(name="balance", description="Check your or another user's balance")
    async def slash_balance(self, interaction: discord.Interaction, member: discord.Member = None):
        user = member or interaction.user
        account = self.get_account(user.id)
        embed = discord.Embed(
            title=f"💰 {user.name}'s Balance",
            color=discord.Color.green()
        )
        embed.add_field(name="Wallet", value=f"${account['wallet']:,}", inline=True)
        embed.add_field(name="Bank", value=f"${account['bank']:,}", inline=True)
        embed.add_field(name="Total", value=f"${(account['wallet'] + account['bank']):,}", inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="work", description="Work to earn money")
    async def slash_work(self, interaction: discord.Interaction):
        cooldown_time = 30  # 30 Seconds
        remaining = self.is_on_cooldown(interaction.user.id, 'work', cooldown_time)
        if remaining > 0:
            friendly_time = f"{int(remaining // 3600)}h {int((remaining % 3600) // 60)}m {int(remaining % 60)}s"
            await interaction.response.send_message(f"❌ You are on cooldown! Try again in **{friendly_time}**.")
            return

        account = self.get_account(interaction.user.id)
        earnings = random.randint(self.settings['work_min'], self.settings['work_max'])
        account['wallet'] += earnings
        self.save_economy()
        self.set_cooldown(interaction.user.id, 'work', cooldown_time)
        embed = discord.Embed(
            title="Work Complete",
            description=f"You worked hard and earned ${earnings:,}!",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @commands.command(name='coinflip', aliases=['cf'])
    async def coinflip(self, ctx, choice: str, amount: str):
        """
        Play a coin flip game with suspense animation.
        Usage:
        i!coinflip <heads/tails> <amount/all/half>
        """
        account = self.get_account(ctx.author.id)

        # Validate choice
        choice = choice.lower()
        if choice not in ['heads', 'tails', 'h', 't']:
            await ctx.send("❌ Invalid choice! Use 'heads' or 'tails' (or 'h' and 't').")
            return

        # Convert shorthand choice
        choice = 'heads' if choice in ['heads', 'h'] else 'tails'

        # Handle amount
        if amount.lower() == 'all':
            amount = account['wallet']
        elif amount.lower() == 'half':
            amount = account['wallet'] // 2
        else:
            try:
                amount = int(amount)
            except ValueError:
                await ctx.send("❌ Invalid amount! Use a number, 'all', or 'half'.")
                return

        if amount <= 0:
            await ctx.send("❌ Bet amount must be positive!")
            return

        if amount > account['wallet']:
            await ctx.send("❌ You don't have enough money to make that bet!")
            return

        # Animation messages
        suspense_messages = ["Flipping the coin... 🪙", "It's spinning... 🔄", "Almost there... 🤔"]
        msg = await ctx.send(suspense_messages[0])
        for suspense in suspense_messages[1:]:
            await asyncio.sleep(2)  # Pause for 2 seconds between messages
            await msg.edit(content=suspense)

        # Determine the coin flip result
        await asyncio.sleep(2)  # Add a short delay before revealing the result
        result = random.choice(['heads', 'tails'])
        win = result == choice

        if win:
            winnings = amount * 2
            account['wallet'] += winnings
            result_message = f"🎉 The coin landed on **{result.capitalize()}**! You won **${winnings:,}**!"
            color = discord.Color.green()
        else:
            account['wallet'] -= amount
            result_message = f"💔 The coin landed on **{result.capitalize()}**. You lost **${amount:,}**."
            color = discord.Color.red()

        # Save account changes
        self.save_economy()

        # Create and send embed
        embed = discord.Embed(
            title="Coin Flip Result",
            description=result_message,
            color=color
        )
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)
        await msg.edit(content=None, embed=embed)


    @commands.command(name="adventure",aliases=['adv'])
    @commands.cooldown(1, 900, commands.BucketType.user)  # 30-minute cooldown
    async def adventure(self, ctx):
        """
        Embark on an adventure for random outcomes with exciting scenarios!
        """
        account = self.get_account(ctx.author.id)

        # Define possible outcomes
        outcomes = [
            # Big Wins
            {"message": "You discovered a **hidden treasure chest** full of gold! 💰", "earnings": random.randint(500, 1500), "item": None},
            {"message": "You found a **rare artifact** and sold it for a fortune! 🏺", "earnings": random.randint(700, 1200), "item": "Ancient Artifact 🏺"},

            # Moderate Wins
            {"message": "You helped a **wandering merchant** and earned a reward. 🛍️", "earnings": random.randint(300, 500), "item": "Merchant's Token 🪙"},
            {"message": "You stumbled upon a **stash of coins** hidden under a tree. 🌳", "earnings": random.randint(200, 400), "item": None},

            # Small Wins
            {"message": "You found some **loose change** on your journey. 🪙", "earnings": random.randint(50, 150), "item": None},
            {"message": "You collected **herbs and berries** from the forest. 🌿", "earnings": random.randint(100, 200), "item": "Forest Herbs 🌿"},

            # Neutral Outcomes
            {"message": "You got lost in the woods but eventually found your way back. 🌲", "earnings": 0, "item": None},
            {"message": "You spent the day exploring but found nothing of value. 🕵️‍♂️", "earnings": 0, "item": None},

            # Small Losses
            {"message": "You accidentally stepped on a thorn and had to pay for treatment. 🩹", "earnings": -random.randint(50, 150), "item": None},
            {"message": "You dropped your wallet while crossing a river. 🌊", "earnings": -random.randint(100, 300), "item": None},

            # Moderate Losses
            {"message": "You were ambushed by **bandits** and lost some of your money. 🦹", "earnings": -random.randint(300, 500), "item": None},
            {"message": "You traded with a **shady merchant** and got scammed. 🤦", "earnings": -random.randint(300, 700), "item": None},

            # Big Losses
            {"message": "A **dragon** attacked your camp, and you had to flee, leaving valuables behind. 🐉", "earnings": -random.randint(500, 1000), "item": None},
            {"message": "You got caught in a **storm** and lost some of your supplies. ⛈️", "earnings": -random.randint(400, 800), "item": None},
        ]

        # Randomly select an outcome
        outcome = random.choice(outcomes)
        earnings = outcome["earnings"]
        item = outcome["item"]

        # Update account based on outcome
        account['wallet'] += earnings
        if item:
            # Add the item to inventory
            inventory = account.setdefault("inventory", [])
            found = False
            for inv_item in inventory:
                if inv_item["item"] == item:
                    inv_item["quantity"] += 1
                    found = True
                    break
            if not found:
                inventory.append({"item": item, "value": random.randint(200, 500), "quantity": 1})

        # Save account changes
        self.save_economy()

        # Create earnings message
        earnings_message = (
            f"You earned **${earnings:,}**!" if earnings > 0 else
            f"You lost **${-earnings:,}**!" if earnings < 0 else
            "You neither gained nor lost money."
        )
        item_message = f"You also found **{item}**!" if item else ""

        # Send adventure result
        embed = discord.Embed(
            title="Adventure Result",
            description=f"{outcome['message']}\n\n{earnings_message}\n{item_message}",
            color=discord.Color.green() if earnings > 0 else discord.Color.red() if earnings < 0 else discord.Color.greyple()
        )
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)
        await ctx.send(embed=embed)

        
        
        

    @app_commands.command(name="daily", description="Claim your daily reward")
    async def slash_daily(self, interaction: discord.Interaction):
        cooldown_time = 86400  # 24 hours
        remaining = self.is_on_cooldown(interaction.user.id, 'daily', cooldown_time)
        if remaining > 0:
            friendly_time = f"{int(remaining // 3600)}h {int((remaining % 3600) // 60)}m {int(remaining % 60)}s"
            await interaction.response.send_message(f"❌ You are on cooldown! Try again in **{friendly_time}**.")
            return

        account = self.get_account(interaction.user.id)
        amount = self.settings['daily_amount']
        account['wallet'] += amount
        self.save_economy()
        self.set_cooldown(interaction.user.id, 'daily', cooldown_time)
        embed = discord.Embed(
            title="Daily Reward",
            description=f"You received ${amount:,} in your wallet!",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="deposit", description="Deposit money into your bank")
    @app_commands.describe(amount="Amount to deposit or 'all'")
    async def slash_deposit(self, interaction: discord.Interaction, amount: str):
        account = self.get_account(interaction.user.id)
        if amount.lower() == 'all':
            amount = account['wallet']
        else:
            try:
                amount = int(amount)
            except ValueError:
                await interaction.response.send_message("Please enter a valid amount or 'all'.")
                return

        if amount <= 0:
            await interaction.response.send_message("Amount must be positive!")
            return
        if amount > account['wallet']:
            await interaction.response.send_message("You don't have that much money in your wallet!")
            return

        account['wallet'] -= amount
        account['bank'] += amount
        self.save_economy()
        embed = discord.Embed(
            title="Deposit Successful",
            description=f"Deposited ${amount:,} into your bank!",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="withdraw", description="Withdraw money from your bank")
    @app_commands.describe(amount="Amount to withdraw or 'all'")
    async def slash_withdraw(self, interaction: discord.Interaction, amount: str):
        account = self.get_account(interaction.user.id)
        if amount.lower() == 'all':
            amount = account['bank']
        else:
            try:
                amount = int(amount)
            except ValueError:
                await interaction.response.send_message("Please enter a valid amount or 'all'.")
                return

        if amount <= 0:
            await interaction.response.send_message("Amount must be positive!")
            return
        if amount > account['bank']:
            await interaction.response.send_message("You don't have that much money in your bank!")
            return

        account['bank'] -= amount
        account['wallet'] += amount
        self.save_economy()
        embed = discord.Embed(
            title="Withdrawal Successful",
            description=f"Withdrew ${amount:,} from your bank!",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rob", description="Attempt to rob another user")
    @app_commands.describe(victim="The user you want to rob")
    async def slash_rob(self, interaction: discord.Interaction, victim: discord.Member):
        if victim.id == interaction.user.id:
            await interaction.response.send_message("❌ You can't rob yourself!")
            return

        cooldown_time = 3600  # 1 Hour
        remaining = self.is_on_cooldown(interaction.user.id, 'rob', cooldown_time)
        if remaining > 0:
            friendly_time = f"{int(remaining // 3600)}h {int((remaining % 3600) // 60)}m {int(remaining % 60)}s"
            await interaction.response.send_message(f"❌ You are on cooldown! Try again in **{friendly_time}**.")
            return

        robber_account = self.get_account(interaction.user.id)
        victim_account = self.get_account(victim.id)
        if victim_account['wallet'] < 100:
            await interaction.response.send_message("❌ This user doesn't have enough money to rob!")
            return

        if random.randint(1, 100) <= self.settings['rob_chance']:
            steal_percent = random.randint(self.settings['rob_min_percent'], self.settings['rob_max_percent'])
            amount = int(victim_account['wallet'] * (steal_percent / 100))
            victim_account['wallet'] -= amount
            robber_account['wallet'] += amount
            self.save_economy()
            result = f"You successfully robbed **${amount:,}** from {victim.name}!"
            color = discord.Color.green()
        else:
            fine = random.randint(100, 1000)
            robber_account['wallet'] -= fine
            self.save_economy()
            result = f"You were caught and fined **${fine:,}**!"
            color = discord.Color.red()

        self.set_cooldown(interaction.user.id, 'rob', cooldown_time)
        embed = discord.Embed(
            title="Robbery Attempt",
            description=result,
            color=color
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="View the richest users")
    async def slash_leaderboard(self, interaction: discord.Interaction):
        sorted_users = sorted(
            self.economy_data.items(),
            key=lambda x: x[1]['wallet'] + x[1]['bank'],
            reverse=True
        )[:10]
        embed = discord.Embed(
            title="💎 Leaderboard: Richest Users 💎",
            color=discord.Color.gold()
        )
        for rank, (user_id, data) in enumerate(sorted_users, 1):
            user = await self.bot.fetch_user(int(user_id))
            total = data['wallet'] + data['bank']
            embed.add_field(
                name=f"{rank}. {user.name}",
                value=f"💼 Wallet: ${data['wallet']:,}\n🏦 Bank: ${data['bank']:,}\n💰 Total: ${total:,}",
                inline=False
            )
        await interaction.response.send_message(embed=embed)


    @commands.command()
    async def work(self, ctx):
        """Work to earn money"""
        cooldown_time = 30  # 30 Seconds
        remaining = self.is_on_cooldown(ctx.author.id, 'work', cooldown_time)

        if remaining > 0:
            friendly_time = f"{int(remaining // 3600)}h {int((remaining % 3600) // 60)}m {int(remaining % 60)}s"
            await ctx.send(f"❌ You are on cooldown! Try again in **{friendly_time}**.")
            return

        account = self.get_account(ctx.author.id)
        earnings = random.randint(self.settings['work_min'], self.settings['work_max'])
        account['wallet'] += earnings
        self.save_economy()

        self.set_cooldown(ctx.author.id, 'work', cooldown_time)

        jobs = [
            "🛠 helped moderate a Discord server",
            "🐞fixed some bugs in the matrix",
            "sold virtual lemonade 🍹",
            "mined some diamonds 💎",
            "wrote some code 👨‍💻",
            "created memes 🤣",
            "👨‍🎨created some art 🎨",
            "created some music 🎶",
        ]

        embed = discord.Embed(
            title="Work Complete",
            description=f"You {random.choice(jobs)} and earned ${earnings:,}!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    
    @commands.command()
    async def daily(self, ctx):
        """Claim your daily reward"""
        cooldown_time = 86400  # 24 hours
        remaining = self.is_on_cooldown(ctx.author.id, 'daily', cooldown_time)

        if remaining > 0:
            friendly_time = f"{int(remaining // 3600)}h {int((remaining % 3600) // 60)}m {int(remaining % 60)}s"
            await ctx.send(f"❌ You are on cooldown! Try again in **{friendly_time}**.")
            return

        account = self.get_account(ctx.author.id)
        amount = self.settings['daily_amount']
        account['wallet'] += amount
        self.save_economy()

        self.set_cooldown(ctx.author.id, 'daily', cooldown_time)

        embed = discord.Embed(
            title="Daily Reward",
            description=f"You received ${amount:,} in your wallet!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)


    @commands.command(aliases=['dep'])
    async def deposit(self, ctx, amount: str):
        """Deposit money into your bank"""
        account = self.get_account(ctx.author.id)
        cooldown_time = 5  # Cooldown in seconds
        remaining = self.is_on_cooldown(ctx.author.id, 'deposit', cooldown_time)

        if remaining > 0:
            await ctx.send(f"❌ You are on cooldown! Try again in {int(remaining)} seconds.")
            return

        if amount.lower() == 'all':
            amount = account['wallet']
        else:
            try:
                amount = int(amount)
            except ValueError:
                await ctx.send("Please enter a valid amount or 'all'.")
                return

        if amount <= 0:
            await ctx.send("Amount must be positive!")
            return

        if amount > account['wallet']:
            await ctx.send("You don't have that much money in your wallet!")
            return

        account['wallet'] -= amount
        account['bank'] += amount
        self.save_economy()
        self.set_cooldown(ctx.author.id, 'deposit', cooldown_time)

        embed = discord.Embed(
            title="Deposit Successful",
            description=f"Deposited ${amount:,} into your bank!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=['with'])
    async def withdraw(self, ctx, amount: str):
        """Withdraw money from your bank"""
        account = self.get_account(ctx.author.id)
        cooldown_time = 5  # Cooldown in seconds
        remaining = self.is_on_cooldown(ctx.author.id, 'withdraw', cooldown_time)

        if remaining > 0:
            await ctx.send(f"❌ You are on cooldown! Try again in {int(remaining)} seconds.")
            return

        if amount.lower() == 'all':
            amount = account['bank']
        else:
            try:
                amount = int(amount)
            except ValueError:
                await ctx.send("Please enter a valid amount or 'all'.")
                return

        if amount <= 0:
            await ctx.send("Amount must be positive!")
            return

        if amount > account['bank']:
            await ctx.send("You don't have that much money in your bank!")
            return

        account['bank'] -= amount
        account['wallet'] += amount
        self.save_economy()
        self.set_cooldown(ctx.author.id, 'withdraw', cooldown_time)

        embed = discord.Embed(
            title="Withdrawal Successful",
            description=f"Withdrew ${amount:,} from your bank!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @commands.command()
    async def rob(self, ctx, victim: discord.Member):
        """Attempt to rob another user"""
        cooldown_time = 3600  # 1 Hour
        remaining = self.is_on_cooldown(ctx.author.id, 'rob', cooldown_time)

        if remaining > 0:
            friendly_time = f"{int(remaining // 3600)}h {int((remaining % 3600) // 60)}m {int(remaining % 60)}s"
            await ctx.send(f"❌ You are on cooldown! Try again in **{friendly_time}**.")
            return

        if victim.id == ctx.author.id:
            await ctx.send("❌ You can't rob yourself!")
            return

        robber_account = self.get_account(ctx.author.id)
        victim_account = self.get_account(victim.id)

        if victim_account['wallet'] < 100:
            await ctx.send("❌ This user doesn't have enough money to rob!")
            return

        if random.randint(1, 100) <= self.settings['rob_chance']:
            steal_percent = random.randint(
                self.settings['rob_min_percent'],
                self.settings['rob_max_percent']
            )
            amount = int(victim_account['wallet'] * (steal_percent / 100))

            victim_account['wallet'] -= amount
            robber_account['wallet'] += amount
            self.save_economy()
            result = f"You successfully robbed ${amount:,} from {victim.name}!"
            color = discord.Color.green()
        else:
            fine = random.randint(100, 1000)
            robber_account['wallet'] -= fine
            self.save_economy()
            result = f"You were caught and fined ${fine:,}!"
            color = discord.Color.red()

        self.set_cooldown(ctx.author.id, 'rob', cooldown_time)

        embed = discord.Embed(
            title="Robbery Attempt",
            description=result,
            color=color
        )
        await ctx.send(embed=embed)
        
    @commands.command()
    async def crime(self, ctx):
        """Attempt to commit a crime for a chance at a big payout"""
        cooldown_time = 7200  # 2 hours
        remaining = self.is_on_cooldown(ctx.author.id, 'crime', cooldown_time)

        if remaining > 0:
            friendly_time = f"{int(remaining // 3600)}h {int((remaining % 3600) // 60)}m {int(remaining % 60)}s"
            await ctx.send(f"❌ You are on cooldown! Try again in **{friendly_time}**.")
            return

        account = self.get_account(ctx.author.id)
        success_chance = 15  # 15% chance to succeed
        success_reward_range = (1000, 10000)  # Reward range on success
        failure_penalty_range = (200, 1000)  # Penalty range on failure

        if random.randint(1, 100) <= success_chance:
            reward = random.randint(*success_reward_range)
            account['wallet'] += reward
            self.save_economy()
            result = f"🎉 You successfully pulled off the crime and earned **${reward:,}**!"
            color = discord.Color.green()
        else:
            penalty = random.randint(*failure_penalty_range)
            account['wallet'] -= penalty
            self.save_economy()
            result = f"🚓 You were caught and fined **${penalty:,}**!"
            color = discord.Color.red()

        self.set_cooldown(ctx.author.id, 'crime', cooldown_time)

        embed = discord.Embed(
            title="Crime Attempt",
            description=result,
            color=color
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=['rr'])
    async def russianroulette(self, ctx, amount: str):
        """Play Russian Roulette with adjustable risks."""
        account = self.get_account(ctx.author.id)

        # Handle 'all' subcommand
        if amount.lower() == "all":
            amount = account["wallet"]
            reduced_win_chance = 2  # Only 2 chances to win out of 6
        else:
            try:
                amount = int(amount)
                reduced_win_chance = 1  # Default win chances out of 6
            except ValueError:
                await ctx.send("❌ Invalid amount! Use a number or 'all'.")
                return

        if amount <= 0:
            await ctx.send("❌ Bet amount must be positive!")
            return

        if amount > account["wallet"]:
            await ctx.send("❌ You don't have enough money!")
            return

        embed = discord.Embed(
            title="Russian Roulette",
            description="🔫 Spinning the chamber...",
            color=discord.Color.gold()
        )
        msg = await ctx.send(embed=embed)

        # Simulate suspense
        suspense_steps = ["🔫 Click... Nothing happened.", "🔫 Click... Still safe.", "🔫 Click... Almost there."]
        for step in suspense_steps:
            embed.description = step
            await msg.edit(embed=embed)
            await asyncio.sleep(2)

        # Determine result
        if random.randint(1, 10) > reduced_win_chance:  # Adjusted for reduced chances on "all"
            account["wallet"] -= amount
            result = f"💥 BANG! You lost **${amount:,}**."
            color = discord.Color.red()
        else:
            winnings = amount * 2
            account["wallet"] += winnings
            result = f"😅 Click! You survived and won **${winnings:,}**!"
            color = discord.Color.green()

        self.save_economy()

        embed = discord.Embed(
            title="Russian Roulette Result",
            description=result,
            color=color
        )
        await msg.edit(embed=embed)

    @commands.command()
    async def give(self, ctx, member: discord.Member, amount: int):
        """Give money to another user"""
        cooldown_time = 5  # 5 seconds
        remaining = self.is_on_cooldown(ctx.author.id, 'give', cooldown_time)

        if remaining > 0:
            await ctx.send(f"❌ You are on cooldown! Try again in {int(remaining)} seconds.")
            return

        if member.id == ctx.author.id:
            await ctx.send("You can't give money to yourself!")
            return

        if amount <= 0:
            await ctx.send("Amount must be positive!")
            return

        giver_account = self.get_account(ctx.author.id)
        receiver_account = self.get_account(member.id)

        if amount > giver_account['wallet']:
            await ctx.send("You don't have enough money!")
            return

        giver_account['wallet'] -= amount
        receiver_account['wallet'] += amount
        self.save_economy()
        self.set_cooldown(ctx.author.id, 'give', cooldown_time)

        embed = discord.Embed(
            title="Money Transfer",
            description=f"You gave ${amount:,} to {member.name}!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    
    # @commands.command(aliases=['lb'])
    # async def leaderboard(self, ctx):
    #     """Show the richest users"""
    #     sorted_users = sorted(
    #         self.economy_data.items(),
    #         key=lambda x: x[1]['wallet'] + x[1]['bank'],
    #         reverse=True
    #     )[:10]
        
    #     embed = discord.Embed(
    #         title="💰 Richest Users",
    #         color=discord.Color.gold()
    #     )
        
    #     for i, (user_id, data) in enumerate(sorted_users, 1):
    #         user = self.bot.get_user(int(user_id))
    #         if user:
    #             total = data['wallet'] + data['bank']
    #             embed.add_field(
    #                 name=f"{i}. {user.name}",
    #                 value=f"${total:,}",
    #                 inline=False
    #             )
        
    #     await ctx.send(embed=embed)
    
    
    # Search & Mine Game Code 
    @commands.command(name="buytool", aliases=["buyt"])
    async def buy_tool(self, ctx):
        """Buy a search tool."""
        tools = self.tools["metal_detector"]
        tool_type = "metal_detector"  # Define the tool type explicitly
        embed = discord.Embed(
            title="🛠️ Buy Metal Detector",
            description="React to buy one of the tools:",
            color=discord.Color.blue(),
        )
        reactions = []
        for i, (name, data) in enumerate(tools.items(), 1):
            emoji = data["emoji"]
            price = data["cost"]
            embed.add_field(name=f"{emoji} {name.capitalize()} Detector", value=f"Price: ${price:,}", inline=False)
            reactions.append(f"{i}\N{COMBINING ENCLOSING KEYCAP}")

        msg = await ctx.send(embed=embed)
        for reaction in reactions:
            await msg.add_reaction(reaction)

        def check(reaction, user):
            return (
                user == ctx.author
                and str(reaction.emoji) in reactions
                and reaction.message.id == msg.id
            )

        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("⏳ Time's up! Purchase cancelled.")
            return

        index = reactions.index(str(reaction.emoji))
        selected_tool = list(tools.items())[index]
        tool_name, data = selected_tool
        price = data["cost"]
        account = self.get_account(ctx.author.id)
        if account["wallet"] >= price:
            account["wallet"] -= price
            account.setdefault("tools", {})[tool_type] = {"name": tool_name, "uses_remaining": random.randint(1, 6)}
            self.save_economy()
            await ctx.send(f"✅ You successfully bought a {tool_name.capitalize()} {tool_type} with {account['tools'][tool_type]['uses_remaining']} uses remaining!")
        else:
            await ctx.send("❌ You don't have enough money in your wallet!")


    @commands.command(name="buypickaxe", aliases=["buypick"])
    async def buy_pickaxe(self, ctx):
        """Buy a mining pickaxe."""
        tools = self.tools["pickaxe"]
        tool_type = "pickaxe"  # Define the tool type explicitly
        embed = discord.Embed(
            title="⛏️ Buy Pickaxe",
            description="React to buy one of the pickaxes:",
            color=discord.Color.orange(),
        )
        reactions = []
        for i, (name, data) in enumerate(tools.items(), 1):
            emoji = data["emoji"]
            price = data["cost"]
            embed.add_field(name=f"{emoji} {name.capitalize()} Pickaxe", value=f"Price: ${price:,}", inline=False)
            reactions.append(f"{i}\N{COMBINING ENCLOSING KEYCAP}")

        msg = await ctx.send(embed=embed)
        for reaction in reactions:
            await msg.add_reaction(reaction)

        def check(reaction, user):
            return (
                user == ctx.author
                and str(reaction.emoji) in reactions
                and reaction.message.id == msg.id
            )

        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("⏳ Time's up! Purchase cancelled.")
            return

        index = reactions.index(str(reaction.emoji))
        selected_tool = list(tools.items())[index]
        tool_name, data = selected_tool
        price = data["cost"]
        account = self.get_account(ctx.author.id)
        if account["wallet"] >= price:
            account["wallet"] -= price
            account.setdefault("tools", {})[tool_type] = {"name": tool_name, "uses_remaining": random.randint(1, 6)}
            self.save_economy()
            await ctx.send(f"✅ You successfully bought a {tool_name.capitalize()} {tool_type} with {account['tools'][tool_type]['uses_remaining']} uses remaining!")
        else:
            await ctx.send("❌ You don't have enough money in your wallet!")



    # Search command with cooldown
    # Search command with cooldown and error handling
    @commands.command(name="search")
    @commands.cooldown(1, 30, BucketType.user)  # 1 use per 30 seconds per user
    async def search(self, ctx):
        """Search for random items using a metal detector."""
        account = self.get_account(ctx.author.id)

        # Check if the user has tools
        if "tools" not in account or not account["tools"]:
            await ctx.send("❌ You don't own any metal detector! Purchase one using `i!buytool`.")
            return

        # Get the metal detector from the tools dictionary
        metal_detector = account["tools"].get("metal_detector")
        if not metal_detector:
            await ctx.send("❌ You need a metal detector to search! Purchase one using `i!buytool`.")
            return

        # Check remaining uses
        if metal_detector["uses_remaining"] <= 0:
            del account["tools"]["metal_detector"]
            self.save_economy()
            await ctx.send("❌ Your metal detector broke! Purchase a new one using `i!buytool`.")
            return

        # Perform the search
        rarity_weights = {
            "common": 60,
            "uncommon": 25,
            "rare": 10,
            "epic": 4,
            "legendary": 1,
        }
        rarity = random.choices(list(rarity_weights.keys()), weights=rarity_weights.values(), k=1)[0]
        item_emoji, item_data = random.choice(list(self.item_data[rarity].items()))

        # Update inventory: Group identical items and maintain quantities
        found = False
        for item in account.setdefault("inventory", []):
            if item["item"] == item_data["name"]:
                item["quantity"] = item.get("quantity", 1)  # Ensure quantity exists
                item["quantity"] += 1
                found = True
                break

        if not found:
            account["inventory"].append({
                "item": item_data["name"],
                "value": item_data["value"],
                "emoji": item_emoji,
                "quantity": 1  # Ensure new items have a quantity
            })

        # Decrement tool usage
        metal_detector["uses_remaining"] -= 1
        if metal_detector["uses_remaining"] <= 0:
            del account["tools"]["metal_detector"]
            await ctx.send("❗ Your metal detector broke after this search! Purchase a new one using `i!buytool`.")
        self.save_economy()

        # Response
        await ctx.send(f"🔍 You used your metal detector and found a **{item_data['name']}** {item_emoji} worth ${item_data['value']:,}!")


    @search.error
    async def search_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            retry_after = int(error.retry_after)
            friendly_time = f"{retry_after // 60}m {retry_after % 60}s"
            await ctx.send(f"⏳ You are on cooldown! Try again in **{friendly_time}**.")





    # Mine command with cooldown
   # Mine command with cooldown and error handling
    @commands.command(name="mine")
    @commands.cooldown(1, 30, BucketType.user)  # 1 use per 30 seconds per user
    async def mine(self, ctx):
        """Mine for random items using a pickaxe."""
        account = self.get_account(ctx.author.id)

        if "tools" not in account or not account["tools"]:
            await ctx.send("❌ You don't own any pickaxe! Purchase one using `i!buypickaxe`.")
            return

        pickaxe = account["tools"].get("pickaxe")
        if not pickaxe:
            await ctx.send("❌ You need a pickaxe to mine! Purchase one using `i!buypickaxe`.")
            return

        # Check remaining uses
        if pickaxe["uses_remaining"] <= 0:
            del account["tools"]["pickaxe"]
            self.save_economy()
            await ctx.send("❌ Your pickaxe broke! Purchase a new one using `i!buypickaxe`.")
            return

        # Perform the mining
        rarity_weights = {
            "common": 50,
            "uncommon": 30,
            "rare": 15,
            "epic": 4,
            "legendary": 1,
        }
        rarity = random.choices(list(rarity_weights.keys()), weights=rarity_weights.values(), k=1)[0]
        item_emoji, item_data = random.choice(list(self.item_data[rarity].items()))

        # Update inventory and tool usage
        found = False
        for item in account.setdefault("inventory", []):
            if item["item"] == item_data["name"]:
                item["quantity"] = item.get("quantity", 1)  # Ensure quantity exists
                item["quantity"] += 1
                found = True
                break

        if not found:
            account["inventory"].append({
                "item": item_data["name"],
                "value": item_data["value"],
                "emoji": item_emoji,
                "quantity": 1  # Ensure new items have a quantity
            })

        # Decrement tool usage
        pickaxe["uses_remaining"] -= 1
        if pickaxe["uses_remaining"] <= 0:
            del account["tools"]["pickaxe"]
            await ctx.send("❗ Your pickaxe broke after this mining session! Purchase a new one using `i!buypickaxe`.")
        self.save_economy()

        # Response
        await ctx.send(f"⛏️ You used your pickaxe and mined a **{item_data['name']}** {item_emoji} worth ${item_data['value']:,}!")


    @mine.error
    async def mine_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            retry_after = int(error.retry_after)
            friendly_time = f"{retry_after // 60}m {retry_after % 60}s"
            await ctx.send(f"⏳ You are on cooldown! Try again in **{friendly_time}**.")

        
    @commands.command(name="inventory", aliases=["inv"])
    async def inventory(self, ctx):
        """Show your inventory of collected items grouped by rarity and tools."""
        account = self.get_account(ctx.author.id)

        # Ensure all items in the inventory have proper rarity
        inventory = account.get("inventory", [])
        items_by_rarity = {
            "common": [],
            "uncommon": [],
            "rare": [],
            "epic": [],
            "legendary": []
        }

        # Group items by rarity
        for item in inventory:
            rarity = None
            for rarity_level, items in self.item_data.items():
                if item["item"] in [i["name"] for i in items.values()]:
                    rarity = rarity_level
                    break
            if rarity:
                items_by_rarity[rarity].append(item)

        # Build inventory display with proper indexing
        inventory_display = ""
        indexed_inventory = []
        index = 1
        for rarity, items in items_by_rarity.items():
            if items:
                inventory_display += f"**{rarity.capitalize()}**\n"
                for item in items:
                    quantity = item.get("quantity", 1)  # Ensure quantity exists
                    value = item.get("value", 0)
                    emoji = item.get("emoji", "❓")  # Show ❓ if emoji is missing
                    inventory_display += f"{index}. {emoji} {item['item']} (x{quantity}, ${value:,})\n"
                    item_with_index = item.copy()
                    item_with_index["index"] = index
                    indexed_inventory.append(item_with_index)
                    index += 1

        # Store indexed inventory in the account for quick reference in `sell`
        account["indexed_inventory"] = indexed_inventory

        # Tools Section
        tools = account.get("tools", {})
        tools_display = (
            "\n".join(
                f"{tool_info.get('emoji', '❓')} {tool_name.capitalize()} - {tool_info.get('uses_remaining', 0)} uses left"
                for tool_name, tool_info in tools.items()
            )
            or "No tools available."
        )

        # Create and send the embed
        embed = discord.Embed(
            title=f"🎒 {ctx.author.name}'s Inventory",
            description="Here's what you currently own:",
            color=discord.Color.green()
        )
        embed.add_field(name="Items", value=inventory_display or "No items in inventory.", inline=False)
        embed.add_field(name="Tools", value=tools_display, inline=False)

        await ctx.send(embed=embed)



    @commands.command(name="sell")
    async def sell(self, ctx, index: str, amount: int = 1):
        """
        Sell items from your inventory.
        - Use `i!sell <index> <amount>` to sell a specific item.
        - Use `i!sell all` to sell all items in the inventory.
        """
        account = self.get_account(ctx.author.id)

        # Handle "sell all" subcommand
        if index.lower() == "all":
            inventory = account.get("inventory", [])
            if not inventory:
                await ctx.send("🎒 Your inventory is empty! Start searching or mining to find items.")
                return

            total_earnings = 0
            for item in inventory:
                quantity = item.get("quantity", 1)
                value = item.get("value", 0)
                total_earnings += quantity * value

            # Clear inventory and update wallet
            account["inventory"] = []
            account["wallet"] += total_earnings
            self.save_economy()

            await ctx.send(
                f"✅ Sold all items in your inventory for a total of **${total_earnings:,}**! "
                f"Your wallet now has **${account['wallet']:,}**."
            )
            return

        # Handle selling by index
        try:
            index = int(index)  # Validate if index is an integer
        except ValueError:
            await ctx.send("❌ Invalid index! Use `i!sell <index>` or `i!sell all`.")
            return

        # Ensure the inventory exists and is not empty
        inventory = account.get("inventory", [])
        if not inventory:
            await ctx.send("🎒 Your inventory is empty! Start searching or mining to find items.")
            return

        # Ensure the index is valid
        if index < 1 or index > len(inventory):
            await ctx.send(f"❌ Invalid index! Please choose a valid item index (1-{len(inventory)}).")
            return

        # Get the item at the specified index
        item_entry = inventory[index - 1]
        item_name = item_entry["item"]
        item_quantity = item_entry.get("quantity", 1)

        # Check if there is enough quantity to sell
        if amount > item_quantity:
            await ctx.send(f"❌ You only have {item_quantity}x {item_name}.")
            return

        # Calculate earnings and update inventory
        earnings = item_entry["value"] * amount
        item_entry["quantity"] -= amount

        # Remove the item if quantity reaches zero
        if item_entry["quantity"] <= 0:
            inventory.pop(index - 1)

        # Update the account
        account["wallet"] += earnings
        self.save_economy()

        await ctx.send(
            f"✅ Sold {amount}x **{item_name}** for **${earnings:,}**. "
            f"Your wallet now has **${account['wallet']:,}**."
        )


    @commands.command(name="profile")
    async def profile(self, ctx, member: discord.Member = None):
        """Displays the profile of a user, including economy stats, levels, items, and inventory."""
        user = member or ctx.author
        user_id = str(user.id)

        # Economy Data
        account = self.get_account(user.id)
        wallet = account.get("wallet", 0)
        bank = account.get("bank", 0)
        total_coins = wallet + bank

        # Fetch Leveling Data from the Leveling cog
        level_data = self.leveling_cog.level_data
        if user_id not in level_data:
            level_data[user_id] = {"exp": 0, "level": 1}
            self.leveling_cog.save_level_data()

        user_data = level_data[user_id]
        level = user_data["level"]
        xp = user_data["exp"]
        exp_to_next_level = self.leveling_cog.get_exp_to_next_level(level)

        # Progress Bar
        progress_bar_length = 20  # Length of the progress bar
        filled_length = int(progress_bar_length * xp / exp_to_next_level)
        progress_bar = "█" * filled_length + "—" * (progress_bar_length - filled_length)

        # Tools
        tools = account.get("tools", {})
        tools_display = "\n".join(
            f"{data.get('emoji', '❓')} {tool.capitalize()} - {data.get('uses_remaining', 0)} uses left"
            for tool, data in tools.items()
        ) or "No tools owned."

        # Pets
        pets = account.get("pets", [])
        pets_display = ", ".join(pets) or "No pets owned."

        # Inventory
        inventory = account.get("inventory", [])
        inventory_display = ""
        for item in inventory:
            item_name = item.get("item", "Unknown Item")
            emoji = item.get("emoji", "❓")
            quantity = item.get("quantity", 1)
            value = item.get("value", 0)
            inventory_display += f"{emoji} {item_name} (x{quantity}, ${value:,} each)\n"

        if not inventory_display:
            inventory_display = "No items in inventory."

        # Embed
        embed = discord.Embed(
            title=f"{user.name}'s Profile",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=user.avatar.url)

        # Add Fields
        embed.add_field(
            name="💰 **Economy**",
            value=f"**Wallet:** ${wallet:,}\n**Bank:** ${bank:,}\n**Total:** ${total_coins:,}",
            inline=False
        )
        embed.add_field(
            name="🎮 **Leveling**",
            value=(
                f"**Level:** {level}\n"
                f"**XP:** {xp}/{exp_to_next_level}\n"
                f"Progress: `{progress_bar}`"
            ),
            inline=False
        )
        embed.add_field(name="🛠️ **Tools**", value=tools_display, inline=False)
        embed.add_field(name="🐾 **Pets**", value=pets_display, inline=False)
        embed.add_field(name="🎒 **Inventory**", value=inventory_display, inline=False)

        # Footer
        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.avatar.url)

        await ctx.send(embed=embed)







    @commands.command(name="trade")
    async def trade(self, ctx, member: discord.Member, item_name: str, amount: int = 1):
        """Trade an item with another user."""
        if member.id == ctx.author.id:
            await ctx.send("❌ You can't trade with yourself!")
            return

        sender_account = self.get_account(ctx.author.id)
        receiver_account = self.get_account(member.id)

        # Check if sender has the item
        if "inventory" not in sender_account or not sender_account["inventory"]:
            await ctx.send("🎒 Your inventory is empty! Start searching or mining to find items.")
            return

        # Search for the item in sender's inventory
        for item in sender_account["inventory"]:
            if item["item"].lower() == item_name.lower():
                if amount > 0:
                    # Check if user has enough of the item to trade
                    count = sum(1 for i in sender_account["inventory"] if i["item"].lower() == item_name.lower())
                    if count >= amount:
                        # Remove the traded items from sender and add to receiver
                        traded_items = [i for i in sender_account["inventory"] if i["item"].lower() == item_name.lower()][:amount]
                        sender_account["inventory"] = [i for i in sender_account["inventory"] if i not in traded_items]
                        receiver_account.setdefault("inventory", []).extend(traded_items)
                        self.save_economy()

                        await ctx.send(f"✅ Traded {amount}x {item_name} to {member.mention}.")
                        return
                    else:
                        await ctx.send(f"❌ You only have {count}x {item_name}.")
                        return
                else:
                    await ctx.send("❌ Amount to trade must be positive!")
                    return
        await ctx.send("❌ Item not found in your inventory!")

    
    
    
    
    
    
    @commands.command(aliases=['lb'])
    async def leaderboard(self, ctx):
        """Show the richest users in style"""
        sorted_users = sorted(
            self.economy_data.items(),
            key=lambda x: x[1]['wallet'] + x[1]['bank'],
            reverse=True
        )[:10]
        
        # Embed setup
        embed = discord.Embed(
            title="💎 **Leaderboard: Richest Users** 💎",
            description=(
                "Welcome to the **Economy Leaderboard**! These are the top 10 wealthiest users in the system. "
                "Climb the ranks and make it to the top! 🚀"
            ),
            color=discord.Color.gold()
        )
        
        medals = ["🥇", "🥈", "🥉"]  # Gold, Silver, Bronze medals for the top 3
        
        for i, (user_id, data) in enumerate(sorted_users, 1):
            user = self.bot.get_user(int(user_id))
            if user:
                wallet = data['wallet']
                bank = data['bank']
                total = wallet + bank
                medal = medals[i - 1] if i <= 3 else "✨"  # Assign medals to top 3 or a sparkle emoji
                
                embed.add_field(
                    name=f"{medal} **{i}. {user.name}**",
                    value=(
                        f"**💼 Wallet:** `${wallet:,}`\n"
                        f"**🏦 Bank:** `${bank:,}`\n"
                        f"**💰 Total:** `${total:,}`"
                    ),
                    inline=False
                )
        
        # Enhance the embed footer and aesthetics
        embed.set_footer(
            text=f"Requested by {ctx.author.name} • Keep grinding for the top! 🏆",
            icon_url=ctx.author.avatar.url
        )
        embed.set_thumbnail(
             url="https://cdn.discordapp.com/avatars/845661604699701278/4899feb202f9ee24cebb085f0dde7802.png?size=4096"  # Replace with a relevant thumbnail URL
        )
        # embed.set_image(
        #     url="https://i.imgur.com/a5WlG5W.png"  # Optional banner image URL
        # )
        embed.timestamp = ctx.message.created_at
        
        await ctx.send(embed=embed)



    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setdaily(self, ctx, amount: int):
        """Set the daily reward amount"""
        self.settings['daily_amount'] = amount
        await ctx.send(f"Daily reward amount set to ${amount:,}")
        
@commands.command(name='setwork')
@commands.has_permissions(administrator=True)
async def setwork(self, ctx, min_earnings: int, max_earnings: int, cooldown: int):
    """Set work earnings range and cooldown"""
    if min_earnings <= 0 or max_earnings <= 0 or cooldown <= 0:
        await ctx.send("❌ All values must be positive!")
        return

    if min_earnings > max_earnings:
        await ctx.send("❌ Minimum earnings cannot be greater than maximum earnings!")
        return

    self.settings['work_min'] = min_earnings
    self.settings['work_max'] = max_earnings

    # Change the cooldown of the work command dynamically
    self.bot.get_command('work').reset_cooldown(ctx)
    self.bot.get_command('work').cooldown = commands.Cooldown(1, cooldown, commands.BucketType.user)

    await ctx.send(
        f"✅ Work earnings range set to ${min_earnings:,} - ${max_earnings:,} with a cooldown of {cooldown} seconds!"
    )
    
    @commands.command(name='setrobchance')
    @commands.has_permissions(administrator=True)
    async def setrobchance(self, ctx, chance: int):
        """Set the robbery success chance"""
        if chance < 0 or chance > 100:
            await ctx.send("❌ Robbery chance must be between 0% and 100%!")
            return

        self.settings['rob_chance'] = chance
        await ctx.send(f"✅ Robbery success chance set to {chance}%!")

async def cog_command_error(self, ctx, error):
    """Handles errors for commands in this cog."""
    if isinstance(error, commands.CommandOnCooldown):
        retry_after = int(error.retry_after)
        # Convert seconds into a human-readable format
        hours, remainder = divmod(retry_after, 3600)
        minutes, seconds = divmod(remainder, 60)

        # Create a friendly cooldown message
        time_parts = []
        if hours > 0:
            time_parts.append(f"{hours}h")
        if minutes > 0:
            time_parts.append(f"{minutes}m")
        if seconds > 0 or not time_parts:
            time_parts.append(f"{seconds}s")

        friendly_time = " ".join(time_parts)

        embed = discord.Embed(
            title="⏳ Command Cooldown",
            description=f"You are on cooldown. Try again in **{friendly_time}**.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)

    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="❌ Missing Argument",
            description=f"You're missing a required argument for this command. Use `i!help <command>` for details.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

    elif isinstance(error, commands.BadArgument):
        embed = discord.Embed(
            title="❌ Bad Argument",
            description=f"One of the arguments provided is invalid. Please check your input and try again.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

    elif isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ Insufficient Permissions",
            description="You don't have the required permissions to run this command.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

    else:
        # Raise other errors for debugging or custom handling elsewhere
        raise error




    


load_dotenv()

# Load configurations
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
MINECRAFT_SERVER_IP = os.getenv('MINECRAFT_SERVER_IP')
MINECRAFT_SERVER_PORT = int(os.getenv('MINECRAFT_SERVER_PORT'))
SERVER_VERSION = "1.21.1"  # Update with the actual server version

# Hardcoded values
DISCORD_INVITE = "https://discord.gg/krdHGQsne4"
SERVER_MODERATORS = ["𝓡𝓸𝓬𝓴𝔂_𝓡𝓾𝓽𝔀𝓲𝓴", "kabashikun"]
SUPPORT_CHANNEL_LINK = "https://discord.com/channels/894902529039687720/960196810796847134"

# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Enable member intents for role commands
# bot = commands.Bot(command_prefix='i!', intents=intents, help_command=None)  # Custom help command
# def get_prefix(bot, message):
#     prefixes = ['i!', 'I!',]  # Define both prefixes
#     for prefix in prefixes:
#         if message.content.startswith(prefix):
#             return prefix  # Return the matching prefix
#     return commands.when_mentioned_or(*prefixes)(bot, message)  # Fallback to mention or valid prefixes
def get_prefix(bot, message):
    # List of valid prefixes
    prefixes = ['i!', 'I!']

    # Iterate over prefixes and check if the message starts with any of them
    for prefix in prefixes:
        if message.content.startswith(prefix):
            # Check if there's a space after the prefix
            if message.content[len(prefix):].startswith(' '):
                # Return the prefix plus space to support commands with a space
                return prefix + ' '
            # Return the prefix as is for regular commands
            return prefix

    # Fallback to mention prefix if no match is found
    return commands.when_mentioned_or(*prefixes)(bot, message)



bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None, case_insensitive=True)

tree = bot.tree  # For slash commands
@bot.event
async def on_ready():
    try:
        # Sync slash commands
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands globally.")
        for command in bot.tree.get_commands():
            print(f"Slash Command Synced: {command.name}")

        # Initialize and add Leveling cog
        if not bot.get_cog("Leveling"):
            leveling_cog = Leveling(bot)
            await bot.add_cog(leveling_cog)
            print("✅ Leveling cog loaded successfully.")
        else:
            leveling_cog = bot.get_cog("Leveling")  # Get existing cog reference

        # Initialize and add Economy cog with reference to Leveling cog
        if not bot.get_cog("Economy"):
            await bot.add_cog(Economy(bot, leveling_cog))  # Pass Leveling cog reference
            print("✅ Economy cog loaded successfully.")

        print("Bot is ready and all systems are operational!")

    except Exception as e:
        # Log the error details for debugging
        print(f"❌ Error during on_ready: {e}")
        with open("bot_errors.log", "a") as f:
            f.write(f"Error in on_ready: {e}\n")

# Global error handler for unexpected errors
@bot.event
async def on_error(event, *args, **kwargs):
    error_details = sys.exc_info()
    with open("bot_errors.log", "a") as f:
        f.write(f"Error in {event}: {error_details}\n")
    print(f"❌ Unexpected error in {event}: {error_details}")

# Initialize Minecraft server status
minecraft_server = JavaServer.lookup(f"{MINECRAFT_SERVER_IP}:{MINECRAFT_SERVER_PORT}")

# Load and save counting game data from/to JSON file
def load_game_data():
    if os.path.exists('counting_game_data.json'):
        with open('counting_game_data.json', 'r') as f:
            return json.load(f)
    return {}

def save_game_data(data):
    with open('counting_game_data.json', 'w') as f:
        json.dump(data, f, indent=4)

# Initialize the game data dictionary
game_data = load_game_data()

# Function to validate if the message is a valid number or expression
def is_valid_count(message, expected_number):
    try:
        if int(message.content) == expected_number:
            return True
    except ValueError:
        pass

    try:
        result = eval(message.content)
        if result == expected_number:
            return True
    except Exception:
        pass
    return False

# Track leave notification channel
leave_channels = {}

def save_leave_channels():
    with open('leave_channels.json', 'w') as f:
        json.dump(leave_channels, f, indent=4)

def load_leave_channels():
    global leave_channels
    if os.path.exists('leave_channels.json'):
        with open('leave_channels.json', 'r') as f:
            leave_channels = json.load(f)

load_leave_channels()

# Leave channel setup
@bot.command(name='leave')
@commands.has_permissions(administrator=True)
async def set_leave_channel(ctx, channel: discord.TextChannel):
    leave_channels[str(ctx.guild.id)] = channel.id
    save_leave_channels()
    await ctx.send(f"Leave notifications will be sent to {channel.mention}")

@tree.command(name="leave", description="Set the channel for leave notifications")
@app_commands.describe(channel="The channel for leave notifications")
async def slash_leave(interaction: discord.Interaction, channel: discord.TextChannel):
    leave_channels[str(interaction.guild.id)] = channel.id
    save_leave_channels()
    await interaction.response.send_message(f"Leave notifications will be sent to {channel.mention}")

# Send leave notification when a member leaves the server
@bot.event
async def on_member_remove(member):
    guild_id = str(member.guild.id)
    if guild_id in leave_channels:
        channel = bot.get_channel(int(leave_channels[guild_id]))
        if channel:
            embed = discord.Embed(
                title="Member Left",
                description=f"{member.mention} ({member.name}#{member.discriminator}) has left the server.",
                color=discord.Color.red()
            )
            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
            await channel.send(embed=embed)


@bot.event
async def on_message(message):
    global game_data

    if message.guild is None:
        await bot.process_commands(message)
        return

    guild_id = str(message.guild.id)

    if guild_id in game_data and message.channel.id == game_data[guild_id]['counting_channel_id']:
        if message.author != bot.user:
            current_number = game_data[guild_id]['current_number']
            last_user_id = game_data[guild_id]['last_user_id']

            reset_on_error = game_data[guild_id].get('reset_on_error', 'reset')

            if is_valid_count(message, current_number):
                if last_user_id == message.author.id:
                    embed = discord.Embed(
                        title="Error",
                        description=f"{message.author.mention}, you cannot send two numbers in a row!",
                        color=discord.Color.red()
                    )
                    await message.channel.send(embed=embed)
                else:
                    embed = discord.Embed(
                        title="Correct Count",
                        description=f"{message.author.mention} counted {current_number} correctly!",
                        color=discord.Color.green()
                    )
                    await message.channel.send(embed=embed)
                    game_data[guild_id]['current_number'] += 1
                    game_data[guild_id]['last_user_id'] = message.author.id
                    save_game_data(game_data)
            elif message.content.isdigit() or re.match(r'[\d\+\-\*/]+', message.content):
                embed = discord.Embed(
                    title="Wrong Number",
                    description=f"{message.author.mention}, wrong number or expression!",
                    color=discord.Color.red()
                )
                await message.channel.send(embed=embed)
                if reset_on_error == 'reset':
                    game_data[guild_id]['current_number'] = 1
                    await message.channel.send(embed=discord.Embed(
                        title="Counting Game",
                        description=f"Counting restarted! Start from 1.",
                        color=discord.Color.green()
                    ))
                game_data[guild_id]['last_user_id'] = None
                save_game_data(game_data)
    await bot.process_commands(message)

#Sync Bot Commands    
    @commands.command(name='sync', aliases=['resync'])
    @commands.is_owner()
    async def sync_commands(self, ctx):
        """Syncs slash commands"""
        try:
            synced = await self.bot.tree.sync(force=True)
            await ctx.send(f"✅ Synced {len(synced)} commands.")
        except Exception as e:
            await ctx.send(f"❌ Failed to sync commands: {e}")
    
# Counting game setup
@bot.command(name='setchannel', aliases=['setch'])
@commands.has_permissions(administrator=True)
async def setchannel(ctx, channel: discord.TextChannel, reset_option: str):
    global game_data
    guild_id = str(ctx.guild.id)

    if reset_option not in ['reset', 'dontreset']:
        await ctx.send("Invalid option! Use 'reset' to reset on a wrong number, or 'dontreset' to continue counting.")
        return

    game_data[guild_id] = {
        'counting_channel_id': channel.id,
        'current_number': 1,
        'last_user_id': None,
        'reset_on_error': reset_option
    }
    save_game_data(game_data)

    embed = discord.Embed(
        title="Counting Game",
        description=f"Counting game started in {channel.mention} with reset option {reset_option}! Start counting from 1.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@tree.command(name="setchannel", description="Set the counting game channel with reset option")
@app_commands.describe(channel="The channel to set", reset_option="Choose between reset or dontreset")
@app_commands.choices(reset_option=[
    app_commands.Choice(name="Reset on error", value="reset"),
    app_commands.Choice(name="Don't reset", value="dontreset")
])
async def slash_setchannel(interaction: discord.Interaction, channel: discord.TextChannel, reset_option: str):
    guild_id = str(interaction.guild.id)

    game_data[guild_id] = {
        'counting_channel_id': channel.id,
        'current_number': 1,
        'last_user_id': None,
        'reset_on_error': reset_option
    }
    save_game_data(game_data)

    embed = discord.Embed(
        title="Counting Game",
        description=f"Counting game started in {channel.mention} with reset option {reset_option}! Start counting from 1.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

# Server info
@bot.command(name='serverinfo')
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"{guild.name} Server Information", color=discord.Color.blue())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.add_field(name="ID", value=guild.id, inline=True)
    embed.add_field(name="Owner", value=guild.owner, inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="Created At", value=guild.created_at.strftime('%Y-%m-%d %I:%M %p'), inline=True)

    await ctx.send(embed=embed)

@tree.command(name="serverinfo", description="Displays server information")
async def slash_serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"{guild.name} Server Information", color=discord.Color.blue())

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.add_field(name="ID", value=guild.id, inline=True)
    embed.add_field(name="Owner", value=guild.owner, inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="Created At", value=guild.created_at.strftime('%Y-%m-%d %I:%M %p'), inline=True)

    await interaction.response.send_message(embed=embed)


# User avatar and Info's
@bot.command(name='avatar', aliases=['av'])
async def avatar(ctx, member: discord.Member = None):
    """Displays the avatar of the user or a specified member."""
    user = member or ctx.author  # Default to the command author if no member is specified

    embed = discord.Embed(
        title=f"{user.name}'s Avatar",
        color=discord.Color.blue()
    )
    embed.set_image(url=user.avatar.url)
    embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)

    await ctx.send(embed=embed)

@tree.command(name="avatar", description="Displays a user's avatar")
@app_commands.describe(member="The member whose avatar you want to view")
async def slash_avatar(interaction: discord.Interaction, member: discord.Member = None):
    """Displays the avatar of the user or a specified member via slash command."""
    user = member or interaction.user  # Default to the command invoker if no member is specified

    embed = discord.Embed(
        title=f"{user.name}'s Avatar",
        color=discord.Color.blue()
    )
    embed.set_image(url=user.avatar.url)
    embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.avatar.url)

    await interaction.response.send_message(embed=embed)



@bot.command(name='userinfo', aliases=['uinfo'])
async def userinfo(ctx, member: discord.Member = None):
    """Fetches and displays user info."""
    user = member or ctx.author
    embed = discord.Embed(
        title=f"User Information - {user.name}",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=user.avatar.url)
    embed.add_field(name="Username", value=f"{user.name}#{user.discriminator}", inline=True)
    embed.add_field(name="User ID", value=user.id, inline=True)
    embed.add_field(name="Joined Server", value=user.joined_at.strftime('%Y-%m-%d %H:%M:%S'), inline=False)
    embed.add_field(name="Account Created", value=user.created_at.strftime('%Y-%m-%d %H:%M:%S'), inline=False)
    embed.add_field(name="Top Role", value=user.top_role.mention if user.top_role else "None", inline=True)
    await ctx.send(embed=embed)
    
@tree.command(name="userinfo", description="Fetch user information")
@app_commands.describe(member="The member whose info you want to view")
async def slash_userinfo(interaction: discord.Interaction, member: discord.Member = None):
    user = member or interaction.user
    embed = discord.Embed(
        title=f"User Information - {user.name}",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=user.avatar.url)
    embed.add_field(name="Username", value=f"{user.name}#{user.discriminator}", inline=True)
    embed.add_field(name="User ID", value=user.id, inline=True)
    embed.add_field(name="Joined Server", value=user.joined_at.strftime('%Y-%m-%d %H:%M:%S'), inline=False)
    embed.add_field(name="Account Created", value=user.created_at.strftime('%Y-%m-%d %H:%M:%S'), inline=False)
    embed.add_field(name="Top Role", value=user.top_role.mention if user.top_role else "None", inline=True)
    await interaction.response.send_message(embed=embed)



# Role info
@bot.command(name='roleinfo')
async def roleinfo(ctx, role: discord.Role):
    permissions = ', '.join([perm[0].replace('_', ' ').title() for perm in role.permissions if perm[1]])
    embed = discord.Embed(title=f"Role Information - {role.name}", color=role.color)
    embed.add_field(name="ID", value=role.id, inline=True)
    embed.add_field(name="Permissions", value=f"`{permissions or 'None'}`", inline=False)
    embed.add_field(name="Created At", value=role.created_at.strftime('%Y-%m-%d %I:%M %p'), inline=True)
    await ctx.send(embed=embed)

@tree.command(name="roleinfo", description="Displays role information")
@app_commands.describe(role="The role to display information about")
async def slash_roleinfo(interaction: discord.Interaction, role: discord.Role):
    permissions = ', '.join([perm[0].replace('_', ' ').title() for perm in role.permissions if perm[1]])
    embed = discord.Embed(title=f"Role Information - {role.name}", color=role.color)
    embed.add_field(name="ID", value=role.id, inline=True)
    embed.add_field(name="Permissions", value=f"`{permissions or 'None'}`", inline=False)
    embed.add_field(name="Created At", value=role.created_at.strftime('%Y-%m-%d %I:%M %p'), inline=True)
    await interaction.response.send_message(embed=embed)

# Add and remove role
@bot.command(name='addrole')
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, member_type: str, role: discord.Role, member: discord.Member = None):
    """
    Add a role to all humans, bots, or a specific member.
    Usage:
    i!addrole human <role> - Adds the role to all human members.
    i!addrole bots <role> - Adds the role to all bot members.
    i!addrole member <role> <@member> - Adds the role to a specific member.
    """
    if member_type.lower() == 'human':
        # Adding role to all humans
        humans = [m for m in ctx.guild.members if not m.bot]
        for human in humans:
            if ctx.author.top_role <= role:
                await ctx.send(embed=discord.Embed(
                    title="Error",
                    description=f"Cannot add role `{role.name}` because your role is lower or equal to the target role.",
                    color=discord.Color.red()))
                return
            await human.add_roles(role, reason=f"Role added by {ctx.author}")
        await ctx.send(embed=discord.Embed(
            title="Add Role",
            description=f"Added role `{role.name}` to all human members.",
            color=discord.Color.green()))

    elif member_type.lower() == 'bots':
        # Adding role to all bots
        bots = [m for m in ctx.guild.members if m.bot]
        for bot in bots:
            if ctx.author.top_role <= role:
                await ctx.send(embed=discord.Embed(
                    title="Error",
                    description=f"Cannot add role `{role.name}` because your role is lower or equal to the target role.",
                    color=discord.Color.red()))
                return
            await bot.add_roles(role, reason=f"Role added by {ctx.author}")
        await ctx.send(embed=discord.Embed(
            title="Add Role",
            description=f"Added role `{role.name}` to all bots.",
            color=discord.Color.green()))

    elif member_type.lower() == 'member' and member:
        # Adding role to a specific member
        if ctx.author.top_role <= role:
            await ctx.send(embed=discord.Embed(
                title="Error",
                description=f"Cannot add role `{role.name}` because your role is lower or equal to the target role.",
                color=discord.Color.red()))
            return
        await member.add_roles(role, reason=f"Role added by {ctx.author}")
        await ctx.send(embed=discord.Embed(
            title="Add Role",
            description=f"Added role `{role.name}` to {member.mention}.",
            color=discord.Color.green()))
    else:
        await ctx.send("❌ Invalid usage! Use:\n`i!addrole human <role>`\n`i!addrole bots <role>`\n`i!addrole member <role> <@member>`.")


@tree.command(name="addrole", description="Add a role to humans, bots, or a specific member.")
@app_commands.describe(
    member_type="Who should receive the role: humans, bots, or a specific member",
    role="The role to assign",
    member="The specific member to assign the role to (if member type is 'member')"
)
@app_commands.choices(
    member_type=[
        app_commands.Choice(name="Humans", value="human"),
        app_commands.Choice(name="Bots", value="bots"),
        app_commands.Choice(name="Member", value="member")
    ]
)
async def slash_addrole(
    interaction: discord.Interaction,
    member_type: app_commands.Choice[str],
    role: discord.Role,
    member: discord.Member = None
):
    """
    Slash command to add a role to humans, bots, or a specific member.
    """
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message(
            "❌ You don't have permission to manage roles.", ephemeral=True
        )
        return

    if interaction.user.top_role <= role:
        await interaction.response.send_message(
            f"❌ You cannot manage the `{role.name}` role because it's higher or equal to your top role.",
            ephemeral=True,
        )
        return

    # Add the role to all humans
    if member_type.value == "human":
        humans = [m for m in interaction.guild.members if not m.bot]
        for human in humans:
            if interaction.guild.me.top_role <= role:
                await interaction.response.send_message(
                    f"❌ I cannot manage the `{role.name}` role because it is higher than my top role.",
                    ephemeral=True,
                )
                return
            await human.add_roles(role, reason=f"Role added by {interaction.user}")
        await interaction.response.send_message(
            f"✅ Assigned the `{role.name}` role to all human members.", ephemeral=True
        )

    # Add the role to all bots
    elif member_type.value == "bots":
        bots = [m for m in interaction.guild.members if m.bot]
        for bot in bots:
            if interaction.guild.me.top_role <= role:
                await interaction.response.send_message(
                    f"❌ I cannot manage the `{role.name}` role because it is higher than my top role.",
                    ephemeral=True,
                )
                return
            await bot.add_roles(role, reason=f"Role added by {interaction.user}")
        await interaction.response.send_message(
            f"✅ Assigned the `{role.name}` role to all bot members.", ephemeral=True
        )

    # Add the role to a specific member
    elif member_type.value == "member":
        if not member:
            await interaction.response.send_message(
                "❌ Please specify a member when selecting 'member' as the target.",
                ephemeral=True,
            )
            return
        if interaction.guild.me.top_role <= role:
            await interaction.response.send_message(
                f"❌ I cannot manage the `{role.name}` role because it is higher than my top role.",
                ephemeral=True,
            )
            return
        await member.add_roles(role, reason=f"Role added by {interaction.user}")
        await interaction.response.send_message(
            f"✅ Assigned the `{role.name}` role to {member.mention}.", ephemeral=True
        )


@bot.command(name='removerole')
@commands.has_permissions(manage_roles=True)
async def removerole(ctx, member_type: str, role: discord.Role, member: discord.Member = None):
    """
    Remove a role from all humans, bots, or a specific member.
    Usage:
    i!removerole human <role> - Removes the role from all human members.
    i!removerole bots <role> - Removes the role from all bot members.
    i!removerole member <role> <@member> - Removes the role from a specific member.
    """
    if member_type.lower() == 'human':
        # Removing role from all humans
        humans = [m for m in ctx.guild.members if not m.bot and role in m.roles]
        for human in humans:
            await human.remove_roles(role, reason=f"Role removed by {ctx.author}")
        await ctx.send(embed=discord.Embed(
            title="Remove Role",
            description=f"Removed role `{role.name}` from all human members.",
            color=discord.Color.red()))

    elif member_type.lower() == 'bots':
        # Removing role from all bots
        bots = [m for m in ctx.guild.members if m.bot and role in m.roles]
        for bot in bots:
            await bot.remove_roles(role, reason=f"Role removed by {ctx.author}")
        await ctx.send(embed=discord.Embed(
            title="Remove Role",
            description=f"Removed role `{role.name}` from all bot members.",
            color=discord.Color.red()))

    elif member_type.lower() == 'member' and member:
        # Removing role from a specific member
        if role not in member.roles:
            await ctx.send(embed=discord.Embed(
                title="Error",
                description=f"{member.mention} does not have the `{role.name}` role.",
                color=discord.Color.red()))
            return
        await member.remove_roles(role, reason=f"Role removed by {ctx.author}")
        await ctx.send(embed=discord.Embed(
            title="Remove Role",
            description=f"Removed role `{role.name}` from {member.mention}.",
            color=discord.Color.red()))
    else:
        await ctx.send("❌ Invalid usage! Use:\n`i!removerole human <role>`\n`i!removerole bots <role>`\n`i!removerole member <role> <@member>`.")

@tree.command(name="removerole", description="Remove a role from humans, bots, or a specific member.")
@app_commands.describe(
    member_type="Who should lose the role: humans, bots, or a specific member",
    role="The role to remove",
    member="The specific member to remove the role from (if member type is 'member')"
)
@app_commands.choices(
    member_type=[
        app_commands.Choice(name="Humans", value="human"),
        app_commands.Choice(name="Bots", value="bots"),
        app_commands.Choice(name="Member", value="member")
    ]
)
async def slash_removerole(
    interaction: discord.Interaction,
    member_type: app_commands.Choice[str],
    role: discord.Role,
    member: discord.Member = None
):
    """
    Slash command to remove a role from humans, bots, or a specific member.
    """
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message(
            "❌ You don't have permission to manage roles.", ephemeral=True
        )
        return

    if interaction.user.top_role <= role:
        await interaction.response.send_message(
            f"❌ You cannot manage the `{role.name}` role because it's higher or equal to your top role.",
            ephemeral=True,
        )
        return

    # Remove the role from all humans
    if member_type.value == "human":
        humans = [m for m in interaction.guild.members if not m.bot and role in m.roles]
        for human in humans:
            await human.remove_roles(role, reason=f"Role removed by {interaction.user}")
        await interaction.response.send_message(
            f"✅ Removed the `{role.name}` role from all human members.", ephemeral=True
        )

    # Remove the role from all bots
    elif member_type.value == "bots":
        bots = [m for m in interaction.guild.members if m.bot and role in m.roles]
        for bot in bots:
            await bot.remove_roles(role, reason=f"Role removed by {interaction.user}")
        await interaction.response.send_message(
            f"✅ Removed the `{role.name}` role from all bot members.", ephemeral=True
        )

    # Remove the role from a specific member
    elif member_type.value == "member":
        if not member:
            await interaction.response.send_message(
                "❌ Please specify a member when selecting 'member' as the target.",
                ephemeral=True,
            )
            return
        if role not in member.roles:
            await interaction.response.send_message(
                f"❌ {member.mention} does not have the `{role.name}` role.", ephemeral=True
            )
            return
        await member.remove_roles(role, reason=f"Role removed by {interaction.user}")
        await interaction.response.send_message(
            f"✅ Removed the `{role.name}` role from {member.mention}.", ephemeral=True
        )


# IP, Ping, Status, Players, Support Commands

# Ip Command (r!ip and /ip)
@bot.command(name='ip')
async def ip(ctx):
    embed = discord.Embed(
        title="Server IP Address",
        description="Here are the connection details for the Minecraft server:",
        color=discord.Color.blue()
    )
    embed.add_field(name="Java Edition", value="mc.rutwikdev.com", inline=False)
    embed.add_field(name="Bedrock Edition", value="mc.rutwikdev.com:6007", inline=False)
    embed.set_footer(text="If unable to connect with mc.rutwikdev.com from Java, try using port 6007.")
    
    await ctx.send(embed=embed)

@bot.tree.command(name="ip", description="Shows the Minecraft server IP address")
async def slash_ip(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Server IP Address",
        description="Here are the connection details for the Minecraft server:",
        color=discord.Color.blue()
    )
    embed.add_field(name="Java Edition", value="mc.rutwikdev.com", inline=False)
    embed.add_field(name="Bedrock Edition", value="mc.rutwikdev.com:6007", inline=False)
    embed.set_footer(text="If unable to connect with mc.rutwikdev.com from Java, try using port 6007.")
    
    await interaction.response.send_message(embed=embed)


# Ping Command (r!ping and /ping)
@bot.command(name='ping', aliases=['p'])
async def ping(ctx):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="Bot Latency",
        description=f"Pong! Latency is {latency} ms.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@tree.command(name="ping", description="Shows the bot's latency")
async def slash_ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="Bot Latency",
        description=f"Pong! Latency is {latency} ms.",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed)
    
    
# Status Command (r!status and /status)
@bot.command(name='status', aliases=['st'])
async def status(ctx):
    try:
        status = minecraft_server.status()
        embed = discord.Embed(
            title="Server Status",
            description="The server is currently **Online**.",
            color=discord.Color.green()
        )
        embed.add_field(name="Players Online", value=f"{status.players.online}/{status.players.max}")
    except Exception as e:
        embed = discord.Embed(
            title="Server Status",
            description="The server is currently **Offline**.",
            color=discord.Color.red()
        )
        print(f"Error fetching server status: {e}")
    
    await ctx.send(embed=embed)

@tree.command(name="status", description="Shows whether the server is online or offline")
async def slash_status(interaction: discord.Interaction):
    try:
        status = minecraft_server.status()
        embed = discord.Embed(
            title="Server Status",
            description="The server is currently **Online**.",
            color=discord.Color.green()
        )
        embed.add_field(name="Players Online", value=f"{status.players.online}/{status.players.max}")
    except Exception as e:
        embed = discord.Embed(
            title="Server Status",
            description="The server is currently **Offline**.",
            color=discord.Color.red()
        )
        print(f"Error fetching server status: {e}")
    
    await interaction.response.send_message(embed=embed)


# Players Command (r!players and /players)
@bot.command(name='players', aliases=['pl'])
async def players(ctx):
    try:
        status = await asyncio.get_event_loop().run_in_executor(None, minecraft_server.status)
        player_list = ', '.join(player.name for player in status.players.sample) if status.players.sample else 'No players online'
        embed = discord.Embed(
            title="Players Online",
            description=f"Players currently online: {player_list}",
            color=discord.Color.blue()
        )
    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description="Unable to retrieve player list.",
            color=discord.Color.red()
        )
        print(f"Error fetching player list: {e}")
    await ctx.send(embed=embed)

@tree.command(name="players", description="Shows the players currently online on the Minecraft server")
async def slash_players(interaction: discord.Interaction):
    try:
        status = await asyncio.get_event_loop().run_in_executor(None, minecraft_server.status)
        player_list = ', '.join(player.name for player in status.players.sample) if status.players.sample else 'No players online'
        embed = discord.Embed(
            title="Players Online",
            description=f"Players currently online: {player_list}",
            color=discord.Color.blue()
        )
    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description="Unable to retrieve player list.",
            color=discord.Color.red()
        )
        print(f"Error fetching player list: {e}")
    
    await interaction.response.send_message(embed=embed)


# Support Command (r!support and /support)
@bot.command(name='support')
async def support(ctx):
    """Sends support message."""
    embed = discord.Embed(
        title="Server Support",
        description=f"If you need support for the server, please contact the server admins or visit our [Support Channel]({SUPPORT_CHANNEL_LINK}).",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@tree.command(name="support", description="Provides server support information")
async def slash_support(interaction: discord.Interaction):
    """Slash command version for support."""
    embed = discord.Embed(
        title="Server Support",
        description=f"If you need support for the server, please contact the server admins or visit our [Support Channel]({SUPPORT_CHANNEL_LINK}).",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed)

# Poll Command

@bot.command(name='poll')
async def poll(ctx, question: str, *options):
    """Creates a poll."""
    if len(options) < 2:
        await ctx.send("You must provide at least 2 options.")
        return
    if len(options) > 10:
        await ctx.send("You cannot provide more than 10 options.")
        return
    
    embed = discord.Embed(title="📊 Poll", description=question, color=discord.Color.green())
    for i, option in enumerate(options, 1):
        embed.add_field(name=f"Option {i}", value=option, inline=False)
    
    msg = await ctx.send(embed=embed)
    reactions = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
    for i in range(len(options)):
        await msg.add_reaction(reactions[i])
@tree.command(name="poll", description="Create a poll with multiple options")
@app_commands.describe(question="The poll question", options="Provide comma-separated options (e.g., Yes,No,Maybe)")
async def slash_poll(interaction: discord.Interaction, question: str, options: str):
    options_list = options.split(',')
    if len(options_list) < 2:
        await interaction.response.send_message("You must provide at least 2 options.")
        return
    if len(options_list) > 10:
        await interaction.response.send_message("You cannot provide more than 10 options.")
        return
    
    embed = discord.Embed(title="📊 Poll", description=question, color=discord.Color.green())
    for i, option in enumerate(options_list, 1):
        embed.add_field(name=f"Option {i}", value=option.strip(), inline=False)
    
    msg = await interaction.response.send_message(embed=embed, ephemeral=False)
    reactions = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
    for i in range(len(options_list)):
        await msg.add_reaction(reactions[i])


# Suggest Command

# File to store suggestion channels
SUGGESTION_CHANNELS_FILE = 'suggestion_channels.json'

# Load suggestion channels from file
def load_suggestion_channels():
    if os.path.exists(SUGGESTION_CHANNELS_FILE):
        with open(SUGGESTION_CHANNELS_FILE, 'r') as f:
            return json.load(f)
    return {}

# Save suggestion channels to file
def save_suggestion_channels(data):
    with open(SUGGESTION_CHANNELS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Load the existing suggestion channels at startup
suggestion_channels = load_suggestion_channels()

# Set suggestion channel command
@bot.command(name="setsuggestionchannel", aliases=["setsugchannel"])
@commands.has_permissions(administrator=True)
async def set_suggestion_channel(ctx, channel: discord.TextChannel):
    guild_id = str(ctx.guild.id)  # Unique identifier for the server
    suggestion_channels[guild_id] = channel.id  # Store the channel ID for the server
    save_suggestion_channels(suggestion_channels)  # Save to file
    await ctx.send(f"✅ Suggestions will now be sent to {channel.mention}")

# Suggest command
@bot.command(name="suggest")
async def suggest(ctx, *, suggestion: str):
    guild_id = str(ctx.guild.id)
    if guild_id not in suggestion_channels:
        await ctx.send("❌ No suggestion channel is set. Please ask an admin to set it using `i!setsuggestionchannel`.")
        return

    channel_id = suggestion_channels[guild_id]
    channel = bot.get_channel(channel_id)
    if not channel:
        await ctx.send("❌ The suggestion channel is invalid or no longer exists. Please ask an admin to reset it.")
        return

    embed = discord.Embed(
        title="📝 New Suggestion",
        description=suggestion,
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Suggested by {ctx.author}", icon_url=ctx.author.avatar.url)
    suggestion_message = await channel.send(embed=embed)
    await suggestion_message.add_reaction("✅")
    await suggestion_message.add_reaction("❌")
    await ctx.send(f"✅ Your suggestion has been sent to {channel.mention}")

# Slash command version of suggest
@tree.command(name="suggest", description="Submit a suggestion")
@app_commands.describe(suggestion="Your suggestion text")
async def slash_suggest(interaction: discord.Interaction, suggestion: str):
    guild_id = str(interaction.guild.id)
    if guild_id not in suggestion_channels:
        await interaction.response.send_message(
            "❌ No suggestion channel is set. Please ask an admin to set it using `/setsuggestionchannel`.",
            ephemeral=True
        )
        return

    channel_id = suggestion_channels[guild_id]
    channel = bot.get_channel(channel_id)
    if not channel:
        await interaction.response.send_message(
            "❌ The suggestion channel is invalid or no longer exists. Please ask an admin to reset it.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="📝 New Suggestion",
        description=suggestion,
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Suggested by {interaction.user}", icon_url=interaction.user.avatar.url)
    suggestion_message = await channel.send(embed=embed)
    await suggestion_message.add_reaction("✅")
    await suggestion_message.add_reaction("❌")
    await interaction.response.send_message("✅ Your suggestion has been submitted!", ephemeral=True)
    
    
# Updated Help Command with Bot Icon
@bot.command(name='help', aliases=['h'])
async def help_command(ctx):
    embeds = {
        "server": discord.Embed(
            title=":gear: **Minecraft /Server Commands**",
            description=(
                "`i!ip` - 📡 Get the Minecraft server IP address.\n"
                "`i!ping` - 🏓 Check the bot's latency.\n"
                "`i!status` - 🔌 Check if the Minecraft server is online.\n"
                "`i!players` - 👥 View the players currently online.\n"
                "`i!support` - 📞 Get support contact information."
            ),
            color=discord.Color.blue()
        ).set_thumbnail(
            url="https://cdn.discordapp.com/avatars/845661604699701278/4899feb202f9ee24cebb085f0dde7802.png"
        ),
        "Fun Games": discord.Embed(
            title=":video_game: **Fun Game Commands**",
            description=(
                "`i!setchannel [#channel] reset/dontreset` - 🎮 Configure the counting game channel.\n"
                
                "`i!poll <question> <options>` - 🗳️ Create a poll."
            ),
            color=discord.Color.green()
        ).set_thumbnail(
            url="https://cdn.discordapp.com/avatars/845661604699701278/4899feb202f9ee24cebb085f0dde7802.png"
        ),
        "economy": discord.Embed(
            title=":moneybag: **Economy Commands**",
            description=(
                "`i!daily` - 🎁 Claim your daily rewards.\n"
                "`i!work` - 🛠️ Work to earn money.\n"
                "`i!balance` - 💳 Check your balance.\n"
                "`i!deposit <amount/all>` - 🏦 Deposit money to your bank.\n"
                "`i!withdraw <amount/all>` - 💸 Withdraw money from your bank.\n"
                "`i!give <user> <amount>` - 🤝 Transfer money to another user.\n"
                "`i!rob <user>` - 🦹 Attempt to rob someone (risky!).\n"
                "`i!russianroulette <amount>` - 🎲 Gamble money in Russian Roulette.\n"
                "`i!crime` - 🕵️‍♂️ Attempt to commit a crime for money (risky!).\n"
                "`i!coinflip <heads/tails> <amount/all/half>` - 🎲 Flip a coin and bet your money on the outcome. Win or lose based on luck!"
                "`i!search` - 🔍 Use your metal detector to find items.\n"
                "`i!mine` - ⛏️ Use your pickaxe to mine valuable items.\n"
                "`i!coinflip `heads/tails` `amount`- Bet"
                "`i!adventure` - 🗺️ Embark on a thrilling adventure! You might earn a fortune, find valuable items, or face dangerous losses."
                "`i!inventory` - 🎒 Check your inventory.\n"
                "`i!buytool` - 🛒 Purchase a metal detector.\n"
                "`i!buypickaxe` - 🛒 Purchase a pickaxe.\n"
                "`i!sell <item> <amount>` - 💵 Sell items from your inventory.\n"
                "`i!trade <user> <item> <amount>` - 🤝 Trade items with another user.\n"
                "`i!leaderboard` - 🏆 View the richest users."
            ),
            color=discord.Color.gold()
        ).set_thumbnail(
            url="https://cdn.discordapp.com/avatars/845661604699701278/4899feb202f9ee24cebb085f0dde7802.png"
        ),
        "admin": discord.Embed(
            title=":wrench: **Admin Commands**",
            description=(
                "`i!setdaily <amount>` - 🔧 Configure the daily reward amount.\n"
                "`i!setrobchance <chance>` - 🎯 Set the robbery success probability.\n"
                "`i!sync` - 🔄 Sync slash commands.\n"
                "`i!addrole <human/bots/member> <role>` - ➕ Add a role to specified users.\n"
                "`i!removerole <@member> <@role>` - ➖ Remove a role from a user.\n"
                "`i!serverinfo` - 📋 View detailed server information.\n"
                "`i!roleinfo <@role>` - ℹ️ Get detailed information about a role.\n"
                "`i!leave [#channel]` - 🚪 Set the leave notification channel.\n"
                "`i!setsuggestionchannel [#channel]` - 📝 Set the suggestion channel."
            ),
            color=discord.Color.orange()
        ).set_thumbnail(
            url="https://cdn.discordapp.com/avatars/845661604699701278/4899feb202f9ee24cebb085f0dde7802.png"
        ),
        "other": discord.Embed(
            title=":information_source: **Other Commands**",
            description=(
                "`i!avatar` - 🖼️ View your or another user's avatar.\n"
                "`i!userinfo` - 📜 View user information.\n"
                "`i!profile` - 📝 View your Economy Profile.\n"
                "`i!suggest <suggestion>` - 📝 Submit a suggestion.\n"
                "`i!help` - ❓ Display this help menu."
            ),
            color=discord.Color.purple()
        ).set_thumbnail(
            url="https://cdn.discordapp.com/avatars/845661604699701278/4899feb202f9ee24cebb085f0dde7802.png"
        )
    }

    await ctx.send(embed=embeds["server"], view=HelpView(embeds))


class HelpView(View):
    def __init__(self, embeds):
        super().__init__()
        self.embeds = embeds

    async def update_embed(self, interaction: discord.Interaction, category: str):
        embed = self.embeds[category]
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Server", style=discord.ButtonStyle.primary)
    async def server_button(self, interaction: discord.Interaction, button: Button):
        await self.update_embed(interaction, "server")

    @discord.ui.button(label="Fun", style=discord.ButtonStyle.success)
    async def fun_button(self, interaction: discord.Interaction, button: Button):
        await self.update_embed(interaction, "Fun Games")

    @discord.ui.button(label="Economy", style=discord.ButtonStyle.secondary)
    async def economy_button(self, interaction: discord.Interaction, button: Button):
        await self.update_embed(interaction, "economy")

    @discord.ui.button(label="Admin", style=discord.ButtonStyle.danger)
    async def admin_button(self, interaction: discord.Interaction, button: Button):
        await self.update_embed(interaction, "admin")

    @discord.ui.button(label="Other", style=discord.ButtonStyle.grey)
    async def other_button(self, interaction: discord.Interaction, button: Button):
        await self.update_embed(interaction, "other")

# Slash Commands Help Section
@tree.command(name="help", description="Show help menu for bot commands")
async def slash_help(interaction: discord.Interaction):
    embeds = {
        "server": discord.Embed(
            title=":gear: **Server Commands**",
            description=(
                "`/ip` - 📡 Get the Minecraft server IP address.\n"
                "`/ping` - 🏓 Check the bot's latency.\n"
                "`/status` - 🔌 Check if the Minecraft server is online.\n"
                "`/players` - 👥 View the players currently online.\n"
                "`/support` - 📞 Get support contact information."
            ),
            color=discord.Color.blue()
        ).set_thumbnail(
            url="https://cdn.discordapp.com/avatars/845661604699701278/4899feb202f9ee24cebb085f0dde7802.png"
        ),
        "Fun Games": discord.Embed(
            title=":video_game: **Fun Game Commands**",
            description=(
                "`/setchannel [#channel] reset/dontreset` - 🎮 Configure the counting game channel.\n"
                "`/russianroulette <amount>` - 🎲 Gamble money in Russian Roulette.\n"
                "`/crime` - 🕵️‍♂️ Attempt to commit a crime for money (risky!).\n"
                "`/poll <question> <options>` - 🗳️ Create a poll."
            ),
            color=discord.Color.green()
        ).set_thumbnail(
            url="https://cdn.discordapp.com/avatars/845661604699701278/4899feb202f9ee24cebb085f0dde7802.png"
        ),
        "economy": discord.Embed(
            title=":moneybag: **Economy Commands**",
            description=(
                "`/daily` - 🎁 Claim your daily rewards.\n"
                "`/work` - 🛠️ Work to earn money.\n"
                "`/balance` - 💳 Check your balance.\n"
                "`/deposit <amount/all>` - 🏦 Deposit money to your bank.\n"
                "`/withdraw <amount/all>` - 💸 Withdraw money from your bank.\n"
                "`/give <user> <amount>` - 🤝 Transfer money to another user.\n"
                "`/rob <user>` - 🦹 Attempt to rob someone (risky!).\n"
                "`/search` - 🔍 Use your metal detector to find items.\n"
                "`/mine` - ⛏️ Use your pickaxe to mine valuable items.\n"
                "`i!coinflip <heads/tails> <amount/all/half>` - 🎲 Flip a coin and bet your money on the outcome. Win or lose based on luck!"
                "`/adventure` - 🗺️ Embark on a thrilling adventure to earn rewards or face losses."
                "`/inventory` - 🎒 Check your inventory.\n"
                "`/buytool` - 🛒 Purchase a metal detector.\n"
                "`/buypickaxe` - 🛒 Purchase a pickaxe.\n"
                "`/sell <item> <amount>` - 💵 Sell items from your inventory.\n"
                "`/trade <user> <item> <amount>` - 🤝 Trade items with another user.\n"
                "`/leaderboard` - 🏆 View the richest users."
            ),
            color=discord.Color.gold()
        ).set_thumbnail(
            url="https://cdn.discordapp.com/avatars/845661604699701278/4899feb202f9ee24cebb085f0dde7802.png"
        ),
        "admin": discord.Embed(
            title=":wrench: **Admin Commands**",
            description=(
                "`/setdaily <amount>` - 🔧 Configure the daily reward amount.\n"
                "`/setrobchance <chance>` - 🎯 Set the robbery success probability.\n"
                "`/sync` - 🔄 Sync slash commands.\n"
                "`/addrole <human/bots/member> <role>` - ➕ Add a role to specified users.\n"
                "`/removerole <@member> <@role>` - ➖ Remove a role from a user.\n"
                "`/serverinfo` - 📋 View detailed server information.\n"
                "`/roleinfo <@role>` - ℹ️ Get detailed information about a role.\n"
                "`/leave [#channel]` - 🚪 Set the leave notification channel.\n"
                "`/setsuggestionchannel [#channel]` - 📝 Set the suggestion channel."
            ),
            color=discord.Color.orange()
        ).set_thumbnail(
            url="https://cdn.discordapp.com/avatars/845661604699701278/4899feb202f9ee24cebb085f0dde7802.png"
        ),
        "other": discord.Embed(
            title=":information_source: **Other Commands**",
            description=(
                "`/avatar` - 🖼️ View your or another user's avatar.\n"
                "`/userinfo` - 📜 View user information.\n"
                "`/profile` - 📝 View your Economy Profile.\n"
                "`/suggest <suggestion>` - 📝 Submit a suggestion.\n"
                "`/help` - ❓ Display this help menu."
            ),
            color=discord.Color.purple()
        ).set_thumbnail(
            url="https://cdn.discordapp.com/avatars/845661604699701278/4899feb202f9ee24cebb085f0dde7802.png"
        )
    }

    await interaction.response.send_message(embed=embeds["server"], view=HelpView(embeds))

# Run the setup function
# asyncio.run(setup()) 
# Run the bot
bot.run(DISCORD_TOKEN)