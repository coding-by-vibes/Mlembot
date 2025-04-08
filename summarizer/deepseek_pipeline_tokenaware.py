import os
import httpx
import asyncio
import tiktoken

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL_NAME = "deepseek-chat"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

SUMMARY_INSTRUCTIONS = {
    "tl;dr": "Write a 1–2 sentence summary of this article’s core idea. No formatting.",
    "default": (
        "Summarize this article clearly and concisely. Use bullet points *only* if the article itself uses lists or numbered sections. "
        "Avoid formatting examples, markdown instructions, or headings unless present in the original article."
    ),
    "detailed": (
        "Provide a detailed, paragraph-based summary. If the article uses natural section breaks (e.g. intro, technique, tips), reflect that. "
        "Use bullet points only when necessary. Avoid restating any formatting rules. Output should read like a clean article digest."
    )
}

def truncate_to_token_limit(text, max_tokens=1500):
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    return enc.decode(tokens[:max_tokens])

def clean_discord_markdown(text):
    lines = text.splitlines()
    cleaned = []
    last_was_parent_bullet = False

    for line in lines:
        stripped = line.strip()

        # Fix headings
        if stripped.startswith("###") or stripped.startswith("##"):
            stripped = "**" + stripped.lstrip("#").strip() + "**"

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

    return "\n".join(cleaned)

async def format_summary_with_chatgpt(summary_text: str) -> str:
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise ValueError("Missing OPENAI_API_KEY")

    SYSTEM_PROMPT = (
        "You will receive a raw article summary. Format it using only markdown compatible with Discord messages.\n"
        "- Use `-` for top-level bullets\n"
        "- Use `  -` for sub-bullets\n"
        "- Bold key terms or phrases at the start of lines (e.g., `- **Newcomer-Friendly**: text`)\n"
        "- Do not use `###` or other heading styles\n"
        "- Do not wrap section headers in triple asterisks (***). Just use standard bold.\n"
        "- Avoid any commentary, character count notes, or summary framing\n"
        "- Return only the formatted summary"
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
        f"Output must be under {max_final_chars} characters. Use clean, readable markdown (like `-` for bullets), "
        f"but avoid quoting or repeating formatting rules. Never echo the prompt or structure of the instructions. "
        f"Focus purely on the content."
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
