MIN_CHUNK_LENGTH = 50
MAX_WHITESPACE_RATIO = 0.6


def is_valid_chunk(text: str) -> bool:
    """Return False if the chunk is too short or mostly whitespace/symbols."""
    if len(text) < MIN_CHUNK_LENGTH:
        return False

    non_whitespace = sum(1 for c in text if not c.isspace())
    if non_whitespace / max(len(text), 1) < (1 - MAX_WHITESPACE_RATIO):
        return False

    return True


def filter_chunks(chunks: list) -> list:
    """Remove low-quality chunks from a list of TextChunk objects."""
    return [c for c in chunks if is_valid_chunk(c.text)]
