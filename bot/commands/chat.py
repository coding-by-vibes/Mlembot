from discord.ext import commands
from discord import app_commands, Interaction, Message
import logging
from utils.conversation import ConversationManager
from utils.user_manager import UserManager
from utils.discord_utils import send_discord_safe
from pathlib import Path

# Character limits for responses
DEFAULT_CHAR_LIMIT = 1800  # Default limit for responses
EXTENDED_CHAR_LIMIT = DEFAULT_CHAR_LIMIT + 500  # Extended limit when more detail is requested

# Keywords that indicate a request for more detail
DETAIL_KEYWORDS = [
    "more detail",
    "more information",
    "explain more",
    "elaborate",
    "longer answer",
    "detailed answer",
    "in depth",
    "thorough"
]

class Chat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.settings_dir = Path("storage")
        self.user_manager = UserManager(settings_dir=self.settings_dir)
        self.conversation_manager = ConversationManager(settings_dir=str(self.settings_dir))
        self.logger.info("Chat cog initialized")

    def _get_char_limit(self, message: str) -> int:
        """Determine the character limit based on the message content."""
        message_lower = message.lower()
        if any(keyword in message_lower for keyword in DETAIL_KEYWORDS):
            return EXTENDED_CHAR_LIMIT
        return DEFAULT_CHAR_LIMIT

    def _get_system_prompt(self, char_limit: int) -> str:
        """Generate the system prompt with the appropriate character limit."""
        return (
            f"You are a helpful AI assistant in a Discord chat. Your responses should be clear, concise, and well-structured, "
            f"using Discord's official markdown formatting:\n"
            f"- Headers: Use # for main titles, ## for section headers, ### for subsection headers\n"
            f"- **Bold**: Use **text** for emphasis and important points\n"
            f"- *Italic*: Use *text* or _text_ for emphasis\n"
            f"- __Underline__: Use __text__ for underlining\n"
            f"- ~~Strikethrough~~: Use ~~text~~ for corrections or outdated information\n"
            f"- `Code`: Use `text` for inline code, commands, or technical terms\n"
            f"- ```Code blocks```: Use ``` for multi-line code examples; add language name for syntax highlighting\n"
            f"- Lists: Use hyphens (-) for bullet points; use 2 spaces before - for nested bullets\n"
            f"- Numbered lists: Use 1., 2., etc. for steps or ordered points\n"
            f"- > Blockquote: Use > for single-line quotes\n"
            f"- >>> Multi-line quote: Use >>> for extended quotes\n"
            f"- Masked links: Use [text](URL) format\n"
            f"- Combine formatting: ***bold and italic***, __**underline and bold**__, etc.\n"
            f"\n"
            f"Remember:\n"
            f"- Discord has a 2000 character limit per message\n"
            f"- Your response must be under {char_limit} characters\n"
            f"- If someone requests more detail, you can use up to {EXTENDED_CHAR_LIMIT} characters\n"
            f"- Keep responses focused and well-organized\n"
            f"- Use appropriate spacing and formatting for readability (e.g., space after # for headers)\n"
            f"- Don't use more than 3 hashtags (####, #####) as they don't render properly in Discord"
        )

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        # Ignore messages from bots
        if message.author.bot:
            return
            
        # Check if this is a reply to a bot message or mentions the bot
        is_reply = message.reference and message.reference.message_id
        is_mention = self.bot.user in message.mentions
        
        if is_reply or is_mention:
            try:
                # If it's a reply, get the referenced message
                if is_reply:
                    referenced_message = await message.channel.fetch_message(message.reference.message_id)
                    # Check if the referenced message is from our bot
                    if referenced_message.author.id != self.bot.user.id:
                        return
                
                await message.channel.typing()
                
                user_id = str(message.author.id)
                channel_id = str(message.channel.id)
                
                # Remove the bot mention from the message content if present
                content = message.content
                if is_mention:
                    content = content.replace(f"<@{self.bot.user.id}>", "").strip()
                
                # Determine character limit and system prompt
                char_limit = self._get_char_limit(content)
                system_prompt = self._get_system_prompt(char_limit)
                
                # Store the user's message and get the conversation
                conversation = await self.conversation_manager.add_message(
                    user_id=user_id,
                    channel_id=channel_id,
                    content=content,
                    role="user",
                    system_prompt=system_prompt
                )
                
                if conversation is None:
                    await message.reply("⚠️ Could not store your message. Please try again.")
                    return
                
                # Generate a response using the conversation
                response = await self.conversation_manager.generate_response(
                    user_id=user_id,
                    channel_id=channel_id,
                    message=content,
                    conversation=conversation
                )
                
                if response is None:
                    await message.reply("❌ Failed to generate a response.")
                    return
                
                # Format the response in the same style as /ask
                formatted_response = f"**Question:** {content}\n\n🧠 **Answer:**\n{response}"
                # Only wrap in markdown if the response contains code blocks
                contains_code = "```" in response
                await send_discord_safe(message, formatted_response, wrap_in_markdown=contains_code)
                
            except Exception as e:
                self.logger.error(f"Error in message handler: {e}", exc_info=True)
                await message.reply(f"❌ Error while generating response: {str(e)}")

    @app_commands.command(name="ask", description="Ask the bot anything. It will remember your previous messages.")
    @app_commands.describe(prompt="Your question or message")
    async def ask(self, interaction: Interaction, prompt: str):
        await interaction.response.defer(thinking=True)

        user_id = str(interaction.user.id)
        channel_id = str(interaction.channel_id)

        try:
            # Determine character limit and system prompt
            char_limit = self._get_char_limit(prompt)
            system_prompt = self._get_system_prompt(char_limit)
            
            # Store the user's message and get the conversation
            conversation = await self.conversation_manager.add_message(
                user_id=user_id,
                channel_id=channel_id,
                content=prompt,
                role="user",
                system_prompt=system_prompt
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

            # Format the response and send it safely
            formatted_response = f"**Question:** {prompt}\n\n🧠 **Answer:**\n{response}"
            # Only wrap in markdown if the response contains code blocks
            contains_code = "```" in response
            await send_discord_safe(interaction, formatted_response, wrap_in_markdown=contains_code)

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
