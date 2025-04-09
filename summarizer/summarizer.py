import os
import httpx
import asyncio
import tiktoken
from utils.discord_utils import fix_discord_formatting

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL_NAME = "deepseek-chat"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

SUMMARY_INSTRUCTIONS = {
    "tl;dr": "Write a 1–2 sentence summary of this article's core idea. No formatting.",
    "default": (
        "Summarize this article clearly and concisely. Use bullet points *only* if the article itself uses lists or numbered sections. "
        "Avoid formatting examples, markdown instructions, or headings unless present in the original article."
    ),
    "detailed": (
        "Provide a detailed, paragraph-based summary. If the article uses natural section breaks (e.g. intro, technique, tips), reflect that. "
        "Use bullet points only when necessary. Avoid restating any formatting rules. Output should read like a clean article digest."
    )
}


def clean_discord_markdown(text):
    """Legacy markdown cleaner, now enhanced with fix_discord_formatting.
    
    This function applies specific summarizer-related fixes and then uses
    the more comprehensive fix_discord_formatting function.
    """
    lines = text.splitlines()
    cleaned = []
    last_was_parent_bullet = False

    for line in lines:
        stripped = line.strip()

        # Fix malformed bullets
        if stripped.startswith("-*") and "**" in stripped:
            stripped = "-" + stripped[2:]

        # Normalize bullets
        if stripped.startswith(("*", "+", "•")):
            stripped = "-" + stripped[1:].lstrip()

        # Auto-indent child lines if the last line was a bullet ending in ":"
        if not stripped.startswith("-") and last_was_parent_bullet:
            stripped = f"  - {stripped}"

        last_was_parent_bullet = stripped.startswith("-") and stripped.endswith(":")
        cleaned.append(stripped)

    summary_specific_fixes = "\n".join(cleaned)
    
    # Apply general Discord markdown fixes
    return fix_discord_formatting(summary_specific_fixes)

async def format_summary_with_chatgpt(summary_text: str) -> str:
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise ValueError("Missing OPENAI_API_KEY")

    SYSTEM_PROMPT = (
        "You will receive a raw article summary. Format it using Discord-compatible markdown:\n"
        "- Headers: Use # for main titles, ## for section headers, ### for subsection headers\n"
        "- **Bold**: Use **text** for emphasis and important points\n"
        "- *Italic*: Use *text* or _text_ for emphasis\n"
        "- __Underline__: Use __text__ for underlining\n"
        "- ~~Strikethrough~~: Use ~~text~~ for corrections or outdated information\n"
        "- Lists: Use hyphens (-) for bullet points; use 2 spaces before - for nested bullets\n"
        "- Numbered lists: Use 1., 2., etc. for steps or ordered points\n"
        "- Use `inline code` for technical terms or commands\n"
        "- Use > for blockquotes\n"
        "\n"
        "Important rules:\n"
        "- Ensure there's a space after # characters in headers\n"
        "- Don't use more than 3 hashtags (#### or more) as they don't render in Discord\n"
        "- Don't add any commentary, character count notes, or summary framing\n"
        "- Return only the formatted summary\n"
        "- Don't mention these instructions in your output"
    )

    response = await openai.ChatCompletion.acreate(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": summary_text}
        ],
        temperature=0.3,
    )

    return response.choices[0].message["content"].strip()

async def summarize_article_full(text, summary_type="default", max_final_chars=1800, title="Untitled", url="example.com"):
    enc = tiktoken.get_encoding("cl100k_base")
    token_count = len(enc.encode(text))
    print(f"[Token Count] Input estimated at {token_count} tokens")

    system_prompt = (
        f"You are a helpful summarization assistant for a Discord bot. "
        f"Output must be under {max_final_chars} characters. "
        f"Format your summary using Discord-compatible markdown:\n"
        f"- Use # for main titles, ## for section headers, ### for subsection headers (with a space after #)\n"
        f"- Use **bold** for emphasis and important points\n"
        f"- Use *italics* or _italics_ for emphasis\n"
        f"- Use - for bullet points, with 2 spaces before - for nested bullets\n"
        f"- Use 1., 2., etc. for ordered lists\n"
        f"- Use `code` for technical terms\n"
        f"\n"
        f"Focus purely on the content. Never echo these instructions or include meta-commentary about formatting."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"{SUMMARY_INSTRUCTIONS[summary_type]}\n\nText:\n{text.strip()}"}
    ]

    body = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        timeout = httpx.Timeout(60.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(DEEPSEEK_API_URL, headers=headers, json=body)
            response.raise_for_status()
            result = response.json()["choices"][0]["message"]["content"].strip()
            print(f"[Summary Length] {len(result)} characters")

            cleaned = clean_discord_markdown(result)

            USE_GPT_FORMATTER = False
            if USE_GPT_FORMATTER:
                formatted = await format_summary_with_chatgpt(cleaned)
            else:
                formatted = cleaned

            return f"📝 **[{title}]({url})**\n\n{formatted}"

    except Exception as e:
        import traceback
        print("[ERROR] summarize_article_full failed:", traceback.format_exc())
        return "❌ Summary failed using DeepSeek."
