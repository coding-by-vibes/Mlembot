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


def detect_recipe_from_text(text: str) -> Optional[Dict]:
    return RecipeDetector().detect_recipe(text)
