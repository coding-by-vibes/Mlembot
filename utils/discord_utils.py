# utils/discord_utils.py

import re

async def send_discord_safe(interaction, full_text: str, wrap_in_markdown: bool = False):
    """Send one or more messages to Discord, respecting the 2000 character limit."""
    if len(full_text.strip()) == 0:
        print("[Warning] Tried to send empty message")
        return

    # Auto-disable wrapping if content looks like recipe or clean markdown
    def looks_like_clean_markdown(text):
        return (
            "**Ingredients:**" in text or
            "**Instructions:**" in text or
            re.search(r"(^|\n)-\s", text) or
            re.search(r"(^|\n)\d+\.\s", text)
        )

    if wrap_in_markdown and looks_like_clean_markdown(full_text):
        print("[Info] Detected formatted markdown — disabling wrap_in_markdown")
        wrap_in_markdown = False

    # Strip code block if rewrapping
    if wrap_in_markdown:
        full_text = full_text.strip()
        if full_text.startswith("```") and full_text.endswith("```"):
            full_text = "\n".join(full_text.split("\n")[1:-1])

    wrapper_len = len("```markdown\n\n```")  # 14 chars budget
    max_length = 2000 - wrapper_len

    lines = full_text.splitlines()
    chunks = []
    current = ""

    for line in lines:
        if len(current) + len(line) + 1 > max_length:
            if current.strip():
                chunks.append(current.strip())
            current = line
        else:
            current += "\n" + line

    if current.strip():
        chunks.append(current.strip())

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        if wrap_in_markdown:
            msg = f"```markdown\n{chunk}\n```"
        else:
            msg = chunk

        if len(msg) > 2000:
            print(f"[Error] Chunk too long even after split: {len(msg)} chars")
            msg = msg[:1997] + "..."

        await interaction.followup.send(msg)
