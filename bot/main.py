import sys
import os
import discord
from discord.ext import commands
import asyncio
import logging

# Add project root to sys.path so imports like `from utils...` work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.config import DISCORD_BOT_TOKEN

intents = discord.Intents.default()
intents.message_content = True  # If needed for message-based commands

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} app command(s).")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

async def load_extensions():
    extensions = [
        "bot.commands.chat",
        "bot.commands.summarize",
        "bot.commands.user"
        # "bot.commands.recipe"
        # Add more cogs here if needed
    ]
    for ext in extensions:
        try:
            await bot.load_extension(ext)
            print(f"✅ Loaded extension: {ext}")
        except Exception as e:
            print(f"❌ Failed to load {ext}: {e}")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(DISCORD_BOT_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Bot shutdown by user.")