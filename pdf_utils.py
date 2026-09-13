from io import BytesIO
from pypdf import PdfReader

MAX_PDF_BYTES = 20 * 1024 * 1024
MAX_CHARS_PER_DOC = 120_000


def extract_pdf_text(uploaded_file) -> tuple[str, int, list[dict]]:
    """Extract text and lightweight page metadata from a PDF-like upload."""
    data = uploaded_file.getvalue()
    if len(data) > MAX_PDF_BYTES:
        raise ValueError("The PDF is larger than 20 MB. Please use a smaller file for the hackathon demo.")

    reader = PdfReader(BytesIO(data))
    page_text = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        text = text.replace("\x00", " ").strip()
        if text:
            page_text.append({"page": i, "text": text})

    full = "\n\n".join(f"[Page {x['page']}]\n{x['text']}" for x in page_text)
    if len(full) > MAX_CHARS_PER_DOC:
        head = int(MAX_CHARS_PER_DOC * 0.68)
        tail = MAX_CHARS_PER_DOC - head
        full = full[:head] + "\n\n[...middle of PDF truncated for MVP context... ]\n\n" + full[-tail:]

    if not full.strip():
        raise ValueError("No selectable text was found in this PDF. For this MVP, upload a text-based PDF rather than a scanned image-only PDF.")
    return full, len(reader.pages), page_text


def make_evidence_excerpt(page_text: list[dict], query_terms: list[str], limit: int = 6000) -> str:
    """Return relevant page excerpts for user-facing evidence."""
    scores = []
    q = [t.lower() for t in query_terms]
    for item in page_text:
        text = item["text"].lower()
        score = sum(text.count(term) for term in q if term)
        scores.append((score, item))
    scores.sort(key=lambda x: x[0], reverse=True)
    selected = [item for score, item in scores[:8] if score > 0]
    if not selected:
        selected = page_text[:4]
    out = []
    used = 0
    for item in selected:
        chunk = f"Page {item['page']}: {item['text']}"
        if used + len(chunk) > limit:
            break
        out.append(chunk)
        used += len(chunk)
    return "\n\n".join(out)
