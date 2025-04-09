# utils/discord_utils.py

import re
from discord import Interaction, Message

def fix_discord_formatting(text: str) -> str:
    """Fix Discord markdown formatting issues before sending messages.
    
    This function ensures text follows Discord's markdown formatting rules:
    1. Converting excess hashtags (#### or more) to bold headers
    2. Ensuring proper spacing after hashtags in headers
    3. Limiting asterisks to maximum of 3 (***) for bold+italic
    4. Limiting underscores to maximum of 2 (__) for underline
    5. Limiting tildes to maximum of 2 (~~) for strikethrough
    
    Args:
        text: The text to fix
        
    Returns:
        Properly formatted text for Discord
    """
    # Replace header lines with 4+ hashtags with bold formatting
    # Example: "#### Header" -> "**Header**"
    text = re.sub(r'^(#{4,})\s+(.+?)$', r'**\2**', text, flags=re.MULTILINE)
    
    # Ensure proper spacing after hashtags in headers (# Header, ## Header, ### Header)
    text = re.sub(r'^(#{1,3})([^\s#].+?)$', r'\1 \2', text, flags=re.MULTILINE)
    
    # Fix excessive asterisks (more than 3) - convert to bold+italic
    # This handles cases like ****text**** -> ***text***
    text = re.sub(r'\*{4,}([^*]+?)\*{4,}', r'***\1***', text)
    
    # Fix excessive underscores (more than 2) - convert to underline
    # This handles cases like ___text___ -> __text__
    text = re.sub(r'_{3,}([^_]+?)_{3,}', r'__\1__', text)
    
    # Fix excessive tildes (more than 2) - convert to strikethrough
    # This handles cases like ~~~text~~~ -> ~~text~~
    text = re.sub(r'~{3,}([^~]+?)~{3,}', r'~~\1~~', text)
    
    # Fix mismatched markdown pairs (e.g., different number of opening/closing characters)
    # This is more complex and would require further parsing
    
    return text

async def send_discord_safe(target, full_text: str, wrap_in_markdown: bool = False):
    """Send one or more messages to Discord, respecting the 2000 character limit.
    
    Args:
        target: Either a discord.Interaction or discord.Message object
        full_text: The text to send
        wrap_in_markdown: Whether to wrap the text in markdown code blocks
    """
    if len(full_text.strip()) == 0:
        print("[Warning] Tried to send empty message")
        return

    # Extract code blocks to protect them from formatting changes
    code_blocks = {}
    code_block_pattern = r'```([\w]*)\n.*?```'
    
    # Extract and temporarily replace code blocks with placeholders
    def replace_code_block(match):
        placeholder = f"__CODE_BLOCK_{len(code_blocks)}__"
        code_blocks[placeholder] = match.group(0)
        return placeholder
    
    # Extract code blocks
    text_without_code = re.sub(code_block_pattern, replace_code_block, full_text, flags=re.DOTALL)
    
    # Fix Discord markdown formatting issues on text outside code blocks
    fixed_text = fix_discord_formatting(text_without_code)
    
    # Restore code blocks
    for placeholder, code_block in code_blocks.items():
        fixed_text = fixed_text.replace(placeholder, code_block)
    
    # Auto-disable wrapping if content looks like recipe or clean markdown
    def looks_like_clean_markdown(text):
        return (
            "**Ingredients:**" in text or
            "**Instructions:**" in text or
            re.search(r"(^|\n)-\s", text) or
            re.search(r"(^|\n)\d+\.\s", text)
        )

    if wrap_in_markdown and looks_like_clean_markdown(fixed_text):
        print("[Info] Detected formatted markdown — disabling wrap_in_markdown")
        wrap_in_markdown = False

    def split_code_block(code_block: str, language: str = "") -> list[str]:
        """Split a code block into chunks that fit within Discord's limit."""
        # Remove the code block markers
        content = code_block[len("```" + language):-len("```")].strip()
        
        # Calculate available space for content (accounting for code block markers)
        max_content_length = 2000 - len("```" + language + "\n\n```")
        
        chunks = []
        current_chunk = ""
        
        # Split by lines to try to keep logical breaks
        lines = content.split("\n")
        for line in lines:
            if len(current_chunk) + len(line) + 1 > max_content_length:
                if current_chunk:
                    chunks.append(f"```{language}\n{current_chunk}\n```")
                current_chunk = line
            else:
                if current_chunk:
                    current_chunk += "\n"
                current_chunk += line
        
        if current_chunk:
            chunks.append(f"```{language}\n{current_chunk}\n```")
        
        return chunks

    # Handle code blocks separately
    code_blocks = re.finditer(r'```([\w]*)\n.*?```', fixed_text, re.DOTALL)
    code_block_ranges = [(m.start(), m.end(), m.group(1)) for m in code_blocks]
    
    # Split the text into chunks, preserving code blocks
    chunks = []
    current_chunk = ""
    last_end = 0
    
    for start, end, language in code_block_ranges:
        # Add text before the code block
        pre_code = fixed_text[last_end:start]
        if len(current_chunk) + len(pre_code) > 2000:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = pre_code
        else:
            current_chunk += pre_code
        
        # Handle the code block
        code_block = fixed_text[start:end]
        if len(code_block) > 2000:
            # Split the long code block
            code_chunks = split_code_block(code_block, language)
            for code_chunk in code_chunks:
                if len(current_chunk) + len(code_chunk) > 2000:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = code_chunk
                else:
                    current_chunk += code_chunk
        else:
            if len(current_chunk) + len(code_block) > 2000:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = code_block
            else:
                current_chunk += code_block
        
        last_end = end
    
    # Add any remaining text
    remaining_text = fixed_text[last_end:]
    if len(current_chunk) + len(remaining_text) > 2000:
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        current_chunk = remaining_text
    else:
        current_chunk += remaining_text
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    # Send each chunk
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        if wrap_in_markdown and not chunk.startswith("```"):
            msg = f"```markdown\n{chunk}\n```"
        else:
            msg = chunk

        if len(msg) > 2000:
            print(f"[Error] Chunk too long even after split: {len(msg)} chars")
            msg = msg[:1997] + "..."

        # Handle both Interaction and Message objects
        if isinstance(target, Interaction):
            await target.followup.send(msg)
        elif isinstance(target, Message):
            await target.reply(msg)
        else:
            raise TypeError("target must be either a discord.Interaction or discord.Message object")
