from pathlib import Path
from app.services.logging_service import get_logger

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}


def load_file(path: Path) -> str:
    """Load raw text from a .txt, .md, or .pdf file."""
    ext = path.suffix.lower()

    if ext in (".txt", ".md"):
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")

    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n\n".join(pages)
        except ImportError:
            logger.warning("pypdf not installed — skipping PDF", file=str(path))
            return ""

    logger.warning("Unsupported file type — skipping", file=str(path), ext=ext)
    return ""


def load_from_bytes(content: bytes, filename: str) -> str:
    """Load raw text from in-memory bytes (used by the upload API)."""
    ext = Path(filename).suffix.lower()

    if ext in (".txt", ".md"):
        return content.decode("utf-8", errors="ignore")

    if ext == ".pdf":
        try:
            import io
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n\n".join(pages)
        except ImportError:
            logger.warning("pypdf not installed — cannot process PDF bytes", filename=filename)
            return ""

    return content.decode("utf-8", errors="ignore")


def discover_documents(raw_dir: str | Path) -> list[Path]:
    """Return all supported files under raw_dir recursively."""
    root = Path(raw_dir)
    if not root.exists():
        return []
    return [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]
