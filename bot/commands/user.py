import discord
from discord.ext import commands
from discord import app_commands
import logging
from utils.conversation import ConversationManager
from pathlib import Path

class User(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.settings_dir = Path("storage")
        self.conversation_manager = ConversationManager(settings_dir=str(self.settings_dir))
        self.logger.info("User cog initialized")

    @app_commands.command(name="wipeconvo", description="Clear your chat history with the bot in this channel.")
    async def wipeconvo(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        user_id = str(interaction.user.id)
        channel_id = str(interaction.channel_id)  # <- ✅ This is what you were missing

        try:
            await self.conversation_manager.reset_conversation(user_id, channel_id)
            await interaction.followup.send("🧹 Your conversation history has been cleared.")
        except Exception as e:
            self.logger.error(f"Error in /wipeconvo command: {e}", exc_info=True)
            await interaction.followup.send("❌ Failed to clear your conversation.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(User(bot))