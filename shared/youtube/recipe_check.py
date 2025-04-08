from utils.recipe import RecipeDetector

recipe_detector = RecipeDetector()

def detect_recipe_from_text(text: str) -> dict:
    return recipe_detector.detect_recipe(text)
