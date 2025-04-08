
from summarizer.deepseek_pipeline_tokenaware import summarize_article_full

LIMITS = {
    "tl;dr": 500,
    "default": 1000,
    "detailed": 1800
}

async def summarize_text(text: str, title: str, url: str, summary_type: str = "default") -> str:
    result = await summarize_article_full(
        text=text,
        summary_type=summary_type,
        title=title,
        url=url
    )
    return result[:LIMITS.get(summary_type, 1000)]
