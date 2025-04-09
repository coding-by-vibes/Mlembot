from discord.ext import commands
from discord import app_commands, Interaction
from urllib.parse import urlparse, parse_qs
from scraper.article_utils import get_article_as_json
from utils.youtube import process_youtube_video
from utils.discord_utils import send_discord_safe
from summarizer.summarizer import summarize_article_full
from typing import Optional

SUMMARY_LEVELS = {
    "tl;dr": "Return only 1–2 sentences with key takeaways.",
    "default": "Summarize the article clearly using prose or sections. Use markdown lists *only* if they match the article structure (e.g. tips, steps, variations). Avoid redundant ingredient listings.",
    "detailed": "Provide a detailed, paragraph-style summary with rich insights. Use bullet points sparingly—only when listing multi-step tips or insights. Do not summarize recipe steps as a list unless it reflects article intent."
}

LIMITS = {
    "tl;dr": 500,
    "default": 1000,
    "detailed": 1800
}


class Summarizer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="summarize", description="Summarize an article or YouTube video.")
    @app_commands.describe(url="The link to summarize")
    @app_commands.choices(
        level=[
            app_commands.Choice(name="tl;dr", value="tl;dr"),
            app_commands.Choice(name="default", value="default"),
            app_commands.Choice(name="detailed", value="detailed")
        ]
    )
    async def summarize(
        self,
        interaction: Interaction,
        url: str,
        level: Optional[app_commands.Choice[str]] = None
    ):
        await interaction.response.send_message(f"⏳ Attempting to summarize <{url}>...", ephemeral=True)

        summary_key = level.value if level else "default"
        parsed = urlparse(url)

        # -- YouTube Flow --
        if "youtube.com" in parsed.netloc or "youtu.be" in parsed.netloc:
            try:
                video_id = parse_qs(parsed.query).get("v", [None])[0] if "youtube.com" in parsed.netloc else parsed.path.strip("/")
                if not video_id:
                    raise ValueError("Could not parse YouTube video ID.")

                result = await process_youtube_video(video_id, summary_type=summary_key)
                if not isinstance(result, dict):
                    return await interaction.followup.send("❌ YouTube summary failed: Unexpected response format.")

                return await send_discord_safe(interaction, result["summary"])

            except Exception as e:
                return await interaction.followup.send(f"❌ YouTube summary failed: {str(e)}")

        # -- Article Flow --
        try:
            article = await get_article_as_json(url)
            raw_text = article.get("text", "").strip()
            title = article.get("title") or "Untitled"

            if not raw_text:
                return await interaction.followup.send("⚠️ Unable to extract article content for summarization.")

            summary = await summarize_article_full(
                raw_text,
                summary_type=summary_key,
                title=title,
                url=url
            )
            await send_discord_safe(interaction, summary)

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            await interaction.followup.send(f"❌ Article summary failed: {str(e)}")


async def setup(bot):
    await bot.add_cog(Summarizer(bot))
