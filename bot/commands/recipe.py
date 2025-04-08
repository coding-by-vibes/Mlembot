# from discord.ext import commands
# from discord import app_commands, Interaction
# from scraper.article_utils import get_article_as_json
# from utils.recipe import format_recipe_markdown
# from utils.discord_utils import send_discord_safe


# class Recipe(commands.Cog):
#     def __init__(self, bot):
#         self.bot = bot

#     @app_commands.command(name="recipe", description="Extract ingredients and instructions from a recipe URL.")
#     @app_commands.describe(url="The link to a recipe article")
#     async def recipe(
#         self,
#         interaction: Interaction,
#         url: str
#     ):
#         await interaction.response.send_message(f"⏳ Attempting to extract recipe from <{url}>...", ephemeral=True)

#         try:
#             article = await get_article_as_json(url)

#             title = article.get("title") or "Untitled Recipe"
#             ingredients = article.get("ingredients_text", [])
#             instructions = article.get("instructions_text", [])

#             if not (ingredients and instructions):
#                 return await interaction.followup.send("❌ No valid recipe ingredients or instructions found.")

#             recipe_card = format_recipe_markdown({
#                 "title": title,
#                 "ingredients": ingredients,
#                 "instructions": instructions,
#                 "prep_time": article.get("prep_time"),
#                 "cook_time": article.get("cook_time"),
#                 "total_time": article.get("total_time"),
#                 "yields": article.get("yields"),
#                 "notes": article.get("notes")
#             }, limit=1950)

#             await send_discord_safe(interaction, recipe_card)

#         except Exception as e:
#             import traceback
#             print(traceback.format_exc())
#             await interaction.followup.send(f"❌ Recipe extraction failed: {str(e)}")


# async def setup(bot):
#     await bot.add_cog(Recipe(bot))
