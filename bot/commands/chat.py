from discord.ext import commands
from discord import app_commands, Interaction
import logging
from utils.conversation import ConversationManager
from utils.user_manager import UserManager
from pathlib import Path

class Chat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.settings_dir = Path("storage")
        self.user_manager = UserManager(settings_dir=self.settings_dir)
        self.conversation_manager = ConversationManager(settings_dir=str(self.settings_dir))
        self.logger.info("Chat cog initialized")

    @app_commands.command(name="ask", description="Ask the bot anything. It will remember your previous messages.")
    @app_commands.describe(prompt="Your question or message")
    async def ask(self, interaction: Interaction, prompt: str):
        await interaction.response.defer(thinking=True)

        user_id = str(interaction.user.id)
        channel_id = str(interaction.channel_id)

        try:
            # Store the user's message and get the conversation
            conversation = await self.conversation_manager.add_message(
                user_id=user_id,
                channel_id=channel_id,
                content=prompt,
                role="user"
            )

            if conversation is None:
                await interaction.followup.send("⚠️ Could not store your message. Please try again.")
                return

            # Generate a response using the conversation
            response = await self.conversation_manager.generate_response(
                user_id=user_id,
                channel_id=channel_id,
                message=prompt,
                conversation=conversation
            )

            if response is None:
                await interaction.followup.send("❌ Failed to generate a response.")
                return

            await interaction.followup.send(
                f"**Question:** {prompt}\n\n🧠 **Answer:**```markdown\n{response}```"
            )

        except Exception as e:
            self.logger.error(f"Error in /ask command: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error while generating response: {str(e)}", ephemeral=True)

    # @app_commands.command(name="wipeconvo", description="Clear your chat history with the bot in this channel.")
    # async def wipeconvo(self, interaction: Interaction):
    #     await interaction.response.defer(thinking=True)

    #     user_id = str(interaction.user.id)
    #     channel_id = str(interaction.channel_id)

    #     try:
    #         await self.conversation_manager.reset_conversation(user_id, channel_id)
    #         await interaction.followup.send("🧹 Your conversation history has been cleared.")
    #     except Exception as e:
    #         self.logger.error(f"Error in /wipeconvo command: {e}", exc_info=True)
    #         await interaction.followup.send("❌ Failed to clear your conversation.", ephemeral=True)



async def setup(bot):
    await bot.add_cog(Chat(bot))
