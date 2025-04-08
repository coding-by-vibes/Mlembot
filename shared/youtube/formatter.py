
def format_summary_for_discord(summary: str) -> str:
    """Format summary text for Discord markdown."""
    return summary

def format_recipe_for_discord(recipe: dict) -> str:
    """Format recipe markdown for Discord, given parsed recipe dict."""
    return recipe.get("markdown", "")
