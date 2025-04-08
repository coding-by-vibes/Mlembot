import re
from typing import Optional, Dict, List
from datetime import datetime


class RecipeDetector:
    def __init__(self):
        self.recipe_patterns = {
            "ingredients": [
                r'ingredients?:\s*(.+?)(?=\n\s*(instructions|directions|steps|method|how to make|preparation|procedure|cooking steps))',
                r'##\s*Ingredients\s*(.+?)(?=\n\s*##\s*(Directions|Instructions|Steps))'
            ],
            "instructions": [
                r'instructions?:\s*(.+?)(?=\n\s*(notes|special equipment|make-ahead|storage|nutrition facts|$))',
                r'directions?:\s*(.+?)(?=\n\s*(notes|$))',
                r'steps?:\s*(.+?)(?=\n\s*(notes|$))',
                r'method:\s*(.+?)(?=\n\s*(notes|$))',
                r'##\s*Directions\s*(.+?)(?=\n\s*##)'
            ],
            "servings": [
                r'serves?\s*(\d+(?:\s*to\s*\d+)?)',
                r'makes?\s*(\d+(?:\s*to\s*\d+)?)',
                r'yield:\s*(\d+(?:\s*to\s*\d+)?)'
            ],
            "prep_time": [
                r'prep(?:aration)?\s*time:\s*([^\n]+)',
                r'prep:\s*([^\n]+)'
            ],
            "cook_time": [
                r'cook(?:ing)?\s*time:\s*([^\n]+)',
                r'cook:\s*([^\n]+)'
            ],
            "total_time": [
                r'total\s*time:\s*([^\n]+)',
                r'ready\s*in:\s*([^\n]+)'
            ]
        }

    def detect_recipe(self, text: str) -> Optional[Dict]:
        ingredients = self._extract_list_field(text, self.recipe_patterns["ingredients"])
        instructions = self._extract_list_field(text, self.recipe_patterns["instructions"])

        if not ingredients or not instructions:
            return None

        return {
            "title": self._guess_title(text),
            "ingredients": ingredients,
            "instructions": instructions,
            "servings": self._extract_field(text, self.recipe_patterns["servings"]),
            "prep_time": self._extract_field(text, self.recipe_patterns["prep_time"]),
            "cook_time": self._extract_field(text, self.recipe_patterns["cook_time"]),
            "total_time": self._extract_field(text, self.recipe_patterns["total_time"]),
            "extracted_at": datetime.now().isoformat()
        }

    def _extract_list_field(self, text: str, patterns: List[str]) -> Optional[List[str]]:
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                section = match.group(1).strip()
                return [line.strip("-• \t").strip() for line in section.splitlines() if line.strip()]
        return None

    def _extract_field(self, text: str, patterns: List[str]) -> Optional[str]:
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _guess_title(self, text: str) -> str:
        match = re.search(r"title[:\-]\s*(.+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        lines = text.strip().splitlines()
        return lines[0].strip() if lines else "Untitled Recipe"


def format_recipe_markdown(recipe: dict, limit: int = 1800) -> str:
    """
    Formats a recipe dict for Discord-safe Markdown.
    Keys expected: title, ingredients (list), instructions (list), prep_time, cook_time, total_time, yields, notes
    """
    title = recipe.get("title", "Untitled Recipe")
    ingredients = recipe.get("ingredients", [])
    instructions = recipe.get("instructions", [])

    # Deduplicate and clean ingredients
    ingredients = [i.strip() for i in ingredients if i.strip()]
    ingredients = list(dict.fromkeys(ingredients))  # remove exact duplicates

    # Deduplicate and clean instructions
    instructions = [i.strip() for i in instructions if i.strip()]
    instructions = list(dict.fromkeys(instructions))

    lines = [f"**📋 Full Recipe Card**\n**{title}**"]

    # Ingredient Section
    if ingredients:
        lines.append("\n**Ingredients:**")
        for item in ingredients:
            # Avoid redundant "Ingredients:" inside list
            if item.lower().startswith("ingredients:"):
                continue
            lines.append(f"- {item}")

    # Instruction Section
    if instructions:
        lines.append("\n**Instructions:**")
        for i, step in enumerate(instructions, start=1):
            lines.append(f"{i}. {step}")

    # Optional Metadata
    time_fields = {
        "⏱️ Prep Time": recipe.get("prep_time"),
        "🔥 Cook Time": recipe.get("cook_time"),
        "⏳ Total Time": recipe.get("total_time"),
        "🍽️ Yields": recipe.get("yields"),
    }

    time_lines = [f"{emoji}: {val}" for emoji, val in time_fields.items() if val]
    if time_lines:
        lines.append("\n**Meta:**")
        lines.extend([f"- {line}" for line in time_lines])

    # Optional Notes
    if recipe.get("notes"):
        lines.append("\n**Notes:**")
        lines.append(f"- {recipe['notes'].strip()}")

    # Combine lines while respecting the character limit
    final_output = ""
    cutoff_reached = False

    for line in lines:
        if len(final_output) + len(line) + 1 > limit - 5:
            cutoff_reached = True
            break
        final_output += line + "\n"

    if cutoff_reached:
        final_output = final_output.rstrip() + "\n[...]"

    return final_output