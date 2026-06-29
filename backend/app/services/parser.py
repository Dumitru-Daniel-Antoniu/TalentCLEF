from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def parse_resume(path: Path) -> str:




    try:
        ext = path.suffix.lower()
        if ext == ".pdf":
            try:
                import pdfplumber

                with pdfplumber.open(path) as pdf:
                    pages = [p.extract_text() or "" for p in pdf.pages]
                    text = "\n".join(pages)
                    return text.strip()
            except Exception:

                try:
                    import PyPDF2

                    with open(path, "rb") as fh:
                        reader = PyPDF2.PdfReader(fh)
                        pages = [p.extract_text() or "" for p in reader.pages]
                        return "\n".join(pages).strip()
                except Exception as e:
                    logger.exception("PDF parse failed: %s", e)
                    return ""

        elif ext in (".docx", ".doc"):
            try:
                from docx import Document

                doc = Document(path)
                paragraphs = [p.text for p in doc.paragraphs]
                return "\n".join(paragraphs).strip()
            except Exception as e:
                logger.exception("DOCX parse failed: %s", e)
                return ""

        else:

            try:
                return path.read_text(encoding="utf-8", errors="ignore").strip()
            except Exception:
                return ""
    except Exception as e:
        logger.exception("Unexpected parse error: %s", e)
        return ""
