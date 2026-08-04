"""PDF text extraction and chunking utilities."""
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from app.core.config import settings
from app.core.exceptions import ValidationAppError


def extract_text_from_pdf(file_path: str) -> str:
    """Extract raw text from a PDF file on disk."""
    try:
        reader = PdfReader(file_path)
    except Exception as exc:
        raise ValidationAppError("Unable to parse PDF file") from exc

    pages_text = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(text)

    full_text = "\n\n".join(pages_text).strip()
    if not full_text:
        raise ValidationAppError("No extractable text found in PDF")
    return full_text


def chunk_text(text: str) -> list[str]:
    """Split text into overlapping chunks using a recursive character splitter.

    Chunk size and overlap are configured in characters as an approximation
    of the target token budget (see ADR-007 / rules.md AI Rules).
    """
    # Approximate 1 token ~= 4 characters for chunk sizing purposes.
    chunk_size_chars = settings.chunk_size * 4
    chunk_overlap_chars = settings.chunk_overlap * 4

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size_chars,
        chunk_overlap=chunk_overlap_chars,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)
