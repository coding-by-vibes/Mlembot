import re
import trafilatura
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from trafilatura.settings import use_config
from scraper.stealth_scraper import fetch_content
import json


def extract_text_list_from_dom(soup, selector) -> list[str]:
    return [
        el.get_text(strip=True)
        for el in soup.select(selector)
        if el.get_text(strip=True)
    ]


# def try_scrape_me(url: str) -> dict | None:
#     try:
#         from recipe_scrapers import scrape_me
#         scraper = scrape_me(url)

#         return {
#             "title": scraper.title(),
#             "ingredients_text": scraper.ingredients(),
#             "instructions_text": scraper.instructions().split("\n"),
#             "ingredients_html": "",
#             "instructions_html": "",
#             "text": "",  # You can optionally fetch article prose too
#             "markdown": "",
#             "format_type": "recipe_scraper"
#         }

    # except Exception:
    #     return None  # Silent fail for unsupported sites


async def get_article_as_json(url: str) -> dict:
    html = await fetch_content(url)
    if not html:
        raise ValueError(f"[ERROR] Failed to fetch HTML from: {url}")

    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text(separator="\n", strip=True)

    # Try recipe-scrapers first
    # scraped = try_scrape_me(url)
    # if scraped:
    #     # fallback patch for scrape_me
    #     instruction_candidates = soup.select(
    #         "ol li, ul li, .mntl-sc-block-group--LI, [class*=instruction], [class*=step]"
    #     )
    #     dom_instructions = [
    #         el.get_text(strip=True) for el in instruction_candidates if el.get_text(strip=True)
    #     ]

    #     if isinstance(scraped, dict) and len(scraped.get("instructions_text", [])) < 3 and dom_instructions:
    #         print("[🩹] scrape_me returned too few instructions. Using DOM fallback.")
    #         scraped["instructions_text"] = dom_instructions

    #     return scraped


    # No scrape_me fallback — continue with DOM-based extract
    ingredient_text = extract_text_list_from_dom(
        soup,
        ".ingredient, .ingredients li, .ingredient-list li, [class*=ingredient]"
    )
    ingredient_html = "\n".join(str(el) for el in soup.select(
        ".ingredient, .ingredients li, .ingredient-list li, [class*=ingredient]"
    ))

    instruction_candidates = soup.select(
        "ol li, ul li, .mntl-sc-block-group--LI, [class*=instruction], [class*=step]"
    )
    instruction_text = [
        el.get_text(strip=True) for el in instruction_candidates if el.get_text(strip=True)
    ]
    instruction_html = "\n".join(str(el) for el in instruction_candidates)

    # Paragraph fallback for instructions
    if len(instruction_text) < 3:
        print("[🪄] Adding backup paragraph-style instructions.")
        paragraphs = soup.select("div.mntl-sc-block-group--P p, div.mntl-sc-block p")
        for para in paragraphs:
            text = para.get_text(strip=True)
            if len(text.split()) > 5:
                instruction_text.append(text)

    config = use_config()
    config.set("DEFAULT", "output_format", "xml")

    raw_extracted = trafilatura.extract(html, with_metadata=True, config=config)
    markdown = md(raw_extracted or "", heading_style="ATX") if raw_extracted else ""
    clean_text = raw_extracted or ""

    if not clean_text.strip() and markdown.strip():
        print("[💡] No clean_text found, using markdown fallback.")
        clean_text = markdown

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else "Untitled"

    return {
        "title": title,
        "text": clean_text,
        "markdown": markdown,
        "format_type": "dom_or_fallback",
        "ingredients_text": ingredient_text,
        "ingredients_html": ingredient_html,
        "instructions_text": instruction_text,
        "instructions_html": instruction_html
    }


def extract_text_from_html(html: str) -> dict:
    """Extract readable content from raw HTML using trafilatura."""
    extracted = trafilatura.extract(html, with_metadata=True, output_format="json")
    if not extracted:
        raise ValueError("Failed to extract readable content from HTML.")
    return json.loads(extracted)


async def get_article_from_dynamic_site(url: str) -> dict:
    html = await fetch_content(url)
    return extract_text_from_html(html)


# async def get_article_as_json(url: str) -> dict:
#     return await fetch_article_markdown(url)
