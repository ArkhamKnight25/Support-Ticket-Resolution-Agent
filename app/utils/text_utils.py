import re


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text


def truncate(text: str, max_chars: int = 500) -> str:
    return text[:max_chars] + "..." if len(text) > max_chars else text
