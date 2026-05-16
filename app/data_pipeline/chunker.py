from dataclasses import dataclass


@dataclass
class TextChunk:
    text: str
    chunk_index: int


def _split_on_separators(text: str, separators: list[str]) -> list[str]:
    """Recursively split text trying each separator in order."""
    if not separators:
        return [text]

    sep = separators[0]
    parts = text.split(sep)

    # Filter empty parts but preserve structure
    return [p.strip() for p in parts if p.strip()]


def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[TextChunk]:
    """
    Split text into overlapping chunks using a recursive separator strategy.
    Tries to split on paragraph breaks, then sentences, then words.
    """
    separators = ["\n\n", "\n", ". ", " "]
    chunks: list[TextChunk] = []
    current_chunk = ""
    chunk_index = 0

    # First split into paragraphs/sentences
    segments = _split_on_separators(text, separators[:2])

    for segment in segments:
        # If segment alone exceeds chunk_size, break it further
        if len(segment) > chunk_size:
            words = segment.split(" ")
            for word in words:
                if len(current_chunk) + len(word) + 1 <= chunk_size:
                    current_chunk = current_chunk + " " + word if current_chunk else word
                else:
                    if current_chunk:
                        chunks.append(TextChunk(text=current_chunk.strip(), chunk_index=chunk_index))
                        chunk_index += 1
                        # Carry over overlap
                        overlap_text = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else current_chunk
                        current_chunk = overlap_text + " " + word
                    else:
                        current_chunk = word
        else:
            if len(current_chunk) + len(segment) + 2 <= chunk_size:
                current_chunk = current_chunk + "\n\n" + segment if current_chunk else segment
            else:
                if current_chunk:
                    chunks.append(TextChunk(text=current_chunk.strip(), chunk_index=chunk_index))
                    chunk_index += 1
                    overlap_text = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else current_chunk
                    current_chunk = overlap_text + "\n\n" + segment
                else:
                    current_chunk = segment

    if current_chunk.strip():
        chunks.append(TextChunk(text=current_chunk.strip(), chunk_index=chunk_index))

    return chunks
