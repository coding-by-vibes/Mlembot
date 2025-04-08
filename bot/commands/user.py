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

    @app_commands.command(name="wipeconvo", description="Clear your saved conversation history with the bot")
    async def wipeconvo(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        user_id = str(interaction.user.id)

        try:
            self.conversation_manager.reset_conversation(user_id)
            await interaction.followup.send("🧹 Your conversation history has been cleared!", ephemeral=True)
        except Exception as e:
            self.logger.error(f"Error in /wipeconvo: {e}")
            await interaction.followup.send(f"❌ Failed to clear your conversation: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(User(bot))